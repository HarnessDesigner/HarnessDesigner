# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import ctypes
import threading
import weakref
import numpy as np
from OpenGL import GL
from PySide6 import QtGui

from .. import config as _config
from .. import logger as _logger
from .. import utils as _utils
from ..geometry import point as _point
from ..geometry import angle as _angle
from .. import check_types as _check_types
from . import arena_pool as _arena_pool
from . import arena_buffer as _arena_buffer

if TYPE_CHECKING:
    from ..database.global_db import model3d as _model3d
    from ..ui import mainframe as _mainframe
    from .shaders import program as _shader_program


# Triangle-soup vertices in a long-term model arena (one holding models with two or more users). A long arena is locked
# when a model moving to the long tier does not fit in it, and a locked one is trimmed to the space it uses, so this is only
# how large an open one is.
MODEL_ARENA_CAPACITY_VERTICES = 4000000
# A short-term arena (models with fewer than two users) is half the size of a long-term one and is never trimmed.
MODEL_ARENA_SHORT_CAPACITY_VERTICES = MODEL_ARENA_CAPACITY_VERTICES // 2
# How many users make a model long-term.
MODEL_TIER_LONG_REFS = 2
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


class _MeshArena(_arena_buffer.BufferArena):
    """One GPU buffer that model meshes are sub-allocated from; a slot is a vertex.

    The bookkeeping is ``arena_pool.ArenaMap`` and the buffer mechanics (moving a model to another arena, packing down, trimming)
    are ``arena_buffer.BufferArena``; what is left here is how a mesh is written into it.
    """

    STRIDE_BYTES: int = VERTEX_STRIDE_BYTES

    @_check_types.do
    def upload(self, key: str, data: np.ndarray) -> None:
        alloc = self.allocations[key]

        if len(data) != alloc.count * FLOATS_PER_VERTEX:
            raise ValueError('packed array length does not match the allocation: '
                             f'expected {alloc.count * FLOATS_PER_VERTEX} floats, '
                             f'got {len(data)}')

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)

        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, alloc.start * VERTEX_STRIDE_BYTES,
                           data.nbytes, data)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)


VBO_TYPE_PRIMITIVE = 0
VBO_TYPE_MODEL = 1


# Storage-key suffixes for the moment a VBO is replaced before the cleanup
# callback of the one it replaces has run -- see VBOSingleton. They are only ever
# appended to the KEY an entry is stored under, never to the VBO's own id (which
# is also its arena allocation key).
_OLD = '_old'
_NEW = '_new'


