# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import ctypes
import weakref
from dataclasses import dataclass

import numpy as np
from OpenGL import GL
from PySide6.QtGui import QOpenGLContext

from .. import config as _config
from .. import logger as _logger
from .. import utils as _utils
from ..geometry import point as _point


# Maximum triangle-soup vertices managed in the imported-model arena.
MODEL_ARENA_CAPACITY_VERTICES = 4000000
# Compaction threshold: rebuild arena when free-space fragmentation reaches this ratio.
MODEL_ARENA_FRAGMENTATION_THRESHOLD = 0.35
# Avoid rebuilding for tiny holes until at least this many vertices are reclaimable.
MODEL_ARENA_MIN_FREE_VERTICES = 4096

_FLOAT_SIZE = np.dtype(np.float32).itemsize

# Geometry is stored as one packed array per mesh:
# [positions | smooth normals | face normals], each block count*3 floats.
# Every vertex therefore occupies 9 floats of buffer storage.
FLOATS_PER_VERTEX = 9
VERTEX_STRIDE_BYTES = FLOATS_PER_VERTEX * _FLOAT_SIZE

Config = _config.Config


@dataclass
class _ArenaAllocation:
    start: int
    count: int


class _MeshArena:

    def __init__(self, capacity_vertices: int):
        self.capacity_vertices = int(capacity_vertices)
        self._allocations: dict[str, _ArenaAllocation] = {}
        self._free_ranges: list[tuple[int, int]] = [(0, self.capacity_vertices)]

        self._buffer = None
        self._create_buffer()

    @property
    def buffer(self) -> int:
        return self._buffer

    def _create_empty_array_buffer(self) -> int:
        buffer_id = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)

        GL.glBufferData(GL.GL_ARRAY_BUFFER,
                        self.capacity_vertices * VERTEX_STRIDE_BYTES,
                        None, GL.GL_DYNAMIC_DRAW)

        return buffer_id

    def _create_buffer(self):
        self._buffer = self._create_empty_array_buffer()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def get_allocation(self, key: str) -> _ArenaAllocation | None:
        return self._allocations.get(key)

    def can_fit(self, vertex_count: int) -> bool:
        needed = int(vertex_count)
        if needed <= 0:
            return False

        return any(count >= needed for _, count in self._free_ranges)

    def allocate(self, key: str, vertex_count: int) -> _ArenaAllocation:
        if key in self._allocations:
            return self._allocations[key]

        needed = int(vertex_count)
        if needed <= 0:
            raise ValueError('vertex_count must be > 0')

        for index, (start, count) in enumerate(self._free_ranges):
            if count < needed:
                continue

            alloc = _ArenaAllocation(start=start, count=needed)
            self._allocations[key] = alloc

            if count == needed:
                del self._free_ranges[index]
            else:
                self._free_ranges[index] = (start + needed, count - needed)

            return alloc

        free_total = self.free_vertices
        raise RuntimeError('model mesh arena has no contiguous free range large enough: '
                           f'requested {needed} vertices, '
                           f'largest hole {self.largest_free_range}, '
                           f'total free {free_total}, '
                           f'capacity {self.capacity_vertices}')

    def free(self, key: str):
        alloc = self._allocations.pop(key, None)
        if alloc is None:
            return

        self._free_ranges.append((alloc.start, alloc.count))
        self._free_ranges.sort(key=lambda item: item[0])

        merged: list[tuple[int, int]] = []
        for start, count in self._free_ranges:
            if not merged:
                merged.append((start, count))
                continue

            prev_start, prev_count = merged[-1]
            prev_end = prev_start + prev_count
            if prev_end == start:
                merged[-1] = (prev_start, prev_count + count)
            else:
                merged.append((start, count))

        self._free_ranges = merged

    def upload(self, key: str, data: np.ndarray):
        alloc = self._allocations[key]

        if len(data) != alloc.count * FLOATS_PER_VERTEX:
            raise ValueError('packed array length does not match the allocation: '
                             f'expected {alloc.count * FLOATS_PER_VERTEX} floats, '
                             f'got {len(data)}')

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)

        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, alloc.start * VERTEX_STRIDE_BYTES,
                           data.nbytes, data)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @property
    def fragmentation(self) -> float:
        if not self._free_ranges:
            return 0.0

        free_total = sum(count for _, count in self._free_ranges)
        if free_total <= 0:
            return 0.0

        largest_hole = max(count for _, count in self._free_ranges)
        return 1.0 - (largest_hole / float(free_total))

    @property
    def free_vertices(self) -> int:
        return sum(count for _, count in self._free_ranges)

    @property
    def used_vertices(self) -> int:
        return sum(alloc.count for alloc in self._allocations.values())

    @property
    def largest_free_range(self) -> int:
        if not self._free_ranges:
            return 0

        return max(count for _, count in self._free_ranges)

    def debug_metrics(self) -> dict:
        free_ranges = list(self._free_ranges)

        return dict(buffer_id=self._buffer,
                    capacity_vertices=self.capacity_vertices,
                    used_vertices=self.used_vertices,
                    free_vertices=self.free_vertices,
                    allocation_count=len(self._allocations),
                    free_range_count=len(free_ranges),
                    largest_free_range=self.largest_free_range,
                    fragmentation=self.fragmentation,
                    free_ranges=free_ranges)

    def should_compact(self, threshold: float = MODEL_ARENA_FRAGMENTATION_THRESHOLD,
                       min_free_vertices: int = MODEL_ARENA_MIN_FREE_VERTICES,
                       needed_vertices: int = 0) -> bool:

        needed = int(needed_vertices)

        if 0 < needed <= self.largest_free_range:
            return False

        return (self.free_vertices >= int(min_free_vertices) and
                self.fragmentation >= float(threshold))

    @staticmethod
    def _gpu_copy(src_buffer: int, dst_buffer: int, src_vertex: int,
                  dst_vertex: int, vertex_count: int):

        size = vertex_count * VERTEX_STRIDE_BYTES
        read_offset = src_vertex * VERTEX_STRIDE_BYTES
        write_offset = dst_vertex * VERTEX_STRIDE_BYTES

        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, src_buffer)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, dst_buffer)

        GL.glCopyBufferSubData(GL.GL_COPY_READ_BUFFER, GL.GL_COPY_WRITE_BUFFER,
                               read_offset, write_offset, size)

    def compact(self) -> bool:
        if not self._allocations:
            self._free_ranges = [(0, self.capacity_vertices)]
            return False

        new_buffer = self._create_empty_array_buffer()

        sorted_items = sorted(
            self._allocations.items(), key=lambda item: item[1].start)

        cursor = 0
        for key, alloc in sorted_items:
            self._gpu_copy(
                self._buffer, new_buffer, alloc.start, cursor, alloc.count)

            self._allocations[key] = (
                _ArenaAllocation(start=cursor, count=alloc.count))

            cursor += alloc.count

        GL.glDeleteBuffers(1, [self._buffer])

        self._buffer = new_buffer

        self._free_ranges = []
        if cursor < self.capacity_vertices:
            self._free_ranges.append((cursor, self.capacity_vertices - cursor))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, 0)
        return True


