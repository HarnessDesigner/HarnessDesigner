# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np
import weakref
from OpenGL import GL
from PySide6.QtGui import QOpenGLContext

from ..geometry import point as _point
from .. import utils as _utils


class VBOSingleton(type):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __contains__(cls, item):
        return item in cls._instances

    def __call__(cls, id_: str, vertices: np.ndarray | None = None,  # NOQA
                 normals: np.ndarray | None = None,
                 faces: np.ndarray | None = None,
                 count: int = 0,
                 endpoint: _point.Point | None = None) -> "VBOHandler":

        if id_ not in cls._instances:
            instance = super().__call__(id_, vertices, normals, faces,
                                        count, endpoint)

            cls._instances[id_] = weakref.ref(instance, cls._remove_ref)

        elif cls._instances[id_]() is None:
            # Handle edge case where a reference has been removed
            # but the reference object has not yet been removed from
            # the dict. We have to make sure that we delete the key
            # before adding the object again because of the internal
            # mechanics in weakref and not wanting it to remove
            # the newly added reference
            del cls._instances[id_]
            instance = super().__call__(id_, vertices, normals, faces,
                                        count, endpoint)

            cls._instances[id_] = weakref.ref(instance, cls._remove_ref)
        else:
            instance = cls._instances[id_]()

        return instance


class VBOHandler(metaclass=VBOSingleton):

    # TODO: Might have to write the memory allocation differently where vbo's
    #       are allocated as chunks that contain data for more than 1 object at
    #       a time. The reason for this is because of fragmentation of the
    #       memory if a user is adding and then removing alot of different
    #       objects. By using larger preallocated blocks I can write the code
    #       that will handle where the different things are being stored inside
    #       of the blocks and what block is being used. I am able to copy chunks
    #       of one VBO to another using the GPU. I am going to run with this for
    #       now and see how it does and if I need to impliment a more agressive
    #       approach with managing VBOs to control frag I will do that at a later
    #       time.

    def __init__(self, id_: str, vertices: np.ndarray | None = None,  # NOQA
                 normals: np.ndarray | None = None,
                 faces: np.ndarray | None = None,
                 count: int = 0,
                 endpoint: _point.Point | None = None):

        print('vbo init:', id_)
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        self.id = id_
        self.endpoint = endpoint

        self.__vertices = vertices
        self.__normals = normals
        self.__faces = faces
        self.__count = count

        # Store VBO IDs (these are shared across contexts)
        self.__vbo_vertices = None
        self.__vbo_normals = None
        self.__vbo_faces = None
        self.__vert_count = 0
        
        # Store VAOs per context (VAOs are NOT shared across contexts)
        # Key is id(QOpenGLContext), value is VAO ID
        self.__vaos = {}

        # Create the shared VBOs
        (
            self.__vbo_vertices,
            self.__vbo_normals,
            self.__vbo_faces,
            self.__vert_count
        ) = self._create_vbo(vertices, normals, faces, count)

        local_aabb = _utils.compute_aabb(vertices.reshape(-1, 3))
        self.local_obb = _utils.compute_obb(*local_aabb)

        p1, p2 = local_aabb
        self.local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float64)

    @property
    def vertices(self):
        return self.__vertices

    @property
    def faces(self):
        return self.__faces

    def acquire(self):
        """
        creates a new vao for the context that is being used.
        """

        print('vbo acquire:', self.id)

        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)

        # Check if we already have a VAO for this context
        if ctx_id in self.__vaos:
            return

        # Create VAO
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)
        # Check for OpenGL errors
        err = GL.glGetError()

        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vao)
            raise RuntimeError(f"OpenGL error creating vao: {err}")

        # Create a new VAO for this context
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        # Check for errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            raise RuntimeError(f"OpenGL error creating VAO: {err}")

        # Bind the shared VBOs and set up vertex attribute pointers
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.__vbo_vertices)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.__vbo_normals)
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.__vbo_faces)

        GL.glBindVertexArray(0)

        # Store the VAO for this context
        self.__vaos[ctx_id] = vao

    def release(self):
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)

        # Check if the vao has already been removed for a context
        if ctx_id not in self.__vaos:
            return

        vao = self.__vaos[ctx_id]
        self._release_vao(vao)
        del self.__vaos[ctx_id]

        if not self.__vaos.keys():
            self._release_vbos(
                self.__vbo_vertices, self.__vbo_normals, self.__vbo_faces)

            self.__vbo_vertices = None
            self.__vbo_normals = None
            self.__vbo_faces = None
            self.__vert_count = 0

    @staticmethod
    def _release_vao(vao):
        """Release a single VAO."""
        if vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [vao])
            except:  # NOQA
                pass

    @staticmethod
    def _release_vbos(vbo_vertices=None, vbo_normals=None, vbo_faces=None):
        """Release VBO buffers (shared across contexts)."""
        if vbo_vertices is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_vertices])
            except:  # NOQA
                pass

        if vbo_normals is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_normals])
            except:  # NOQA
                pass

        if vbo_faces is not None:
            try:
                GL.glDeleteBuffers(1, [vbo_faces])
            except:  # NOQA
                pass

    @classmethod
    def _create_vbo(cls, vertices, normals, faces, count):
        # Vertex buffer
        vbo_vertices = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_vertices)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes,
                        vertices, GL.GL_STATIC_DRAW)

        # Check for OpenGL errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices)
            raise RuntimeError(f"OpenGL error creating vertex buffer: {err}")

        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        # Normal buffer
        vbo_normals = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_normals)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, normals.nbytes,
                        normals, GL.GL_STATIC_DRAW)

        # Check for OpenGL errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices, vbo_normals)
            raise RuntimeError(f"OpenGL error creating normals buffer: {err}")

        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        # Element buffer
        vbo_faces = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, vbo_faces)

        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, faces.nbytes,
                        faces, GL.GL_STATIC_DRAW)

        # Check for OpenGL errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_vbos(vbo_vertices, vbo_normals, vbo_faces)
            raise RuntimeError(f"OpenGL error creating faces buffer: {err}")

        GL.glBindVertexArray(0)
        return vbo_vertices, vbo_normals, vbo_faces, int(count / 3)

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
        # Get or create VAO for the current context
        print('vbo render:', self.id)

        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        ctx_id = id(ctx)
        if ctx_id not in self.__vaos:
            self.acquire()

        vao = self.__vaos[ctx_id]

        GL.glBindVertexArray(vao)

        GL.glDrawElements(GL.GL_TRIANGLES, self.__vert_count,
                          GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)