class VBOSingleton(type):
    _instances = {}
    _primitives = {}

    # Storage keys currently carrying the _OLD / _NEW suffix, tracked here rather
    # than found by looking at how a key ends: a real id can end in "_old" or
    # "_new" (a word in a Text, say) and must never be mistaken for one of these.
    _retired = set()
    _replacements = set()

    # _instances/_primitives are shared across every class using this
    # metaclass (not reset per-subclass) and are touched both from here and
    # from external call sites (PooledVBOHandler._clear_model_vaos_for_arena/
    # evict, part_orientation.py) plus _remove_ref firing as a weakref
    # callback on whatever thread drops the last reference. See
    # _EntrySingleton (global_db/bases.py) for why unsynchronized concurrent
    # mutation of a dict like this corrupts its internal structure -- same
    # fix applied here for consistency/defense-in-depth. RLock so a call
    # already holding it (e.g. __call__ triggering _remove_ref indirectly)
    # can safely re-enter.
    _instances_lock = threading.RLock()

    # A model VBO is held by weak reference, and when the callback that removes
    # its entry (and frees its arena allocation) runs is not something to count
    # on: for an object that is part of a reference cycle it runs whenever the
    # garbage collector gets to it, which can be at any point in any code -- so
    # it can run AFTER a new VBO with the same id has been asked for. The entry
    # is then dead but its callback is still to come (and the collector clears
    # every dead reference before it calls any of their callbacks, so one of
    # those can itself ask for this id). Entries are matched to a callback by weak-reference
    # identity, so that callback could never remove the newer entry -- but both
    # VBOs use the id as their arena allocation key, so it could free the newer
    # one's allocation. So a stale entry found by __call__ is set aside and its
    # replacement stored beside it:
    #
    #   <id>       -> dead reference     becomes    <id>_old   (its allocation is
    #                                                freed right then; its callback
    #                                                will free nothing)
    #   (new VBO)                                   <id>_new
    #
    # and the old one's callback then drops its own key and moves <id>_new back
    # under <id>. If the replacement dies first, its callback frees the allocation
    # and drops <id>_new, and the old one's later callback only drops its own key.

    @classmethod
    @_check_types.do
    def _live(cls, key: str) -> _Union["VBOHandlerBase", None]:
        """The VBO stored under *key*, or ``None`` -- dereferenced ONCE and
        returned as a strong reference. Checking that a reference is alive and
        then dereferencing it again is not safe: the garbage collector can run
        in between (any allocation can start it) and clear it."""
        ref = cls._instances.get(key)

        if ref is None:
            return None

        return ref()

    @classmethod
    @_check_types.do
    def _remove_ref(cls, ref: weakref.ref) -> None:
        with cls._instances_lock:
            for key, value in cls._instances.items():
                if value == ref:
                    break
            else:
                return

            if key in cls._retired:
                # The OLD one of a pair: its allocation was freed when it was set
                # aside and now belongs to its replacement, so free nothing. Drop
                # this entry and put the replacement back under the plain key.
                cls._retired.discard(key)
                del cls._instances[key]

                new_key = key[:-len(_OLD)] + _NEW
                if new_key in cls._replacements:
                    cls._replacements.discard(new_key)
                    cls._instances[key[:-len(_OLD)]] = cls._instances.pop(new_key)

                return

            if key in cls._replacements:
                # The replacement died before the old one's callback ran: it owns
                # the allocation for the id, so free it. The old one's callback
                # will find nothing to move back.
                cls._replacements.discard(key)
                PooledVBOHandler.release_model_allocation(key[:-len(_NEW)])
                del cls._instances[key]
                return

            PooledVBOHandler.release_model_allocation(key)

            del cls._instances[key]

    @_check_types.do
    def get(cls, id_: str) -> _Union["VBOHandlerBase", None]:
        """The VBO with id *id_*, or ``None`` if there isn't a live one -- in one
        step, as a strong reference. ``id_ in cls`` followed by ``cls(id_)`` is
        two steps, and the garbage collector can clear the reference between
        them."""
        with cls._instances_lock:
            instance = cls._live(id_)

            if instance is None:
                instance = cls._live(id_ + _NEW)

            if instance is None:
                instance = cls._primitives.get(id_)

            return instance

    @_check_types.do
    def __contains__(cls, item: str) -> bool:
        """Whether a VBO with id *item* exists -- a live one: a model entry is a
        weak reference, and one whose VBO has been collected (its callback may
        not have run yet) doesn't count. Looks under ``item``, then under its
        replacement's key (see the note at the top of this class)."""
        with cls._instances_lock:
            if cls._live(item) is not None or cls._live(item + _NEW) is not None:
                return True

            return item in cls._primitives

    @_check_types.do
    def __call__(cls, id_: str, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None,
                 arena_kind: int = VBO_TYPE_MODEL) -> "PooledVBOHandler":

        with cls._instances_lock:
            if arena_kind == VBO_TYPE_PRIMITIVE:
                if id_ not in cls._primitives:
                    instance = super().__call__(
                        id_, data, count, aabb, obb,
                        endpoint=endpoint, arena_kind=arena_kind)

                    cls._primitives[id_] = instance
                else:
                    instance = cls._primitives[id_]

            elif (instance := cls._live(id_)) is not None:
                pass

            elif (instance := cls._live(id_ + _NEW)) is not None:
                pass

            elif id_ not in cls._instances:
                instance = super().__call__(
                        id_, data, count, aabb, obb,
                        endpoint=endpoint, arena_kind=arena_kind)

                cls._instances[id_] = weakref.ref(instance, cls._remove_ref)

            else:
                # A dead entry whose cleanup callback hasn't run yet: set it
                # aside, free its allocation now (the new VBO gets its own --
                # the sizes can differ), and store the new one beside it.
                old_key = id_ + _OLD
                new_key = id_ + _NEW

                # An older pair still waiting on its callback: that callback
                # will find nothing to match and do nothing.
                cls._instances.pop(old_key, None)
                cls._retired.discard(old_key)

                cls._instances[old_key] = cls._instances.pop(id_)
                cls._retired.add(old_key)

                PooledVBOHandler.release_model_allocation(id_)

                try:
                    instance = super().__call__(
                        id_, data, count, aabb, obb,
                        endpoint=endpoint, arena_kind=arena_kind)
                except BaseException:
                    # Nothing was created -- put things back as they were.
                    cls._instances[id_] = cls._instances.pop(old_key)
                    cls._retired.discard(old_key)
                    raise

                cls._instances[new_key] = weakref.ref(instance, cls._remove_ref)
                cls._replacements.add(new_key)

            return instance


