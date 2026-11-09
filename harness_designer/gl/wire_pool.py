# (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The pool of wire path rows: the GPU holds every wire's path, and a wire is drawn with one call.

A twisted wire is a path of pieces (the straights and the chords of its rounded bends). Drawing it through the faces program's
twist mode used to take one draw call per piece, each setting about 17 uniforms: 0.85 ms of CPU per wire per frame, growing with
every wire (TWISTED_WIRE_DESIGN.md has the measurements). Here the pieces of a wire are rows of a texture buffer, written when
the path changes, and the vertex shader reads its piece from them (``loadPiece`` in ``faces/vertex.vert``, reached through the
batch of ``gl/wire_batch.py``, which draws every wire of a frame with one call).

A row is 5 RGBA32F texels (80 bytes):

* 0: the piece's start position (x, y, z) and its length
* 1: its rotation quaternion (w, x, y, z)
* 2: the twist phase, the ring count, the first vertex of the piece within the wire's draw (an int, stored as its bits) and 0
* 3: the mitre at the start (x, y, z, fade distance)
* 4: the mitre at the end

The first-vertex value is relative to the wire, so a wire's rows mean the same wherever they sit and can be moved between and
within arenas by plain copies. ``WirePool`` is an :class:`arena_buffer.ArenaPoolBase`: the arenas are packed, drained and compacted at
idle time exactly as the model arenas of ``vbo.py`` are (every wire arena is a short-term one: they compact and are never
trimmed or locked).
"""

import itertools

import numpy as np
from OpenGL import GL

from .. import check_types as _check_types
from . import arena_pool as _arena_pool
from . import arena_buffer as _arena_buffer


ROW_FLOATS = 20
ROW_BYTES = ROW_FLOATS * 4
TEXELS_PER_ROW = 5

# Rows in a new arena (more when one wire needs more): 8 MB, room for a couple of thousand wires, so a frame normally draws
# its wires from one arena and ``wire_batch`` draws them with one call. A texture buffer must hold at least 65,536 texels (GL 3.1's
# minimum, NVIDIA allows far more) and a row is 5 of them; ``WirePool._rows_limit`` asks the driver for the real size and the
# arena is cut down to it.
WIRE_ARENA_ROWS = 100000

# Fragmentation at which a wire arena is compacted, and the free rows it needs before that is worth doing.
WIRE_ARENA_FRAGMENTATION_THRESHOLD = 0.35
WIRE_ARENA_MIN_FREE_ROWS = 256

# The texture unit the pool's texture buffer is bound to while a wire is drawn.
POOL_TEXTURE_UNIT = 4

_KEYS = itertools.count(1)


@_check_types.do
def new_key() -> str:
    """A key for one wire's rows in the pool; never reused."""
    return f'wire{next(_KEYS)}'


class WireArena(_arena_buffer.BufferArena):
    """One GPU buffer of wire path rows, read through a texture buffer; a slot is a row."""

    STRIDE_BYTES: int = ROW_BYTES

    @_check_types.do
    def __init__(self, capacity_vertices: int, tier: int = _arena_pool.TIER_SHORT, uid: int = 0):
        super().__init__(capacity_vertices, tier, uid)

        self._texture = int(GL.glGenTextures(1))
        self._point_texture()

    @property
    @_check_types.do
    def texture(self) -> int:
        return self._texture

    @_check_types.do
    def _point_texture(self) -> None:
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, self._texture)
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER, GL.GL_RGBA32F, self._buffer)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER, 0)

    @_check_types.do
    def _buffer_replaced(self) -> None:
        self._point_texture()

    @_check_types.do
    def upload(self, key: str, rows: np.ndarray) -> None:
        alloc = self.allocations[key]

        if rows.shape != (alloc.count, ROW_FLOATS):
            raise ValueError(f'the rows do not match the allocation: expected {(alloc.count, ROW_FLOATS)}, got {rows.shape}')

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, alloc.start * ROW_BYTES, rows.nbytes, rows)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @_check_types.do
    def destroy(self) -> None:
        super().destroy()
        GL.glDeleteTextures([self._texture])
        self._texture = 0


