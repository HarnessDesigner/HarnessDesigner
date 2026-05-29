# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
MODEL_ARENA_CAPACITY_VERTICES = 4_000_000
# Compaction threshold: rebuild arena when free-space fragmentation reaches this ratio.
MODEL_ARENA_FRAGMENTATION_THRESHOLD = 0.35
# Avoid rebuilding for tiny holes until at least this many vertices are reclaimable.
MODEL_ARENA_MIN_FREE_VERTICES = 4096


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

        self._pos_buffer = None
        self._smooth_buffer = None
        self._face_buffer = None
        self._create_buffers()

    @property
    def pos_buffer(self) -> int:
        return self._pos_buffer

    @property
    def smooth_buffer(self) -> int:
        return self._smooth_buffer

    @property
    def face_buffer(self) -> int:
        return self._face_buffer

    def _create_empty_array_buffer(self) -> int:
        buffer_id = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER,
            self.capacity_vertices * 3 * np.dtype(np.float32).itemsize,
            None,
            GL.GL_DYNAMIC_DRAW,
        )
        return buffer_id

    def _create_buffers(self):
        self._pos_buffer = self._create_empty_array_buffer()
        self._smooth_buffer = self._create_empty_array_buffer()
        self._face_buffer = self._create_empty_array_buffer()
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
        raise RuntimeError(
            'model mesh arena has no contiguous free range large enough: '
            f'requested {needed} vertices, '
            f'largest hole {self.largest_free_range}, '
            f'total free {free_total}, '
            f'capacity {self.capacity_vertices}'
        )

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

    def _upload_to_buffer(self, buffer_id: int, start_vertex: int, data: np.ndarray):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)
        GL.glBufferSubData(
            GL.GL_ARRAY_BUFFER,
            start_vertex * 3 * np.dtype(np.float32).itemsize,
            data.nbytes,
            data,
        )

    def upload(
        self,
        key: str,
        vertices: np.ndarray,
        smooth_normals: np.ndarray,
        face_normals: np.ndarray,
        vertex_offset: int = 0,
    ):
        alloc = self._allocations[key]
        offset = int(vertex_offset)

        if offset < 0:
            raise ValueError('vertex_offset cannot be negative')

        chunk_count = len(vertices) // 3
        if chunk_count == 0:
            return

        if len(vertices) % 3 != 0:
            raise ValueError('vertex array length must be divisible by 3')

        if len(smooth_normals) != len(vertices):
            raise ValueError('smooth_normals length must match vertices length')

        if len(face_normals) != len(vertices):
            raise ValueError('face_normals length must match vertices length')

        if offset + chunk_count > alloc.count:
            raise ValueError('partial upload exceeds allocation size')

        start = alloc.start + offset

        self._upload_to_buffer(self._pos_buffer, start, vertices)
        self._upload_to_buffer(self._smooth_buffer, start, smooth_normals)
        self._upload_to_buffer(self._face_buffer, start, face_normals)
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
        return {
            'buffer_id': self._pos_buffer,
            'capacity_vertices': self.capacity_vertices,
            'used_vertices': self.used_vertices,
            'free_vertices': self.free_vertices,
            'allocation_count': len(self._allocations),
            'free_range_count': len(free_ranges),
            'largest_free_range': self.largest_free_range,
            'fragmentation': self.fragmentation,
            'free_ranges': free_ranges,
        }

    def should_compact(
        self,
        threshold: float = MODEL_ARENA_FRAGMENTATION_THRESHOLD,
        min_free_vertices: int = MODEL_ARENA_MIN_FREE_VERTICES,
        needed_vertices: int = 0,
    ) -> bool:
        needed = int(needed_vertices)
        if needed > 0 and self.largest_free_range >= needed:
            return False

        return (
            self.free_vertices >= int(min_free_vertices)
            and self.fragmentation >= float(threshold)
        )

    def _gpu_copy(
        self,
        src_buffer: int,
        dst_buffer: int,
        src_vertex: int,
        dst_vertex: int,
        vertex_count: int,
    ):
        size = vertex_count * 3 * np.dtype(np.float32).itemsize
        read_offset = src_vertex * 3 * np.dtype(np.float32).itemsize
        write_offset = dst_vertex * 3 * np.dtype(np.float32).itemsize

        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, src_buffer)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, dst_buffer)
        GL.glCopyBufferSubData(
            GL.GL_COPY_READ_BUFFER,
            GL.GL_COPY_WRITE_BUFFER,
            read_offset,
            write_offset,
            size,
        )

    def compact(self) -> bool:
        if not self._allocations:
            self._free_ranges = [(0, self.capacity_vertices)]
            return False

        new_pos = self._create_empty_array_buffer()
        new_smooth = self._create_empty_array_buffer()
        new_face = self._create_empty_array_buffer()

        sorted_items = sorted(self._allocations.items(), key=lambda item: item[1].start)
        cursor = 0
        for key, alloc in sorted_items:
            self._gpu_copy(self._pos_buffer, new_pos, alloc.start, cursor, alloc.count)
            self._gpu_copy(self._smooth_buffer, new_smooth, alloc.start, cursor, alloc.count)
            self._gpu_copy(self._face_buffer, new_face, alloc.start, cursor, alloc.count)

            self._allocations[key] = _ArenaAllocation(start=cursor, count=alloc.count)
            cursor += alloc.count

        GL.glDeleteBuffers(1, [self._pos_buffer])
        GL.glDeleteBuffers(1, [self._smooth_buffer])
        GL.glDeleteBuffers(1, [self._face_buffer])

        self._pos_buffer = new_pos
        self._smooth_buffer = new_smooth
        self._face_buffer = new_face

        self._free_ranges = []
        if cursor < self.capacity_vertices:
            self._free_ranges.append((cursor, self.capacity_vertices - cursor))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_READ_BUFFER, 0)
        GL.glBindBuffer(GL.GL_COPY_WRITE_BUFFER, 0)
        return True