class VBOHandlerBase:

    @_check_types.do
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

    @_check_types.do
    def _compute_local_aabb(self) -> np.ndarray:
        # Bounding volumes are calculated once when a model is converted
        # and stored in the database; only primitives (and legacy rows
        # without stored bounds) compute them from the mesh here.
        p1, p2 = _utils.compute_aabb(self.vertices.reshape(-1, 3))

        local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float32)
        return local_aabb

    @_check_types.do
    def _compute_local_obb(self) -> np.ndarray:
        local_aabb = self._compute_local_aabb().reshape(2, 3)
        p1 = _point.Point(*[float(str(item)) for item in local_aabb[0].tolist()])
        p2 = _point.Point(*[float(str(item)) for item in local_aabb[1].tolist()])

        local_obb = _utils.compute_obb(p1, p2)

        return local_obb

    @staticmethod
    @_check_types.do
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
    @_check_types.do
    def _log_debug(cls, *args) -> None:
        _logger.debug_block(*args)

    @staticmethod
    @_check_types.do
    def _is_vbo_debug_enabled() -> bool:
        try:
            return bool(Config.logging.log_debug)
        except Exception:  # NOQA
            return False

    @property
    @_check_types.do
    def is_dirty(self) -> bool:
        return False

    @_check_types.do
    def render_angle(self, angle: _angle.Angle) -> _angle.Angle:
        """Return the angle this handler's owner should actually render/
        derive its OBB and AABB with -- *angle* (the owner's own real
        ``_angle``) unchanged, for every ordinary mesh VBO.

        Consulted by ``objects.objectsvar.base_var.BaseVar``'s own
        ``_render_geometry``/``_compute_obb``/``_compute_aabb`` instead
        of reading ``self._angle`` directly, so a handler that needs to
        show a different orientation than the object's own real, stored
        angle (currently only ``shapes.text.Text``, while camera
        tracking is enabled -- see its own docstring) can override this
        one place and have rendering AND hit-testing/picking (which both
        ultimately come from the OBB/AABB) automatically agree, no
        matter what triggered the recompute (a camera move, a drag, a
        scale change -- anything that ends up calling
        ``_compute_obb``/``_compute_aabb`` already goes through here).
        """
        return angle

    @_check_types.do
    def _attribute_offsets(self) -> tuple[int, int, int, int]:
        raise NotImplementedError

    @classmethod
    @_check_types.do
    def _create_vbo(cls, data: np.ndarray) -> int:
        raise NotImplementedError

    @_check_types.do
    def _clear_vaos(self) -> None:
        # A VAO is not shared between contexts: its id means something only in the context that made it. Only the VAO of the
        # current context can be deleted here; deleting another context's id would delete an unrelated VAO of this one. The
        # other contexts' entries are dropped, so each of them builds a new VAO the next time it draws.
        ctx = QtGui.QOpenGLContext.currentContext()
        if ctx is not None:
            vao = self._vaos.get(id(ctx))
            if vao is not None:
                self._release_vao(vao)

        self._vaos.clear()

    @property
    @_check_types.do
    def ctx(self) -> QtGui.QOpenGLContext:
        ctx = QtGui.QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        return ctx

    @_check_types.do
    def release(self) -> None:
        ctx = self.ctx
        ctx_id = id(ctx)

        vao = self._vaos.pop(ctx_id, None)
        if vao is not None:
            self._release_vao(vao)

    @staticmethod
    @_check_types.do
    def _release_vao(vao: int | None) -> None:
        if vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [vao])
            except Exception:  # NOQA
                pass

    @staticmethod
    @_check_types.do
    def _release_vbo(vbo: int | None = None) -> None:
        if vbo is not None:
            try:
                GL.glDeleteBuffers(1, [vbo])
            except Exception:  # NOQA
                pass

    @_check_types.do
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
    @_check_types.do
    def data(self) -> np.ndarray:
        return self._data

    @property
    @_check_types.do
    def vertices(self) -> np.ndarray:
        return self._data[:self._vert_count * 3]

    @property
    @_check_types.do
    def smooth_normals(self) -> np.ndarray:
        return self._data[self._vert_count * 3:self._vert_count * 6]

    @property
    @_check_types.do
    def face_normals(self) -> np.ndarray:
        return self._data[self._vert_count * 6:]

    @property
    @_check_types.do
    def vertex_count(self) -> int:
        return self._vert_count

    @property
    @_check_types.do
    def faces(self) -> None:
        return None

    @_check_types.do
    def render(self, program: _Union["_shader_program.FacesProgram", "_shader_program.EdgesProgram", "_shader_program.VerticesProgram", "_shader_program.TextureProgram"],
               position: _point.Point, angle: _angle.Angle, scale: _point.Point,
               smooth: bool | None) -> None:
        """Set this mesh's own per-draw transform uniforms, then draw it.

        Moved here (out of objects/objectsvar/base_var.py's own
        _render_geometry, which used to set these same uniforms itself
        before calling a bare ``self._vbo.render()``) so every VBO
        handler owns its own uniform-setting -- a compound handler
        (shapes/text.py's Text, one draw call per word rather than
        one mesh) needs different per-glyph position/rotation/scale
        values than the single set a real mesh VBO uses as-is, and can
        only compute those itself, glyph by glyph, if ``render()`` is
        the one place that both knows the transform *and* issues the
        draw call -- see Text's own ``render()`` docstring.

        *smooth* of ``None`` means "leave normalMode alone entirely" --
        the equivalent of the old ``normal_loc=None`` callers (gizmos
        like move_arrows.py/wire_marker_arrow.py that never resolved a
        normalMode location to begin with), as opposed to a real
        ``True``/``False`` which always pushes the uniform.
        """
        ctx = self.ctx
        ctx_id = id(ctx)
        if ctx_id not in self._vaos:
            self.acquire()

        if smooth is not None and program.has_normal_mode:
            # gl/shaders/faces.py and edges.py both resolve normalMode as
            # "0 -> smooth normal, anything else -> face (flat) normal" --
            # int(not smooth) is therefore the correct mapping (smooth=True
            # -> normalMode=0 -> smooth shading), not int(smooth).
            program.normal_mode = int(not smooth)

        program.position = position.as_float
        program.rotation = [float(str(v)) for v in angle.as_quat_numpy.tolist()]
        program.scale = scale.as_float

        # Attribute offsets (including the arena allocation base) are baked
        # into the VAO, so drawing always starts at vertex 0.  Compaction
        # moves allocations but also clears the affected VAOs, which forces
        # a re-acquire with fresh offsets.
        vao = self._vaos[ctx_id]
        GL.glBindVertexArray(vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._vert_count)
        GL.glBindVertexArray(0)

    @_check_types.do
    def acquire(self) -> None:
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
    @_check_types.do
    def __init__(self, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None):

        super().__init__(data, count, aabb, obb, endpoint=endpoint)
        self._vbo = self._create_vbo(self._data)
        self._dirty_vaos = {}

    @_check_types.do
    def release(self) -> None:
        super().release()

        if self._vaos:
            return

        self._release_vbo(self._vbo)
        self._vbo = None

    @_check_types.do
    def _attribute_offsets(self) -> tuple[int, int, int, int]:
        """Return (buffer id, position/smooth/face byte offsets)."""
        count = self._vert_count
        buffer_id = self._vbo
        base = 0

        block_size = count * 3 * _FLOAT_SIZE

        return int(buffer_id), int(base), int(base + block_size), int(base + 2 * block_size)

    @_check_types.do
    def acquire(self) -> None:
        ctx = self.ctx
        ctx_id = id(ctx)

        if ctx_id not in self._vaos:
            self._dirty_vaos[ctx_id] = False

        super().acquire()

    @classmethod
    @_check_types.do
    def _create_vbo(cls, data: np.ndarray, vbo: int | None = None) -> int:
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

    @_check_types.do
    def update(self, data: np.ndarray, count: int) -> None:
        self._data = data
        self._vert_count = self._normalize_vertex_count(count, len(data))

        self._create_vbo(data, self._vbo)

        for ctx_id in list(self._dirty_vaos.keys())[:]:
            self._dirty_vaos[ctx_id] = True

        self.local_aabb = self._compute_local_aabb()
        self.local_obb = self._compute_local_obb()

    @_check_types.do
    def _rebuild(self) -> None:
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
    @_check_types.do
    def is_dirty(self) -> bool:
        ctx = self.ctx

        ctx_id = id(ctx)
        return self._dirty_vaos.get(ctx_id, True)

    @_check_types.do
    def render(self, program: _Union["_shader_program.FacesProgram", "_shader_program.EdgesProgram", "_shader_program.VerticesProgram"],
               position: _point.Point, angle: _angle.Angle, scale: _point.Point,
               smooth: bool | None) -> None:
        self._rebuild()

        super().render(program, position, angle, scale, smooth)


