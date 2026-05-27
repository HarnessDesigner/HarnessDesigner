# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import weakref
from dataclasses import dataclass

import numpy as np
from OpenGL import GL
from PySide6.QtGui import QOpenGLContext

from .. import utils as _utils
from ..geometry import point as _point


# Maximum triangle-soup vertices managed in the imported-model arena.
MODEL_ARENA_CAPACITY_VERTICES = 4_000_000
# Compaction threshold: rebuild arena when free-space fragmentation reaches this ratio.
MODEL_ARENA_FRAGMENTATION_THRESHOLD = 0.35
# Avoid rebuilding for tiny holes until at least this many vertices are reclaimable.
MODEL_ARENA_MIN_FREE_VERTICES = 4096


@dataclass
class _ArenaAllocation:
    start: int
    count: int


class _MeshArena:

    def __init__(self, capacity_vertices: int):
        self.capacity_vertices = int(capacity_vertices)
        self._allocations: dict[str, _ArenaAllocation] = {}
        self._free_ranges: list[tuple[int, int]] = []
        self._tail = 0

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

        if self._tail + needed > self.capacity_vertices:
            available = self.capacity_vertices - self._tail
            raise RuntimeError(
                'model mesh arena is full: '
                f'requested {needed} vertices, '
                f'available {available}, '
                f'capacity {self.capacity_vertices}'
            )

        alloc = _ArenaAllocation(start=self._tail, count=needed)
        self._allocations[key] = alloc
        self._tail += needed
        return alloc

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

    def _upload_to_buffer(self, buffer_id: int, start: int, data: np.ndarray):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer_id)
        GL.glBufferSubData(
            GL.GL_ARRAY_BUFFER,
            start * 3 * np.dtype(np.float32).itemsize,
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

        chunk_count = len(vertices)
        if chunk_count == 0:
            return

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

    def should_compact(
        self,
        threshold: float = MODEL_ARENA_FRAGMENTATION_THRESHOLD,
        min_free_vertices: int = MODEL_ARENA_MIN_FREE_VERTICES,
    ) -> bool:
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
            self._free_ranges = []
            self._tail = 0
            return False

        new_pos = self._create_empty_array_buffer()
        new_smooth = self._create_empty_array_buffer()
        new_face = self._create_empty_array_buffer()

        sorted_items = sorted(self._allocations.items(), key=lambda item: item[1].start)
        cursor = 0
        for key, alloc in sorted_items:
            if alloc.start != cursor:
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

        self._tail = cursor
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
    _model_arena: _MeshArena | None = None

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

        self.__vbo_vertices = None
        self.__vbo_smooth_normals = None
        self.__vbo_face_normals = None
        self.__vaos: dict[int, int] = {}

        vertex_count_hint = count

        self.__vertices = vertices
        self.__smooth_normals = smooth_normals
        self.__face_normals = face_normals

        if self.__smooth_normals is None and self.__face_normals is None:
            raise ValueError('at least one normal array is required')

        if self.__smooth_normals is None:
            self.__smooth_normals = self.__face_normals.copy()

        if self.__face_normals is None:
            self.__face_normals = self.__smooth_normals.copy()

        self.__vert_count = len(self.__vertices)

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._get_model_arena()
            alloc = arena.allocate(self.id, self.__vert_count)
            arena.upload(self.id, self.__vertices, self.__smooth_normals, self.__face_normals)
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
        self.local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float64)

    @staticmethod
    def _normalize_vertex_count(count: int, array_len: int) -> int:
        if count <= 0:
            return int(array_len)

        if count == array_len * 3:
            return int(array_len)

        if count > array_len:
            return int(array_len)

        return int(count)

    @classmethod
    def _get_model_arena(cls) -> _MeshArena:
        if cls._model_arena is None:
            cls._model_arena = _MeshArena(MODEL_ARENA_CAPACITY_VERTICES)
        return cls._model_arena

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

        if self._arena_kind == 'model':
            arena = self._get_model_arena()
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

        if self._arena_kind != 'model':
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

        vertices = self._normalize_array(vertices) if vertices is not None else self.__vertices
        smooth_normals = (
            self._normalize_array(smooth_normals)
            if smooth_normals is not None else self.__smooth_normals
        )
        face_normals = (
            self._normalize_array(face_normals)
            if face_normals is not None else self.__face_normals
        )

        if self._arena_kind == 'model':
            arena = self._get_model_arena()
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
        arena = cls._model_arena
        if arena is None:
            return False

        if not arena.should_compact(threshold=threshold, min_free_vertices=min_free_vertices):
            return False

        if not arena.compact():
            return False

        refs = list(VBOSingleton._instances.values())
        for ref in refs:
            instance = ref()
            if instance is None or instance._arena_kind != 'model':
                continue
            instance._clear_vaos()

        return True

    @classmethod
    def release_model_allocation(cls, key: str):
        if cls._model_arena is not None:
            cls._model_arena.free(key)

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
        if self._arena_kind == 'model':
            alloc = self._get_model_arena().get_allocation(self.id)
            if alloc is None:
                return
            first = alloc.start

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
        arena_kind='model',
    )