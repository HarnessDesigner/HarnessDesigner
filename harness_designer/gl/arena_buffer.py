# (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The GPU side of the pooled arenas, and the idle-time maintenance both pools share.

``arena_pool.py`` is the GL-free bookkeeping and the planner. This module adds:

* :class:`BufferArena`: an :class:`arena_pool.ArenaMap` with a GL buffer. It can move a model to another arena, rebuild itself
  packed down, and be trimmed, all by GPU-to-GPU copies. A subclass says how many bytes a slot is (``STRIDE_BYTES``).
* :class:`ArenaPoolBase`: the mechanics of a pool of such arenas, the same for every pool (the model meshes of ``vbo.py``, the
  wire path rows of ``wire_pool.py``): one ``app.CallLater`` for a burst of changes, guarded by a flag that is set when
  ``CallLater`` is called and cleared when the pass is done; the pass runs under the owner's GL context, plans with
  :func:`arena_pool.plan` and replays the steps on the real buffers. A pool fills in the hooks.
"""

from typing import TYPE_CHECKING

import weakref
from OpenGL import GL
from PySide6 import QtCore

from .. import logger as _logger
from .. import check_types as _check_types
from . import arena_pool as _arena_pool

if TYPE_CHECKING:
    from ..ui import mainframe as _mainframe


class BufferArena(_arena_pool.ArenaMap):
    """One GPU buffer that fixed-size slots (vertices of a mesh, rows of a wire path) are sub-allocated from.

    ``capacity_vertices`` and the other sizes of :class:`arena_pool.ArenaMap` count slots, whatever a slot is.
    """

    # bytes per slot; a subclass sets it
    STRIDE_BYTES: int = 0

    @_check_types.do
    def __init__(self, capacity_vertices: int, tier: int = _arena_pool.TIER_SHORT, uid: int = 0):
        super().__init__(capacity_vertices, tier, uid)

        self._buffer = None
        self._create_buffer()

    @property
    @_check_types.do
    def buffer(self) -> int:
        return int(self._buffer)

    @classmethod
    @_check_types.do
    def _create_empty_array_buffer(cls, capacity_vertices: int) -> int:
        buffer_id = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)

        GL.glBufferData(GL.GL_ARRAY_BUFFER,
                        capacity_vertices * cls.STRIDE_BYTES,
                        None, GL.GL_DYNAMIC_DRAW)

        return int(buffer_id)

    @_check_types.do
    def _create_buffer(self) -> None:
        self._buffer = self._create_empty_array_buffer(self.capacity_vertices)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @_check_types.do
    def _buffer_replaced(self) -> None:
        """Called after ``_rebuild`` put a new buffer in place of the old one; a subclass that points something else at the
        buffer (a texture buffer) points it at the new one here."""

    @_check_types.do
    def debug_metrics(self) -> dict:
        free_ranges = list(self.free_ranges)

        return dict(buffer_id=self._buffer,
                    capacity_vertices=self.capacity_vertices,
                    used_vertices=self.used_vertices,
                    free_vertices=self.free_vertices,
                    allocation_count=len(self.allocations),
                    free_range_count=len(free_ranges),
                    largest_free_range=self.largest_free_range,
                    fragmentation=self.fragmentation,
                    free_ranges=free_ranges,
                    tier=self.tier,
                    locked=self.locked)

    @classmethod
    @_check_types.do
    def _gpu_copy(cls, src_buffer: int, dst_buffer: int, src_slot: int, dst_slot: int, slot_count: int) -> None:
        size = slot_count * cls.STRIDE_BYTES
        read_offset = src_slot * cls.STRIDE_BYTES
        write_offset = dst_slot * cls.STRIDE_BYTES

        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, src_buffer)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, dst_buffer)

        GL.glCopyBufferSubData(GL.GL_COPY_READ_BUFFER, GL.GL_COPY_WRITE_BUFFER,
                               read_offset, write_offset, size)

    @_check_types.do
    def adopt(self, key: str, source: "BufferArena") -> None:
        """Move model *key* from *source* into this arena (GPU to GPU, no CPU round trip)."""
        source_alloc = source.get_allocation(key)
        alloc = self.allocate(key, source_alloc.count)

        self._gpu_copy(source.buffer, self.buffer, source_alloc.start, alloc.start, source_alloc.count)

        source.free(key)

    @_check_types.do
    def _rebuild(self, capacity_vertices: int) -> None:
        """Copy every model, packed down, into a fresh buffer of *capacity_vertices* and drop the old one (a copy inside one
        buffer may not overlap itself, so sliding in place is not possible)."""
        moves = self.slide()
        new_buffer = self._create_empty_array_buffer(capacity_vertices)

        for _key, old_start, new_start, count in moves:
            self._gpu_copy(self._buffer, new_buffer, old_start, new_start, count)

        GL.glDeleteBuffers(1, [self._buffer])

        self._buffer = new_buffer
        self.capacity_vertices = capacity_vertices

        used = self.used_vertices
        if capacity_vertices > used:
            self.free_ranges = [(used, capacity_vertices - used)]
        else:
            self.free_ranges = []

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, 0)

        self._buffer_replaced()

    @_check_types.do
    def compact(self) -> bool:
        if not self.allocations:
            self.free_ranges = [(0, self.capacity_vertices)]
            return False

        self._rebuild(self.capacity_vertices)
        return True

    @_check_types.do
    def trim(self) -> bool:
        """Pack the models down and cut the capacity to what they use."""
        if not self.allocations:
            return False

        self._rebuild(self.used_vertices)
        return True

    @_check_types.do
    def destroy(self) -> None:
        GL.glDeleteBuffers(1, [self._buffer])
        self._buffer = None


class ArenaPoolBase:
    """The mechanics every pool of arenas shares. A pool is a class with class-level state (like ``PooledVBOHandler``), never
    instantiated for this; it mixes this class in and fills in the ``_pool_arenas`` ... ``_log_pass`` hooks.

    A change that a pass could do something about (a model freed, resized, a tier boundary crossed) calls
    ``_request_maintenance``. That asks ``app.CallLater`` for ONE pass, unless one is already asked for: ``_maintenance_pending``
    is set when ``CallLater`` is called and cleared, in a ``finally``, when the pass has ended, however it ended.
    """

    # the main frame that owns the pools; the pass takes its 3D editor's GL context. One for all pools.
    _owner: weakref.ref | None = None

    _maintenance_pending: bool = False

    # set when a change needs a pass whatever the arenas look like (a tier boundary crossed); cleared when a pass has worked
    _dirty: bool = False

    @classmethod
    @_check_types.do
    def set_owner(cls, owner: "_mainframe.MainFrame") -> None:
        """Say which main frame owns the pools. The pass enters ``owner.editor3d.context`` before it touches a buffer; the pools
        import no canvas module, they are handed the instance once at startup."""
        ArenaPoolBase._owner = weakref.ref(owner)

    # ---- hooks -------------------------------------------------------------------------------------------------------

    @classmethod
    @_check_types.do
    def _pool_arenas(cls) -> list[BufferArena]:
        """The pool's list of arenas itself (steps that create or delete an arena add to / remove from it)."""
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _compact_threshold(cls) -> float:
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _compact_min_free(cls) -> int:
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _long_capacity(cls) -> int:
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _short_capacity(cls) -> int:
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _desired_tiers(cls) -> dict[str, int]:
        """The tier each allocation (by key) should be in."""
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _make_arena(cls, op: _arena_pool.ArenaOp) -> BufferArena:
        """Build the arena a ``create`` step names (``op.capacity``, ``op.tier``, and ``op.uid`` as its uid)."""
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _executed(cls, moved: list[tuple[str, BufferArena]], rebuilt: list[BufferArena]) -> None:
        """Called when a plan has been replayed: the pool tells whatever holds an arena or an offset what changed (*moved*: the
        key and the arena it is in now; *rebuilt*: arenas whose buffer or offsets changed), and makes the copies visible to the
        other GL contexts."""
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _log_pass(cls, ops: list[_arena_pool.ArenaOp], before: list, after: list) -> None:
        """Optional debug output of a pass that did something (arena metrics before and after)."""

    # ---- the mechanics ---------------------------------------------------------------------------------------------------

    @classmethod
    @_check_types.do
    def _maintenance_wanted(cls) -> bool:
        """A cheap check: is there anything a pass would do. (The pass itself plans the details and may find nothing.)"""
        if cls._dirty:
            return True

        arenas = cls._pool_arenas()

        for arena in arenas:
            if not arena.allocations:
                return True

            if arena.tier == _arena_pool.TIER_LONG and arena.locked and arena.free_vertices > 0:
                return True

            if arena.should_compact(cls._compact_threshold(), cls._compact_min_free()):
                return True

        for tier in (_arena_pool.TIER_SHORT, _arena_pool.TIER_LONG):
            of_tier = [arena for arena in arenas if arena.tier == tier]
            if len(of_tier) < 2:
                continue

            free_total = sum(arena.free_vertices for arena in of_tier if not arena.locked)

            for arena in of_tier:
                # what the other arenas of the tier could take in (a locked arena takes nothing)
                if arena.locked:
                    others = free_total
                else:
                    others = free_total - arena.free_vertices

                if arena.used_vertices <= others:
                    return True

        return False

    @classmethod
    @_check_types.do
    def _request_maintenance(cls) -> None:
        """Ask for one pass at idle time with ``app.CallLater``, if one is needed and none is already asked for."""
        if cls._maintenance_pending:
            return

        qt_app = QtCore.QCoreApplication.instance()
        if qt_app is None:
            return

        # imported here: app.py imports the whole application, and this module is imported long before it
        from .. import app as _app

        if QtCore.QThread.currentThread() != qt_app.thread():
            # the last reference to something pooled can be dropped on any thread, and a timer needs the main thread's event loop
            _app.CallAfter(cls._request_maintenance)
            return

        try:
            wanted = cls._maintenance_wanted()
        except Exception as err:  # NOQA
            _logger.traceback(err, f'{cls.__name__} arena maintenance check failed')
            return

        if not wanted:
            return

        cls._maintenance_pending = True
        _app.CallLater(cls._run_maintenance)

    @classmethod
    @_check_types.do
    def _run_maintenance(cls) -> None:
        """The callback ``app.CallLater`` runs: take the owner's GL context, plan, and run the plan."""
        try:
            if ArenaPoolBase._owner is None:
                raise RuntimeError('set_owner() has not been called')

            with ArenaPoolBase._owner().editor3d.context:
                cls._maintain()

            # only once the pass has worked: one that failed leaves the request standing for the next trigger
            cls._dirty = False
        except Exception as err:  # NOQA
            _logger.traceback(err, f'{cls.__name__} arena maintenance failed')
        finally:
            cls._maintenance_pending = False

    @classmethod
    @_check_types.do
    def _maintain(cls) -> bool:
        """One pass: plan, replay. Needs the GL context."""
        ops = _arena_pool.plan(cls._pool_arenas(), cls._desired_tiers(), cls._long_capacity(), cls._short_capacity(),
                               cls._compact_threshold(), cls._compact_min_free())

        if not ops:
            return False

        before = [arena.debug_metrics() for arena in cls._pool_arenas()]
        cls._execute(ops)
        after = [arena.debug_metrics() for arena in cls._pool_arenas()]

        cls._log_pass(ops, before, after)
        return True

    @classmethod
    @_check_types.do
    def _execute(cls, ops: list[_arena_pool.ArenaOp]) -> None:
        pool = cls._pool_arenas()
        arenas = {arena.uid: arena for arena in pool}
        rebuilt: dict[int, BufferArena] = {}
        moved: list[tuple[str, BufferArena]] = []

        for op in ops:
            if op.kind == 'create':
                arena = cls._make_arena(op)
                pool.append(arena)
                arenas[op.uid] = arena
            elif op.kind == 'slide':
                arenas[op.uid].compact()
                rebuilt[op.uid] = arenas[op.uid]
            elif op.kind == 'move':
                target = arenas[op.uid]
                target.adopt(op.key, arenas[op.src])
                moved.append((op.key, target))
            elif op.kind == 'lock':
                arenas[op.uid].locked = True
            elif op.kind == 'trim':
                arenas[op.uid].trim()
                rebuilt[op.uid] = arenas[op.uid]
            elif op.kind == 'delete':
                arena = arenas.pop(op.uid)
                arena.destroy()
                pool.remove(arena)
                rebuilt.pop(op.uid, None)
            else:
                raise ValueError(f'unknown arena step {op.kind!r}')

        cls._executed(moved, list(rebuilt.values()))