class WirePool(_arena_buffer.ArenaPoolBase):
    """Every wire's path rows. Class-level state, like ``PooledVBOHandler``; never instantiated."""

    _arenas: list[WireArena] = []

    # which arena a wire's rows are in, and how many vertices the wire's draw has
    _where: dict[str, WireArena] = {}
    _vertices: dict[str, int] = {}

    # rows a texture buffer can hold; asked of the driver the first time it is needed
    _limit_rows: int = 0

    # A number for each wire that changes whenever the wire's place in the pool or the number of vertices of its draw does (it is
    # written to a new place, resized, or an arena is rebuilt under it). Whatever a wire derived from ``locate`` (the entries of
    # ``wire_batch``) is good for as long as the stamp is the one it was made at.
    _stamp: dict[str, int] = {}
    _ticks: int = 0

    @staticmethod
    @_check_types.do
    def pack(positions: np.ndarray, quats: np.ndarray, lengths: np.ndarray, phases: np.ndarray, start_mitres: np.ndarray,
             end_mitres: np.ndarray, rings: np.ndarray, band_vertices: int) -> tuple[np.ndarray, int]:
        """The rows of a path, from the arrays ``shapes.twisted_path.build_path`` returns.

        :param band_vertices: Vertices between one ring and the next (``SIDES * 6`` in ``faces/vertex.vert``).
        :returns: The ``(pieces, 20)`` float32 rows, and the number of vertices the wire's draw has.
        """
        count = len(lengths)
        rows = np.zeros((count, ROW_FLOATS), dtype=np.float32)

        rows[:, 0:3] = positions
        rows[:, 3] = lengths
        rows[:, 4:8] = quats
        rows[:, 8] = phases
        rows[:, 9] = rings
        rows[:, 12:16] = start_mitres
        rows[:, 16:20] = end_mitres

        vertices = (rings.astype(np.int64) - 1) * band_vertices

        first = np.zeros(count, dtype=np.int32)
        np.cumsum(vertices[:-1], dtype=np.int32, out=first[1:])
        rows.view(np.int32)[:, 10] = first

        return rows, int(vertices.sum())

    @classmethod
    @_check_types.do
    def _rows_limit(cls) -> int:
        if cls._limit_rows == 0:
            cls._limit_rows = int(GL.glGetIntegerv(GL.GL_MAX_TEXTURE_BUFFER_SIZE)) // TEXELS_PER_ROW

        return cls._limit_rows

    @classmethod
    @_check_types.do
    def _allocate(cls, key: str, count: int) -> WireArena:
        limit = cls._rows_limit()
        if count > limit:
            raise ValueError(f'a wire of {count} pieces does not fit in a texture buffer ({limit} rows)')

        for arena in cls._arenas:
            if arena.can_fit(count):
                arena.allocate(key, count)
                return arena

        # enough free rows, but not in one block
        for arena in cls._arenas:
            if arena.should_compact(WIRE_ARENA_FRAGMENTATION_THRESHOLD, WIRE_ARENA_MIN_FREE_ROWS, count):
                if arena.compact() and arena.can_fit(count):
                    cls._restamp(arena)
                    arena.allocate(key, count)
                    return arena

        arena = WireArena(max(min(WIRE_ARENA_ROWS, limit), count))
        cls._arenas.append(arena)
        arena.allocate(key, count)
        return arena

    @classmethod
    @_check_types.do
    def set_rows(cls, key: str, rows: np.ndarray, vertices: int) -> None:
        """Write a wire's rows (``pack``) into the pool, in place when the wire has the same number of pieces as before.
        Needs the GL context."""
        count = len(rows)
        arena = cls._where.get(key)
        resized = False

        if arena is not None and arena.get_allocation(key).count != count:
            arena.free(key)
            del cls._where[key]
            arena = None
            resized = True

        if arena is None:
            arena = cls._allocate(key, count)
            cls._where[key] = arena

        arena.upload(key, rows)

        if resized or cls._vertices.get(key) != vertices or key not in cls._stamp:
            cls._touch(key)

        cls._vertices[key] = vertices

        if resized:
            cls._request_maintenance()

    @classmethod
    @_check_types.do
    def release(cls, key: str) -> None:
        """A wire is gone: its rows are free to reuse. (Bookkeeping only, no GL; the space is reclaimed at idle time.)"""
        arena = cls._where.pop(key, None)
        if arena is None:
            return

        arena.free(key)
        cls._vertices.pop(key, None)
        cls._stamp.pop(key, None)

        cls._request_maintenance()

    @classmethod
    @_check_types.do
    def _touch(cls, key: str) -> None:
        cls._ticks += 1
        cls._stamp[key] = cls._ticks

    @classmethod
    @_check_types.do
    def _restamp(cls, arena: _arena_buffer.BufferArena) -> None:
        """Every wire in *arena* has been moved within it."""
        for key in arena.allocations:
            cls._touch(key)

    @classmethod
    def stamp(cls, key: str) -> int:
        """The wire's stamp (see ``_stamp``). Called once per wire per frame, so not wrapped in ``check_types.do``."""
        return cls._stamp[key]

    @classmethod
    @_check_types.do
    def locate(cls, key: str) -> tuple[int, int, int, int]:
        """Where to draw a wire from: the texture buffer's texture, its first row, its rows, and the vertices of its draw."""
        arena = cls._where[key]
        alloc = arena.get_allocation(key)
        return arena.texture, alloc.start, alloc.count, cls._vertices[key]

    # ---- arena_buffer.ArenaPoolBase hooks ----

    @classmethod
    @_check_types.do
    def _pool_arenas(cls) -> list[_arena_buffer.BufferArena]:
        return cls._arenas

    @classmethod
    @_check_types.do
    def _compact_threshold(cls) -> float:
        return WIRE_ARENA_FRAGMENTATION_THRESHOLD

    @classmethod
    @_check_types.do
    def _compact_min_free(cls) -> int:
        return WIRE_ARENA_MIN_FREE_ROWS

    @classmethod
    @_check_types.do
    def _long_capacity(cls) -> int:
        return WIRE_ARENA_ROWS

    @classmethod
    @_check_types.do
    def _short_capacity(cls) -> int:
        return WIRE_ARENA_ROWS

    @classmethod
    @_check_types.do
    def _desired_tiers(cls) -> dict[str, int]:
        # no tiers for wires: they change too often to be worth trimming; every arena packs and compacts
        desired: dict[str, int] = {}

        for arena in cls._arenas:
            for key in arena.allocations:
                desired[key] = _arena_pool.TIER_SHORT

        return desired

    @classmethod
    @_check_types.do
    def _make_arena(cls, op: _arena_pool.ArenaOp) -> _arena_buffer.BufferArena:
        return WireArena(op.capacity, op.tier, op.uid)

    @classmethod
    @_check_types.do
    def _executed(cls, moved: list[tuple[str, _arena_buffer.BufferArena]], rebuilt: list[_arena_buffer.BufferArena]) -> None:
        # The draw looks a wire up by key every time (nothing bakes an offset), and a rebuilt arena's texture buffer was
        # pointed at its new buffer when it was rebuilt; only the arena a wire is in has to be recorded.
        for key, target in moved:
            cls._where[key] = target
            cls._touch(key)

        for arena in rebuilt:
            cls._restamp(arena)

        GL.glFlush()
