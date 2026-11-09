# (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""All the wires of a frame in ONE draw call (TWISTED_WIRE_DESIGN.md).

``wire_pool.py`` gives every wire its path as rows of a texture buffer and draws a wire with one call per conductor. This module
takes the next step: while a canvas draws its objects, each wire only hands in an *entry*; ``flush`` then draws every collected
wire with a single ``glDrawArrays`` per arena (all wires are normally in one).

An entry is 10 RGBA32F texels (160 bytes), written to the texture buffer ``twistEntries`` every frame for the wires that are in view:

* 0: the wire's first row in the pool and its row count (ints, as bits), the entry's first vertex in the draw (an int, as bits,
  filled in by ``flush``), and the stripe's half angle (0 = no stripe)
* 1: the twist rate and the conductor's circle (centre x, centre y, radius)
* 2, 3, 4: the material's ambient, diffuse and specular
* 5: the material's shininess and emissive (r, g, b)
* 6, 7, 8: the stripe's ambient, diffuse and specular
* 9: the vertex, within the wire's own draw, where the entry's rows begin (an int, as bits; 0 unless the entry is only part of a
  wire: the bare end of a wire that crimps into a terminal is an entry of its own, with a circle of its own)

The vertex shader (``faces/vertex.vert``, ``twistBatch``) finds the entry of its vertex by a binary search on the first-vertex
values, then the piece in the wire's rows by a second one; it passes the entry's number to the fragment shader, which reads the
material from the same texels. So a wire's colour, stripe, rate and size are data, not uniforms, and nothing about a frame's
draw depends on how many wires there are or how they are coloured.
"""

import ctypes

import numpy as np
from OpenGL import GL
from PySide6 import QtGui

from .. import check_types as _check_types
from . import wire_pool as _wire_pool


ENTRY_TEXELS = 10
ENTRY_FLOATS = ENTRY_TEXELS * 4
ENTRY_BYTES = ENTRY_FLOATS * 4

# The texture unit the entries are bound to while the batch is drawn (the pool's pieces are on POOL_TEXTURE_UNIT).
ENTRY_TEXTURE_UNIT = 5

# Entries a new entry buffer holds; it grows by half again when a frame has more.
_MIN_ENTRIES = 256


@_check_types.do
def make_entry(first_row: int, rows: int, rate: float, circle: tuple[float, float, float], material: object,
               stripe: object | None, stripe_half: float, vertex_offset: int = 0) -> np.ndarray:
    """One conductor of a wire as an entry (the first-vertex field is left 0: ``flush`` fills it in).

    :param material: A ``gl.materials.GLMaterial``: its ``ambient`` / ``diffuse`` / ``specular`` / ``shininess`` / ``emissive``.
    :param stripe: The stripe's ``GLMaterial``, or ``None`` for a conductor without a stripe.
    :param stripe_half: Half the angular width of a stripe, radians (``shapes.twisted_wire.STRIPE_HALF_ANGLE``).
    :param vertex_offset: The vertex, within the wire's draw, where *first_row* begins (0 for an entry of the whole wire).
    """
    entry = np.zeros(ENTRY_FLOATS, dtype=np.float32)

    ints = entry.view(np.int32)
    ints[0] = first_row
    ints[1] = rows
    ints[36] = vertex_offset

    entry[4] = rate
    entry[5:8] = circle

    entry[8:12] = material.ambient
    entry[12:16] = material.diffuse
    entry[16:20] = material.specular
    entry[20] = material.shininess
    entry[21:24] = material.emissive[:3]

    if stripe is not None:
        entry[3] = stripe_half
        entry[24:28] = stripe.ambient
        entry[28:32] = stripe.diffuse
        entry[32:36] = stripe.specular

    return entry


@_check_types.do
def entries_for(key: str, rate: float, circles: list[tuple[float, float, float]], materials: list, stripes: list,
                stripe_half: float, rows: np.ndarray | None = None,
                ends: tuple[int, int, tuple[float, float, float], object] | None = None
                ) -> tuple[int, list[np.ndarray], list[int]]:
    """The entries of a wire that is in the pool, one per conductor.

    :param rows: The wire's pool rows (``WirePool.pack``), needed with *ends* to know where a piece's vertices begin.
    :param ends: For a wire of ONE conductor whose first and/or last piece is a bare conductor (it crimps into a terminal):
        how many pieces at the start, how many at the end, and the bare conductor's circle and material. Those pieces are
        entries of their own (the circle's radius and the material differ), the pieces between keep the conductor's own, and
        the stripe is left off the bare ones.
    :returns: The pool texture the wire's rows are in, the entries, and the number of vertices each entry draws.
    """
    texture, first_row, count, vertices = _wire_pool.WirePool.locate(key)

    entries = []
    counts = []

    if ends is None:
        for circle, material, stripe in zip(circles, materials, stripes):
            entries.append(make_entry(first_row, count, rate, circle, material, stripe, stripe_half))
            counts.append(vertices)

        return texture, entries, counts

    bare_start, bare_stop, bare_circle, bare_material = ends
    first = rows.view(np.int32)[:, 10]

    def vertices_of(start_row: int, stop_row: int) -> int:
        if stop_row < count:
            end_vertex = int(first[stop_row])
        else:
            end_vertex = vertices

        return end_vertex - int(first[start_row])

    # (first piece, number of pieces, bare?). A wire of a single piece is bare throughout (``TubeMixin._bare_ends``), so there may
    # be no piece between the bare ends: a span with no pieces is left out (its first piece is not even a row of the wire).
    spans = []

    if bare_start:
        spans.append((0, min(bare_start, count), True))

    middle = count - bare_start - bare_stop

    if middle > 0:
        spans.append((bare_start, middle, False))

    if bare_stop and count - bare_stop >= bare_start:
        spans.append((count - bare_stop, bare_stop, True))

    for start_row, piece_count, bare in spans:
        offset = int(first[start_row])
        total = vertices_of(start_row, start_row + piece_count)

        if bare:
            entries.append(make_entry(first_row + start_row, piece_count, 0.0, bare_circle, bare_material, None, stripe_half,
                                      offset))
        else:
            entries.append(make_entry(first_row + start_row, piece_count, rate, circles[0], materials[0], stripes[0],
                                      stripe_half, offset))

        counts.append(total)

    return texture, entries, counts


class WireBatch:
    """Collects the wires of a frame and draws them with one call. One instance (``BATCH``) serves every canvas."""

    def __init__(self):
        # True while a canvas is drawing its objects: a wire hands itself in only then (anywhere else it draws itself)
        self.active = False

        # pool texture -> (entries, vertices per entry) of the wires collected for the arena that texture belongs to
        self._groups: dict[int, tuple[list, list]] = {}

        # entry buffers, one per arena drawn in a frame, grown as needed: (buffer, texture, capacity in entries)
        self._buffers: list[list[int]] = []

        self._vaos: dict[int, int] = {}

    def begin(self) -> None:
        """A canvas starts drawing its objects. (Called once per frame; not wrapped in ``check_types.do``.)"""
        self.active = True
        self._groups.clear()

    def end(self) -> None:
        self.active = False
        self._groups.clear()

    def add(self, texture: int, entry: np.ndarray, vertices: int) -> None:
        """Hand in one conductor of a wire for this frame's draw. Called once per conductor per wire per frame, so not wrapped in
        ``check_types.do``."""
        group = self._groups.get(texture)

        if group is None:
            group = ([], [])
            self._groups[texture] = group

        group[0].append(entry)
        group[1].append(vertices)

    @_check_types.do
    def _vao(self) -> int:
        """An empty vertex array for the current GL context (the core profile will not draw without one bound)."""
        context = QtGui.QOpenGLContext.currentContext()
        if context is None:
            raise RuntimeError('context has not been acquired')

        key = id(context)

        if key not in self._vaos:
            self._vaos[key] = GL.glGenVertexArrays(1)

        return self._vaos[key]

    @_check_types.do
    def _entry_buffer(self, slot: int, count: int) -> list[int]:
        """The entry buffer for the *slot*-th arena of the frame, big enough for *count* entries."""
        while len(self._buffers) <= slot:
            self._buffers.append([0, 0, 0])

        record = self._buffers[slot]

        if record[2] >= count:
            return record

        if record[0] == 0:
            record[0] = int(GL.glGenBuffers(1))
            record[1] = int(GL.glGenTextures(1))

        capacity = max(_MIN_ENTRIES, count, record[2] + record[2] // 2)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, record[0])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, capacity * ENTRY_BYTES, None, GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, record[1])
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER, GL.GL_RGBA32F, record[0])
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, 0)

        record[2] = capacity
        return record

    @_check_types.do
    def flush(self, program: object) -> None:
        """Draw everything collected so far with one call per arena, then forget it. Needs the GL context. Does nothing when
        nothing was collected.

        :param program: The faces program (``gl.shaders.program.FacesProgram``); entered here.
        """
        if not self._groups:
            return

        try:
            with program:
                # these must be 0 for any draw but a WireStripe's
                program.stripe_clip_start = 0.0
                program.stripe_clip_stop = 0.0

                for slot, (texture, (entries, vertices)) in enumerate(self._groups.items()):
                    self._draw_group(program, slot, texture, entries, vertices)
        finally:
            self._groups.clear()

    @_check_types.do
    def _draw_group(self, program: object, slot: int, texture: int, entries: list, vertices: list) -> None:
        count = len(entries)

        data = np.stack(entries)
        per_entry = np.array(vertices, dtype=np.int64)

        first = np.zeros(count, dtype=np.int32)
        np.cumsum(per_entry[:-1], dtype=np.int32, out=first[1:])
        data.view(np.int32)[:, 2] = first

        total = int(per_entry.sum())
        record = self._entry_buffer(slot, count)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, record[0])
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, data.nbytes, data)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        GL.glActiveTexture(GL.GL_TEXTURE0 + _wire_pool.POOL_TEXTURE_UNIT)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, texture)
        GL.glActiveTexture(GL.GL_TEXTURE0 + ENTRY_TEXTURE_UNIT)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, record[1])
        GL.glActiveTexture(GL.GL_TEXTURE0)

        program.twist_pieces = _wire_pool.POOL_TEXTURE_UNIT
        program.twist_entries = ENTRY_TEXTURE_UNIT
        program.twist_entry_count = count
        program.twist_batch = 1

        try:
            GL.glBindVertexArray(self._vao())
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, total)
            GL.glBindVertexArray(0)
        finally:
            program.twist_batch = 0


BATCH = WireBatch()