class VBOSingleton(type):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        VBOHandler.release_model_allocation(key)

        del cls._instances[key]

    def __contains__(cls, item):
        return item in cls._instances

    def __call__(cls, id_: str, *args, **kwargs) -> "VBOHandler":
        if id_ not in cls._instances:
            instance = super().__call__(id_, *args, **kwargs)
            cls._instances[id_] = weakref.ref(instance, cls._remove_ref)
        elif cls._instances[id_]() is None:
            del cls._instances[id_]
            instance = super().__call__(id_, *args, **kwargs)
            cls._instances[id_] = weakref.ref(instance, cls._remove_ref)
        else:
            instance = cls._instances[id_]()

        return instance


VBO_TYPE_PRIMITIVE = 0
VBO_TYPE_MODEL = 1


class VBOHandler(metaclass=VBOSingleton):
    _model_arenas: list[_MeshArena] = []

    def __init__(
        self,
        id_: str,
        vertices: np.ndarray | None = None,
        smooth_normals: np.ndarray | None = None,
        face_normals: np.ndarray | None = None,
        count: int = 0,
        endpoint: _point.Point | None = None,
        arena_kind: int = VBO_TYPE_MODEL
    ):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        self.id = id_
        self.endpoint = endpoint
        self._arena_kind = arena_kind

        self.__vert_count = 0
        self.__first = 0
        self.__model_arena: _MeshArena | None = None

        self.__vbo_vertices = None
        self.__vbo_smooth_normals = None
        self.__vbo_face_normals = None
        self.__vaos: dict[int, int] = {}

        self.__vertices = vertices
        self.__smooth_normals = smooth_normals
        self.__face_normals = face_normals

        if self.__smooth_normals is None and self.__face_normals is None:
            raise ValueError('at least one normal array is required')

        if self.__smooth_normals is None:
            self.__smooth_normals = self.__face_normals.copy()

        if self.__face_normals is None:
            self.__face_normals = self.__smooth_normals.copy()

        self.__vert_count = self._normalize_vertex_count(count, len(self.__vertices))

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._allocate_model_arena(self.id, self.__vert_count)
            arena.upload(self.id, self.__vertices, self.__smooth_normals, self.__face_normals)
            alloc = arena.get_allocation(self.id)
            self.__model_arena = arena
            self.__first = alloc.start
        else:
            (
                self.__vbo_vertices,
                self.__vbo_smooth_normals,
                self.__vbo_face_normals,
            ) = self._create_vbo(self.__vertices, self.__smooth_normals, self.__face_normals)

        local_aabb = _utils.compute_aabb(self.__vertices.reshape(-1, 3))
        self.local_obb = _utils.compute_obb(*local_aabb)
        p1, p2 = local_aabb
        self.local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float32)

    @staticmethod
    def _normalize_vertex_count(count: int, array_len: int) -> int:
        if count > 0:
            return int(count)

        if array_len % 3 != 0:
            raise ValueError('flattened vertex array length must be divisible by 3')

        return int(array_len // 3)

    @classmethod
    def _log_debug(cls, *args):
        logger = getattr(_logger, 'logger', None)
        if logger is not None:
            logger.debug(*args)
            return

        print(*args)

    @staticmethod
    def _is_vbo_debug_enabled() -> bool:
        try:
            return bool(Config.logging.log_debug)
        except Exception:
            return False

    @classmethod
    def _debug_print_new_buffer_allocation(cls, requested_vertices: int):
        if not cls._is_vbo_debug_enabled():
            return

        cls._log_debug(
            '[VBO] allocating new model arena:',
            f'requested_vertices={requested_vertices}',
            f'existing_buffers={len(cls._model_arenas)}'
        )
        for index, arena in enumerate(cls._model_arenas):
            metrics = arena.debug_metrics()
            cls._log_debug(
                '[VBO] arena',
                f'index={index}',
                f'buffer_id={metrics["buffer_id"]}',
                f'capacity_vertices={metrics["capacity_vertices"]}',
                f'used_vertices={metrics["used_vertices"]}',
                f'free_vertices={metrics["free_vertices"]}',
                f'allocation_count={metrics["allocation_count"]}',
                f'free_range_count={metrics["free_range_count"]}',
                f'largest_free_range={metrics["largest_free_range"]}',
                f'fragmentation={metrics["fragmentation"]:.4f}',
                f'free_ranges={metrics["free_ranges"]}'
            )

    @classmethod
    def _debug_print_compaction(cls, before: dict, after: dict):
        if not cls._is_vbo_debug_enabled():
            return

        cls._log_debug(
            '[VBO] compacted arena:',
            f'buffer_before={before["buffer_id"]}',
            f'buffer_after={after["buffer_id"]}'
        )
        cls._log_debug(
            '[VBO] arena before:',
            f'capacity_vertices={before["capacity_vertices"]}',
            f'used_vertices={before["used_vertices"]}',
            f'free_vertices={before["free_vertices"]}',
            f'allocation_count={before["allocation_count"]}',
            f'free_range_count={before["free_range_count"]}',
            f'largest_free_range={before["largest_free_range"]}',
            f'fragmentation={before["fragmentation"]:.4f}',
            f'free_ranges={before["free_ranges"]}'
        )
        cls._log_debug(
            '[VBO] arena after:',
            f'capacity_vertices={after["capacity_vertices"]}',
            f'used_vertices={after["used_vertices"]}',
            f'free_vertices={after["free_vertices"]}',
            f'allocation_count={after["allocation_count"]}',
            f'free_range_count={after["free_range_count"]}',
            f'largest_free_range={after["largest_free_range"]}',
            f'fragmentation={after["fragmentation"]:.4f}',
            f'free_ranges={after["free_ranges"]}'
        )

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
        cls._log_debug(
            '[VBO] created model arena:',
            f'buffer_id={arena.pos_buffer}',
            f'capacity_vertices={capacity}',
            f'total_buffers={len(cls._model_arenas)}'
        )
        arena.allocate(key, needed)
        return arena

    @classmethod
    def _clear_model_vaos_for_arena(cls, arena: _MeshArena):
        refs = list(VBOSingleton._instances.values())
        for ref in refs:
            instance = ref()
            if instance is None or instance._arena_kind != VBO_TYPE_MODEL:
                continue

            if instance.__model_arena is arena:
                instance._clear_vaos()

    @property
    def vertices(self):
        return self.__vertices

    @property
    def faces(self):
        return None

    def acquire(self):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)
        if ctx_id in self.__vaos:
            return

        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self.__model_arena
            if arena is None:
                raise RuntimeError('model arena allocation is missing')
            vbo_vertices = arena.pos_buffer
            vbo_smooth = arena.smooth_buffer
            vbo_face = arena.face_buffer
        else:
            vbo_vertices = self.__vbo_vertices
            vbo_smooth = self.__vbo_smooth_normals
            vbo_face = self.__vbo_face_normals

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_vertices)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_smooth)
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_face)
        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

        self.__vaos[ctx_id] = vao

    def _clear_vaos(self):
        for vao in self.__vaos.values():
            self._release_vao(vao)
        self.__vaos.clear()

    def release(self):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)
        vao = self.__vaos.pop(ctx_id, None)
        if vao is not None:
            self._release_vao(vao)

        if self.__vaos:
            return

        if self._arena_kind != VBO_TYPE_MODEL:
            self._release_vbos(self.__vbo_vertices, self.__vbo_smooth_normals, self.__vbo_face_normals)
            self.__vbo_vertices = None
            self.__vbo_smooth_normals = None
            self.__vbo_face_normals = None

    @staticmethod
    def _release_vao(vao):
        if vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [vao])
            except Exception:  # NOQA
                pass

    @staticmethod
    def _release_vbos(vbo_vertices=None, vbo_smooth_normals=None, vbo_face_normals=None):
        if vbo_vertices is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_vertices])
            except Exception:  # NOQA
                pass

        if vbo_smooth_normals is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_smooth_normals])
            except Exception:  # NOQA
                pass

        if vbo_face_normals is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_face_normals])
            except Exception:  # NOQA
                pass

    @classmethod
    def _create_vbo(cls, vertices, smooth_normals, face_normals):
        vbo_vertices = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_vertices)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices)
            raise RuntimeError(f"OpenGL error creating vertex buffer: {err}")

        vbo_smooth_normals = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_smooth_normals)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, smooth_normals.nbytes, smooth_normals, GL.GL_STATIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices, vbo_smooth_normals)
            raise RuntimeError(f"OpenGL error creating smooth normals buffer: {err}")

        vbo_face_normals = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_face_normals)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, face_normals.nbytes, face_normals, GL.GL_STATIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices, vbo_smooth_normals, vbo_face_normals)
            raise RuntimeError(f"OpenGL error creating face normals buffer: {err}")

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        return vbo_vertices, vbo_smooth_normals, vbo_face_normals

    def update_data(
        self,
        vertices: np.ndarray | None = None,
        smooth_normals: np.ndarray | None = None,
        face_normals: np.ndarray | None = None,
        vertex_offset: int = 0,
    ):
        if self.__vert_count == 0:
            return

        vertices = vertices if vertices is not None else self.__vertices
        smooth_normals = (
            smooth_normals if smooth_normals is not None else self.__smooth_normals)
        face_normals = (
            face_normals if face_normals is not None else self.__face_normals)

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self.__model_arena
            if arena is None:
                raise RuntimeError('model arena allocation is missing')
            arena.upload(self.id, vertices, smooth_normals, face_normals, vertex_offset=vertex_offset)
            return

        offset_bytes = int(vertex_offset) * 3 * np.dtype(np.float32).itemsize
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.__vbo_vertices)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, offset_bytes, vertices.nbytes, vertices)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.__vbo_smooth_normals)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, offset_bytes, smooth_normals.nbytes, smooth_normals)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.__vbo_face_normals)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, offset_bytes, face_normals.nbytes, face_normals)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @classmethod
    def maintain_model_arena(
        cls,
        threshold: float = MODEL_ARENA_FRAGMENTATION_THRESHOLD,
        min_free_vertices: int = MODEL_ARENA_MIN_FREE_VERTICES,
    ) -> bool:
        compacted = False
        for arena in cls._model_arenas:
            if not arena.should_compact(threshold=threshold, min_free_vertices=min_free_vertices):
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

    def render(self):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)
        if ctx_id not in self.__vaos:
            self.acquire()

        first = self.__first
        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self.__model_arena
            if arena is None:
                return

            alloc = arena.get_allocation(self.id)
            if alloc is None:
                return

            first = alloc.start
            self.__first = first

        vao = self.__vaos[ctx_id]
        GL.glBindVertexArray(vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, first, self.__vert_count)
        GL.glBindVertexArray(0)


def create_model_vbo(model):
    """Create or return a shared arena-backed model VBO for a model record.

    Returns ``None`` when the model has no UUID or no cached mesh payload.
    """
    if model is None:
        return None

    uuid = model.uuid
    if not uuid:
        return None

    if uuid in VBOHandler:
        return VBOHandler(uuid)

    model_data = model.data_path
    if model_data is None:
        return None

    return VBOHandler(
        uuid,
        model_data.vertices,
        model_data.smooth_normals,
        count=model_data.vertex_count,
        face_normals=model_data.face_normals,
        arena_kind=VBO_TYPE_MODEL,
    )