VBO_TYPE_PRIMITIVE = 0
VBO_TYPE_MODEL = 1


class VBOSingleton(type):
    _instances = {}
    _primitives = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        PooledVBOHandler.release_model_allocation(key)

        del cls._instances[key]

    def __contains__(cls, item):
        if item in cls._instances:
            return True

        return item in cls._primitives

    def __call__(cls, id_: str, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None,
                 arena_kind: int = VBO_TYPE_MODEL) -> "PooledVBOHandler":

        if arena_kind == VBO_TYPE_PRIMITIVE:
            if id_ not in cls._primitives:
                instance = super().__call__(
                    id_, data, count, aabb, obb,
                    endpoint=endpoint, arena_kind=arena_kind)

                cls._primitives[id_] = instance
            else:
                instance = cls._primitives[id_]

        elif id_ not in cls._instances or cls._instances[id_]() is None:
            instance = super().__call__(
                    id_, data, count, aabb, obb,
                    endpoint=endpoint, arena_kind=arena_kind)

            cls._instances[id_] = weakref.ref(instance, cls._remove_ref)

        else:
            instance = cls._instances[id_]()

        return instance


class VBOHandlerBase:

    def __init__(self, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None):
        _ = self.ctx

        if data is None:
            raise ValueError('packed mesh data is required')

        self._vbo = None

        self.endpoint = endpoint

        self._vaos: dict[int, int] = {}
        self._data = data
        self._vert_count = self._normalize_vertex_count(count, len(data))

        if aabb is None:
            self.local_aabb = self._compute_local_aabb()
        else:
            self.local_aabb = np.asarray(aabb, dtype=np.float32).reshape(2, 3)

        if obb is None:
            self.local_obb = self._compute_local_obb()
        else:
            self.local_obb = np.asarray(obb, dtype=np.float32).reshape(8, 3)

    def _compute_local_aabb(self):
        # Bounding volumes are calculated once when a model is converted
        # and stored in the database; only primitives (and legacy rows
        # without stored bounds) compute them from the mesh here.
        p1, p2 = _utils.compute_aabb(self.vertices.reshape(-1, 3))

        local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float32)
        return local_aabb

    def _compute_local_obb(self):
        local_aabb = self._compute_local_aabb().reshape(2, 3)
        p1 = _point.Point(*[float(str(item)) for item in local_aabb[0].tolist()])
        p2 = _point.Point(*[float(str(item)) for item in local_aabb[1].tolist()])

        local_obb = _utils.compute_obb(p1, p2)

        return local_obb

    @staticmethod
    def _normalize_vertex_count(count: int, array_len: int) -> int:
        if array_len % FLOATS_PER_VERTEX != 0:
            raise ValueError('packed array length must be divisible by '
                             f'{FLOATS_PER_VERTEX}')

        vert_count = array_len // FLOATS_PER_VERTEX

        count = int(count)
        # Tolerate legacy counts expressed as float counts (count * 9) or
        # flattened position counts (count * 3).
        if count > 0 and count not in (
            vert_count, vert_count * 3, vert_count * FLOATS_PER_VERTEX
        ):
            raise ValueError(f'vertex count {count} does not match the '
                             f'packed array ({vert_count} vertices)')

        return vert_count

    @classmethod
    def _log_debug(cls, *args):
        logger = _logger.logger
        logger.debug_block(*args)

    @staticmethod
    def _is_vbo_debug_enabled() -> bool:
        try:
            return bool(Config.logging.log_debug)
        except Exception:  # NOQA
            return False

    @property
    def is_dirty(self):
        return False

    def _attribute_offsets(self) -> tuple[int, int, int, int]:
        raise NotImplementedError

    @classmethod
    def _create_vbo(cls, data):
        raise NotImplementedError

    def _clear_vaos(self):
        for vao in self._vaos.values():
            self._release_vao(vao)

        self._vaos.clear()

    @property
    def ctx(self):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        return ctx

    def release(self):
        ctx = self.ctx
        ctx_id = id(ctx)

        vao = self._vaos.pop(ctx_id, None)
        if vao is not None:
            self._release_vao(vao)

    @staticmethod
    def _release_vao(vao):
        if vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [vao])
            except Exception:  # NOQA
                pass

    @staticmethod
    def _release_vbo(vbo=None):
        if vbo is not None:
            try:
                GL.glDeleteBuffers(1, [vbo])
            except Exception:  # NOQA
                pass

    def get_aspect(self) -> tuple[float, float]:
        p1, p2 = self.local_aabb

        x1, y1, z1 = float(p1[0]), float(p1[1]), float(p1[2])
        x2, y2, z2 = float(p2[0]), float(p2[1]), float(p2[2])

        width = x2 - x1
        height = y2 - y1
        length = z2 - z1

        w_h_aspect = width / height
        w_l_aspect = width / length
        h_l_aspect = height / length

        return w_h_aspect, w_l_aspect, h_l_aspect

    @property
    def data(self):
        return self._data

    @property
    def vertices(self):
        return self._data[:self._vert_count * 3]

    @property
    def smooth_normals(self):
        return self._data[self._vert_count * 3:self._vert_count * 6]

    @property
    def face_normals(self):
        return self._data[self._vert_count * 6:]

    @property
    def vertex_count(self) -> int:
        return self._vert_count

    @property
    def faces(self):
        return None

    def render(self):
        ctx = self.ctx
        ctx_id = id(ctx)
        if ctx_id not in self._vaos:
            self.acquire()

        # Attribute offsets (including the arena allocation base) are baked
        # into the VAO, so drawing always starts at vertex 0.  Compaction
        # moves allocations but also clears the affected VAOs, which forces
        # a re-acquire with fresh offsets.
        vao = self._vaos[ctx_id]
        GL.glBindVertexArray(vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._vert_count)
        GL.glBindVertexArray(0)

    def acquire(self):
        ctx = self.ctx

        ctx_id = id(ctx)
        if ctx_id in self._vaos:
            return

        (buffer_id, pos_offset, smooth_offset, face_offset) = self._attribute_offsets()

        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)

        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(pos_offset))

        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(smooth_offset))

        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(face_offset))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

        self._vaos[ctx_id] = vao