class PooledVBOHandler(VBOHandlerBase, _arena_buffer.ArenaPoolBase, metaclass=VBOSingleton):
    _model_arenas: list[_MeshArena] = []

    @_check_types.do
    def __init__(self, id_: str, data: np.ndarray | None = None,
                 count: int = 0,
                 aabb: np.ndarray | None = None,
                 obb: np.ndarray | None = None,
                 *, endpoint: _point.Point | None = None,
                 arena_kind: int = VBO_TYPE_MODEL):

        super().__init__(data, count, aabb, obb, endpoint=endpoint)

        self.id = id_
        self._arena_kind = arena_kind
        self._ref_count = 0

        self._model_arena: _MeshArena | None = None

        if self._arena_kind == VBO_TYPE_MODEL:
            arena = self._allocate_model_arena(self.id, self._vert_count)

            arena.upload(self.id, self._data)

            self._model_arena = arena
        else:
            self._vbo = self._create_vbo(self._data)

    @staticmethod
    @_check_types.do
    def _format_arena_metrics(title: str, metrics: dict) -> str:
        res = [title,
               f"  buffer_id: {metrics['buffer_id']}",
               f"  tier: {metrics['tier']} locked: {metrics['locked']}",
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
    @_check_types.do
    def _debug_print_new_buffer_allocation(cls, requested_vertices: int) -> None:
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
    @_check_types.do
    def _debug_print_compaction(cls, before: dict, after: dict) -> None:
        if not cls._is_vbo_debug_enabled():
            return

        lines = ['[VBO] compacted arena',
                 f"  buffer_before: {before['buffer_id']}",
                 f"  buffer_after: {after['buffer_id']}",
                 cls._format_arena_metrics('  before', before),
                 cls._format_arena_metrics('  after', after)]

        cls._log_debug('\n'.join(lines))

    @classmethod
    @_check_types.do
    def _allocate_model_arena(cls, key: str, vertex_count: int) -> _MeshArena:
        needed = int(vertex_count)
        if needed <= 0:
            raise ValueError('vertex_count must be > 0')

        for arena in cls._model_arenas:
            if arena.get_allocation(key) is not None:
                return arena

        for arena in cls._model_arenas:
            if arena.tier == _arena_pool.TIER_SHORT and arena.can_fit(needed):
                arena.allocate(key, needed)
                return arena

        for arena in cls._model_arenas:
            if arena.tier != _arena_pool.TIER_SHORT:
                continue

            if arena.should_compact(MODEL_ARENA_FRAGMENTATION_THRESHOLD, MODEL_ARENA_MIN_FREE_VERTICES, needed):
                before = arena.debug_metrics()

                if arena.compact() and arena.can_fit(needed):
                    after = arena.debug_metrics()
                    cls._debug_print_compaction(before, after)

                    arena.allocate(key, needed)
                    cls._clear_model_vaos_for_arena(arena)

                    return arena

        cls._debug_print_new_buffer_allocation(needed)

        capacity = max(MODEL_ARENA_SHORT_CAPACITY_VERTICES, needed)
        arena = _MeshArena(capacity, _arena_pool.TIER_SHORT)
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
    @_check_types.do
    def _clear_model_vaos_for_arena(cls, arena: _MeshArena) -> None:
        with VBOSingleton._instances_lock:  # NOQA
            refs = list(VBOSingleton._instances.values())  # NOQA
        for ref in refs:
            instance = ref()
            if instance is None or instance._arena_kind != VBO_TYPE_MODEL:  # NOQA
                continue

            if instance._model_arena is arena:  # NOQA
                instance._clear_vaos()  # NOQA

    @_check_types.do
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

        return int(buffer_id), int(base), int(base + block_size), int(base + 2 * block_size)

    @_check_types.do
    def update(self, data: np.ndarray, count: int) -> None:
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

                if self._ref_count >= MODEL_TIER_LONG_REFS:
                    PooledVBOHandler._dirty = True

                PooledVBOHandler._request_maintenance()

            self._data = data
            self._vert_count = new_vert_count
            arena.upload(self.id, data)
            self.local_aabb = self._compute_local_aabb()
            self.local_obb = self._compute_local_obb()
            return

        old_vert_count = self._vert_count
        self._data = data
        self._vert_count = new_vert_count

        if new_vert_count > old_vert_count:
            # This buffer was allocated GL_STATIC_DRAW at exactly the old
            # vertex count -- no headroom to grow into. glBufferSubData
            # writing past that allocated size is invalid, so a growth
            # requires a full reallocation (a fresh glBufferData call),
            # not a sub-range write. Existing VAOs bind directly to the
            # old buffer id, so they must be cleared and re-acquired
            # against the new one.
            self._release_vbo(self._vbo)
            self._vbo = self._create_vbo(data)
            self._clear_vaos()
        else:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, data.nbytes, data)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        self.local_aabb = self._compute_local_aabb()
        self.local_obb = self._compute_local_obb()

    @property
    @_check_types.do
    def ref_count(self) -> int:
        """How many objects use this model. ``vbo.ref_count += 1`` when an object takes it, ``-= 1`` when it lets go. A model with
        ``MODEL_TIER_LONG_REFS`` or more users lives in a long-term arena, fewer in a short-term one; crossing that boundary
        asks for a maintenance pass (which does the moving, later, at idle time). Main thread only: ``+=`` is a read and a
        write. Only a model (arena) handler counts; for any other handler this does nothing."""
        return self._ref_count

    @ref_count.setter
    @_check_types.do
    def ref_count(self, value: int) -> None:
        if self._arena_kind != VBO_TYPE_MODEL:
            return

        new_count = int(value)
        if new_count < 0:
            _logger.warning(f'[VBO] the user count of model {self.id} went below 0 ({new_count}), reset to 0')
            new_count = 0

        crossed = (self._ref_count >= MODEL_TIER_LONG_REFS) != (new_count >= MODEL_TIER_LONG_REFS)
        self._ref_count = new_count

        if crossed:
            PooledVBOHandler._dirty = True
            PooledVBOHandler._request_maintenance()

    # ---- arena_buffer.ArenaPoolBase hooks (the scheduling and the replay of a plan are its) ----

    @classmethod
    @_check_types.do
    def _pool_arenas(cls) -> list[_arena_buffer.BufferArena]:
        return cls._model_arenas

    @classmethod
    @_check_types.do
    def _compact_threshold(cls) -> float:
        return MODEL_ARENA_FRAGMENTATION_THRESHOLD

    @classmethod
    @_check_types.do
    def _compact_min_free(cls) -> int:
        return MODEL_ARENA_MIN_FREE_VERTICES

    @classmethod
    @_check_types.do
    def _long_capacity(cls) -> int:
        return MODEL_ARENA_CAPACITY_VERTICES

    @classmethod
    @_check_types.do
    def _short_capacity(cls) -> int:
        return MODEL_ARENA_SHORT_CAPACITY_VERTICES

    @classmethod
    @_check_types.do
    def _desired_tiers(cls) -> dict[str, int]:
        desired: dict[str, int] = {}

        for arena in cls._model_arenas:
            for key in arena.allocations:
                handler = cls.get(key)

                if handler is None:
                    # its last reference is already gone and the callback that frees the allocation has not run yet
                    desired[key] = arena.tier
                elif handler.ref_count >= MODEL_TIER_LONG_REFS:
                    desired[key] = _arena_pool.TIER_LONG
                else:
                    desired[key] = _arena_pool.TIER_SHORT

        return desired

    @classmethod
    @_check_types.do
    def _make_arena(cls, op: _arena_pool.ArenaOp) -> _arena_buffer.BufferArena:
        return _MeshArena(op.capacity, op.tier, op.uid)

    @classmethod
    @_check_types.do
    def _executed(cls, moved: list[tuple[str, _arena_buffer.BufferArena]], rebuilt: list[_arena_buffer.BufferArena]) -> None:
        # A VAO holds the buffer id and the offset of its model, so every model that moved, and every model in an arena that
        # was rebuilt, needs a new one (render() makes it the next time the model is drawn).
        for key, target in moved:
            handler = cls.get(key)

            if handler is not None:
                handler._model_arena = target  # NOQA
                handler._clear_vaos()  # NOQA

        for arena in rebuilt:
            cls._clear_model_vaos_for_arena(arena)

        # the other canvases share these buffers; make the copies visible to their contexts
        GL.glFlush()

    @classmethod
    @_check_types.do
    def _log_pass(cls, ops: list[_arena_pool.ArenaOp], before: list, after: list) -> None:
        if not cls._is_vbo_debug_enabled():
            return

        steps: dict[str, int] = {}
        for op in ops:
            steps[op.kind] = steps.get(op.kind, 0) + 1

        capacity_before = sum(metrics['capacity_vertices'] for metrics in before)
        capacity_after = sum(metrics['capacity_vertices'] for metrics in after)
        freed = (capacity_before - capacity_after) * VERTEX_STRIDE_BYTES / 1048576.0

        lines = ['[VBO] model arena maintenance',
                 '  steps: ' + ', '.join(f'{kind} x{count}' for kind, count in steps.items()),
                 f'  capacity: {capacity_before} -> {capacity_after} vertices ({freed:.1f} MiB freed)']

        for index, metrics in enumerate(after):
            lines.append(cls._format_arena_metrics(f'  arena[{index}]', metrics))

        cls._log_debug('\n'.join(lines))

    @classmethod
    @_check_types.do
    def release_model_allocation(cls, key: str) -> None:
        for arena in cls._model_arenas:
            if arena.get_allocation(key) is None:
                continue

            arena.free(key)
            cls._request_maintenance()
            break

    @classmethod
    @_check_types.do
    def evict(cls, key: str) -> None:
        """Remove a key from the singleton cache and free its arena slot.

        Call this before re-creating a VBO with the same key but different data.
        Safe to call even if the key is not present.
        """
        cls.release_model_allocation(key)

        # The plain key, and -- if it was mid-replacement -- both halves of the pair.
        for stored in (key, key + _NEW, key + _OLD):
            with VBOSingleton._instances_lock:  # NOQA
                ref = VBOSingleton._instances.pop(stored, None)  # NOQA
                VBOSingleton._retired.discard(stored)  # NOQA
                VBOSingleton._replacements.discard(stored)  # NOQA

            if ref is not None:
                instance = ref()
                if instance is not None:
                    instance._clear_vaos()  # NOQA
                    instance._model_arena = None  # NOQA

    @_check_types.do
    def release(self) -> None:
        super().release()

        if self._vaos:
            return

        if self._arena_kind != VBO_TYPE_MODEL:
            self._release_vbo(self._vbo)
            self._vbo = None

    @classmethod
    @_check_types.do
    def _create_vbo(cls, data: np.ndarray) -> int:
        vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STATIC_DRAW)

        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbo(vbo)

            raise RuntimeError(f"OpenGL error creating mesh buffer: {err}")

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        return vbo


@_check_types.do
def create_model_vbo(model: "_model3d.Model3D") -> _Union["PooledVBOHandler", None]:
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

    packed = _utils.load_hdm(data_path, mmap_mode='r')

    if uuid in PooledVBOHandler:
        vbo = PooledVBOHandler(uuid)
        if len(packed) != len(vbo.data):
            vbo.update(packed, len(packed))
        return vbo

    return PooledVBOHandler(uuid, packed, len(packed),
                            aabb=model.aabb,
                            obb=model.obb,
                            arena_kind=VBO_TYPE_MODEL)
