# (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The outline a selected wire, bundle or cable casts on the floor (WAYPOINT_REWORK_DESIGN.md).

Looking at the object from straight above (along -Y) and tracing the outline of what is seen gives the shape of its path: the
path as drawn (rounded corners), a tube wide, projected onto the floor plane. :func:`silhouette_loops` makes that outline from the
chords of the drawn path (``TubeMixin._curve_chords``), :func:`outline_vertices` turns the loops into thin flat strips lying on the
floor, and ``FLOOR_OUTLINE.draw`` draws them with the faces program.

Everything here but the draw is plain numpy.
"""

import ctypes

import numpy as np
from OpenGL import GL
from PySide6 import QtGui

from .. import check_types as _check_types


# Two chords whose ends are closer than this belong to one continuous run of the path (a stretch hidden inside a bundle leaves a gap).
_JOIN_GAP_MM = 0.01

# A point of the path that is closer than this to the one before it, seen from above, is dropped (a vertical piece has no length in plan).
_PLAN_GAP_MM = 1e-3

# A corner's offset is the mitre of its two sides' offsets; it is never longer than this many radii (a hairpin would spike).
_MITRE_LIMIT = 3.0

# Points of the circle drawn for a path that is vertical from end to end.
_CIRCLE_POINTS = 24

# Floats of a vertex: position, smooth normal, face normal.
_FLOATS_PER_VERTEX = 9


@_check_types.do
def silhouette_loops(chords: list[tuple[np.ndarray, np.ndarray]], radius: float) -> list[np.ndarray]:
    """The outline of the path seen from above.

    :param chords: ``(start, end)`` of each straight piece of the drawn path, in world space, in path order.
    :param radius: Half the width of the tube, mm.
    :returns: One closed loop per continuous run of the path: ``(n, 2)`` points (world x and z), the left side out and the right
        side back.
    """
    if not chords:
        return []

    runs = []
    current = [np.asarray(chords[0][0], dtype=np.float64), np.asarray(chords[0][1], dtype=np.float64)]

    for start, end in chords[1:]:
        start = np.asarray(start, dtype=np.float64)

        if float(np.linalg.norm(start - current[-1])) < _JOIN_GAP_MM:
            current.append(np.asarray(end, dtype=np.float64))
        else:
            runs.append(current)
            current = [start, np.asarray(end, dtype=np.float64)]

    runs.append(current)

    loops = []

    for run in runs:
        plan = np.array(run)[:, [0, 2]]
        keep = [0]

        for i in range(1, len(plan)):
            if float(np.linalg.norm(plan[i] - plan[keep[-1]])) > _PLAN_GAP_MM:
                keep.append(i)

        plan = plan[keep]

        if len(plan) < 2:
            angles = np.linspace(0.0, 2.0 * np.pi, _CIRCLE_POINTS, endpoint=False)
            loops.append(plan[0] + radius * np.stack([np.cos(angles), np.sin(angles)], axis=1))
            continue

        along = plan[1:] - plan[:-1]
        along /= np.linalg.norm(along, axis=1)[:, None]
        sides = np.stack([-along[:, 1], along[:, 0]], axis=1)

        offsets = np.empty_like(plan)
        offsets[0] = sides[0]
        offsets[-1] = sides[-1]

        for i in range(1, len(plan) - 1):
            mitre = sides[i - 1] + sides[i]
            length = float(np.linalg.norm(mitre))

            if length < 1e-6:
                offsets[i] = sides[i]
                continue

            mitre /= length
            offsets[i] = mitre * min(1.0 / max(float(np.dot(mitre, sides[i])), 1e-3), _MITRE_LIMIT)

        loops.append(np.vstack([plan + offsets * radius, (plan - offsets * radius)[::-1]]))

    return loops


@_check_types.do
def outline_vertices(loops: list[np.ndarray], line_width: float, y: float) -> np.ndarray:
    """Triangles for the loops as lines *line_width* wide lying flat at height *y*, both sides facing (the draw does not know
    which way the camera looks).

    :returns: ``(n, 9)`` float32: position, smooth normal and face normal (both straight up) of each vertex.
    """
    half = line_width * 0.5
    quads = []

    for loop in loops:
        starts = loop
        ends = np.roll(loop, -1, axis=0)
        along = ends - starts
        lengths = np.linalg.norm(along, axis=1)
        valid = lengths > 1e-6

        if not valid.any():
            continue

        starts = starts[valid]
        ends = ends[valid]
        along = along[valid] / lengths[valid][:, None]
        sides = np.stack([-along[:, 1], along[:, 0]], axis=1) * half

        quads.append(np.stack([starts + sides, starts - sides, ends - sides, ends + sides], axis=1))

    if not quads:
        return np.zeros((0, _FLOATS_PER_VERTEX), dtype=np.float32)

    corners = np.concatenate(quads)
    count = len(corners)
    plan = np.empty((count, 12, 2), dtype=np.float64)

    # (0 1 2) (0 2 3) facing one way, then the same reversed
    for slot, index in enumerate((0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2)):
        plan[:, slot] = corners[:, index]

    plan = plan.reshape(-1, 2)

    vertices = np.zeros((len(plan), _FLOATS_PER_VERTEX), dtype=np.float32)
    vertices[:, 0] = plan[:, 0]
    vertices[:, 1] = y
    vertices[:, 2] = plan[:, 1]
    vertices[:, 4] = 1.0
    vertices[:, 7] = 1.0
    return vertices


class FloorOutline:
    """Draws the outline triangles with the faces program. One instance (``FLOOR_OUTLINE``) serves every canvas: the buffer is
    shared by the canvases' contexts, a vertex array is made per context."""

    def __init__(self):
        self._buffer = 0
        self._capacity = 0
        self._vaos: dict[int, int] = {}

    @_check_types.do
    def _vao(self) -> int:
        context = QtGui.QOpenGLContext.currentContext()
        if context is None:
            raise RuntimeError('context has not been acquired')

        key = id(context)

        if key not in self._vaos:
            if self._buffer == 0:
                self._buffer = int(GL.glGenBuffers(1))

            stride = _FLOATS_PER_VERTEX * 4
            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)

            for location in range(3):
                GL.glEnableVertexAttribArray(location)
                GL.glVertexAttribPointer(location, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(location * 12))

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
            GL.glBindVertexArray(0)
            self._vaos[key] = vao

        return self._vaos[key]

    @_check_types.do
    def draw(self, program: object, material: object, vertices: np.ndarray) -> None:
        """Draw *vertices* (:func:`outline_vertices`) in *material*. Needs the GL context.

        :param program: The faces program (``gl.shaders.program.FacesProgram``); entered here.
        """
        if not len(vertices):
            return

        vao = self._vao()

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STREAM_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        with program:
            program.stripe_clip_start = 0.0
            program.stripe_clip_stop = 0.0
            program.position = (0.0, 0.0, 0.0)
            program.rotation = [1.0, 0.0, 0.0, 0.0]
            program.scale = (1.0, 1.0, 1.0)
            material.set(program)

            GL.glBindVertexArray(vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(vertices))
            GL.glBindVertexArray(0)


FLOOR_OUTLINE = FloorOutline()