class NonPooledVBOHandler(VBOHandlerBase):
    def __init__(self, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None):

        super().__init__(data, count, aabb, obb, endpoint=endpoint)
        self._vbo = self._create_vbo(self._data)
        self._dirty_vaos = {}

    def release(self):
        super().release()

        if self._vaos:
            return

        self._release_vbo(self._vbo)
        self._vbo = None

    def _attribute_offsets(self) -> tuple[int, int, int, int]:
        """Return (buffer id, position/smooth/face byte offsets)."""
        count = self._vert_count
        buffer_id = self._vbo
        base = 0

        block_size = count * 3 * _FLOAT_SIZE

        return buffer_id, base, base + block_size, base + 2 * block_size

    def acquire(self):
        ctx = self.ctx
        ctx_id = id(ctx)

        if ctx_id not in self._vaos:
            self._dirty_vaos[ctx_id] = False

        super().acquire()

    @classmethod
    def _create_vbo(cls, data, vbo=None):
        if vbo is None:
            vbo = GL.glGenBuffers(1)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbo(vbo)

            raise RuntimeError(f"OpenGL error creating mesh buffer: {err}")

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        return vbo

    def update(self, data: np.ndarray, count: int) -> None:
        self._data = data
        self._vert_count = self._normalize_vertex_count(count, len(data))

        self._create_vbo(data, self._vbo)

        for ctx_id in list(self._dirty_vaos.keys())[:]:
            self._dirty_vaos[ctx_id] = True

        self.local_aabb = self._compute_local_aabb()
        self.local_obb = self._compute_local_obb()

    def _rebuild(self):
        ctx = self.ctx
        ctx_id = id(ctx)

        if ctx_id not in self._dirty_vaos:
            self.acquire()

        if not self._dirty_vaos[ctx_id]:
            return

        (buffer_id, pos_offset,
         smooth_offset, face_offset) = self._attribute_offsets()

        vao = self._vaos[ctx_id]

        GL.glBindVertexArray(vao)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)

        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(pos_offset))

        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(smooth_offset))

        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(face_offset))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

        self._dirty_vaos[ctx_id] = False

    @property
    def is_dirty(self):
        ctx = self.ctx

        ctx_id = id(ctx)
        return self._dirty_vaos.get(ctx_id, True)

    def render(self):
        self._rebuild()

        super().render()


class PooledVBOHandler(VBOHandlerBase, metaclass=VBOSingleton):
    _model_arenas: list[_MeshArena] = []

    def __init__(self, id_: str, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None,
                 arena_kind: int = VBO_TYPE_MODEL):

        super().__init__(data, count, aabb, obb, endpoint=endpoint)

        self.id = id_
        self._arena_kind = arena_kind

        self._model_arena: _MeshArena | None = None

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._allocate_model_arena(self.id, self._vert_count)

            arena.upload(self.id, self._data)

            self._model_arena = arena
        else:
            self._vbo = self._create_vbo(self._data)

    @staticmethod
    def _format_arena_metrics(title: str, metrics: dict) -> str:
        res = [title,
               f"  buffer_id: {metrics['buffer_id']}",
               f"  capacity_vertices: {metrics['capacity_vertices']}",
               f"  used_vertices: {metrics['used_vertices']}",
               f"  free_vertices: {metrics['free_vertices']}",
               f"  allocation_count: {metrics['allocation_count']}",
               f"  free_range_count: {metrics['free_range_count']}",
               f"  largest_free_range: {metrics['largest_free_range']}",
               f"  fragmentation: {metrics['fragmentation']:.4f}",
               f"  free_ranges: {metrics['free_ranges']}"]

        return '\n'.join(res)

    @classmethod
    def _debug_print_new_buffer_allocation(cls, requested_vertices: int):
        if not cls._is_vbo_debug_enabled():
            return

        lines = ['[VBO] allocating new model arena',
                 f'  requested_vertices: {requested_vertices}',
                 f'  existing_buffers: {len(cls._model_arenas)}']

        for index, arena in enumerate(cls._model_arenas):
            metrics = arena.debug_metrics()
            lines.append(
                cls._format_arena_metrics(f'  arena[{index}]', metrics))

        cls._log_debug('\n'.join(lines))

    @classmethod
    def _debug_print_compaction(cls, before: dict, after: dict):
        if not cls._is_vbo_debug_enabled():
            return

        lines = ['[VBO] compacted arena',
                 f"  buffer_before: {before['buffer_id']}",
                 f"  buffer_after: {after['buffer_id']}",
                 cls._format_arena_metrics('  before', before),
                 cls._format_arena_metrics('  after', after)]

        cls._log_debug('\n'.join(lines))

    @classmethod
    def _allocate_model_arena(cls, key: str, vertex_count: int) -> _MeshArena:
        needed = int(vertex_count)
        if needed <= 0:
            raise ValueError('vertex_count must be > 0')

        for arena in cls._model_arenas:
            if arena.get_allocation(key) is not None:
                return arena

        for arena in cls._model_arenas:
            if arena.can_fit(needed):
                arena.allocate(key, needed)
                return arena

        for arena in cls._model_arenas:
            if arena.should_compact(needed_vertices=needed):
                before = arena.debug_metrics()

                if arena.compact() and arena.can_fit(needed):
                    after = arena.debug_metrics()
                    cls._debug_print_compaction(before, after)

                    arena.allocate(key, needed)
                    cls._clear_model_vaos_for_arena(arena)

                    return arena

        cls._debug_print_new_buffer_allocation(needed)

        capacity = max(MODEL_ARENA_CAPACITY_VERTICES, needed)
        arena = _MeshArena(capacity)
        cls._model_arenas.append(arena)

        if cls._is_vbo_debug_enabled():
            msg = ['[VBO] created model arena',
                   f'  buffer_id: {arena.buffer}',
                   f'  capacity_vertices: {capacity}',
                   f'  total_buffers: {len(cls._model_arenas)}',
                   f'  allocation_key: {key}',
                   f'  requested_vertices: {needed}']

            cls._log_debug('\n'.join(msg))

        arena.allocate(key, needed)
        return arena

    @classmethod
    def _clear_model_vaos_for_arena(cls, arena: _MeshArena):
        refs = list(VBOSingleton._instances.values())  # NOQA
        for ref in refs:
            instance = ref()
            if instance is None or instance._arena_kind != VBO_TYPE_MODEL:  # NOQA
                continue

            if instance._model_arena is arena:  # NOQA
                instance._clear_vaos()  # NOQA

    def _attribute_offsets(self) -> tuple[int, int, int, int]:
        """Return (buffer id, position/smooth/face byte offsets)."""
        count = self._vert_count

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._model_arena
            if arena is None:
                raise RuntimeError('model arena allocation is missing')

            alloc = arena.get_allocation(self.id)
            if alloc is None:
                raise RuntimeError('model arena allocation is missing')

            buffer_id = arena.buffer
            base = alloc.start * VERTEX_STRIDE_BYTES
        else:
            buffer_id = self._vbo
            base = 0

        block_size = count * 3 * _FLOAT_SIZE

        return buffer_id, base, base + block_size, base + 2 * block_size

    def update(self, data: np.ndarray, count: int):
        new_vert_count = self._normalize_vertex_count(count, len(data))

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._model_arena

            if arena is None:
                raise RuntimeError('model arena allocation is missing')

            alloc = arena.get_allocation(self.id)
            if alloc is None:
                raise RuntimeError('model arena allocation is missing')

            if new_vert_count != alloc.count:
                # Vertex count changed — free old slot and re-allocate.
                arena.free(self.id)
                arena = self._allocate_model_arena(self.id, new_vert_count)
                self._model_arena = arena
                self._clear_vaos()

            self._data = data
            self._vert_count = new_vert_count
            arena.upload(self.id, data)
            self.local_aabb = self._compute_local_aabb()
            self.local_obb = self._compute_local_obb()
            return

        self._data = data
        self._vert_count = new_vert_count
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, data.nbytes, data)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        self.local_aabb = self._compute_local_aabb()
        self.local_obb = self._compute_local_obb()

    @classmethod
    def maintain_model_arena(
        cls,
        threshold: float = MODEL_ARENA_FRAGMENTATION_THRESHOLD,
        min_free_vertices: int = MODEL_ARENA_MIN_FREE_VERTICES
    ) -> bool:

        compacted = False
        for arena in cls._model_arenas:

            if not arena.should_compact(threshold=threshold,
                                        min_free_vertices=min_free_vertices):

                continue

            before = arena.debug_metrics()
            if not arena.compact():
                continue

            after = arena.debug_metrics()
            cls._debug_print_compaction(before, after)
            cls._clear_model_vaos_for_arena(arena)
            compacted = True

        return compacted

    @classmethod
    def release_model_allocation(cls, key: str):
        for arena in cls._model_arenas:
            if arena.get_allocation(key) is None:
                continue

            arena.free(key)
            break

    @classmethod
    def evict(cls, key: str):
        """Remove a key from the singleton cache and free its arena slot.

        Call this before re-creating a VBO with the same key but different data.
        Safe to call even if the key is not present.
        """
        cls.release_model_allocation(key)
        ref = VBOSingleton._instances.pop(key, None)  # NOQA
        if ref is not None:
            instance = ref()
            if instance is not None:
                instance._clear_vaos()  # NOQA
                instance._model_arena = None  # NOQA

    def release(self):
        super().release()

        if self._vaos:
            return

        if self._arena_kind != VBO_TYPE_MODEL:
            self._release_vbo(self._vbo)
            self._vbo = None

    @classmethod
    def _create_vbo(cls, data):
        vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STATIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbo(vbo)

            raise RuntimeError(f"OpenGL error creating mesh buffer: {err}")

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        return vbo


def create_model_vbo(model):
    """Create or return a shared arena-backed model VBO for a model record.

    Returns ``None`` when the model has no UUID or no cached mesh payload.
    """
    if model is None:
        return None

    uuid = model.uuid
    if not uuid:
        return None

    data_path = model.data_path
    if data_path is None:
        return None

    packed = np.load(data_path, mmap_mode='r')

    if uuid in PooledVBOHandler:
        vbo = PooledVBOHandler(uuid)
        if len(packed) != len(vbo.data):
            vbo.update(packed, len(packed))
        return vbo

    return PooledVBOHandler(uuid, packed, len(packed),
                            aabb=getattr(model, 'aabb', None),
                            obb=getattr(model, 'obb', None),
                            arena_kind=VBO_TYPE_MODEL)
