import numpy as np
import weakref
from OpenGL import GL

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl import materials as _materials
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

    def __call__(cls, id: str, vertices: np.ndarray | None = None,  # NOQA
                 normals: np.ndarray | None = None,
                 faces: np.ndarray | None = None,
                 count: int = 0,
                 endpoint: _point.Point | None = None) -> "VBOHandler":

        if id not in cls._instances:
            instance = super().__call__(id, vertices, normals, faces,
                                        count, endpoint)

            cls._instances[id] = weakref.ref(instance, cls._remove_ref)

        elif cls._instances[id]() is None:
            # Handle edge case where a reference has been removed
            # but the reference object has not yet been removed from
            # the dict. We have to make sure that we delete the key
            # before adding the object again because of the internal
            # mechanics in weakref and not wanting it to remove
            # the newly added reference
            del cls._instances[id]
            instance = super().__call__(id, vertices, normals, faces,
                                        count, endpoint)

            cls._instances[id] = weakref.ref(instance, cls._remove_ref)
        else:
            instance = cls._instances[id]()

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

    def __init__(self, id: str, vertices: np.ndarray | None = None,  # NOQA
                 normals: np.ndarray | None = None,
                 faces: np.ndarray | None = None,
                 count: int = 0,
                 endpoint: _point.Point | None = None):

        self.id = id
        self.endpoint = endpoint

        if vertices is not None:
            vertices_reshaped = vertices.reshape(-1, 3)
            centroid = vertices_reshaped.mean(axis=0)
            vertices_reshaped -= centroid
            vertices = vertices_reshaped.ravel()

        self.__vertices = vertices
        self.__normals = normals
        self.__faces = faces
        self.__count = count

        (
            self.__vao,
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

    def __del__(self):
        self._release_buffers(self.__vao, self.__vbo_vertices,
                              self.__vbo_normals, self.__vbo_faces)

        self.__vao = None
        self.__vbo_vertices = None
        self.__vbo_normals = None
        self.__vbo_faces = None
        self.__vert_count = 0

    @staticmethod
    def _release_buffers(vao=None, vbo_vertices=None, vbo_normals=None, vbo_faces=None):
        # Clean up any partially created buffers
        if vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [vao])
            except:  # NOQA
                pass

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
        # Create VAO
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)
        # Check for OpenGL errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_buffers(vao)
            raise RuntimeError(f"OpenGL error creating vao: {err}")

        # Vertex buffer
        vbo_vertices = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_vertices)

        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes,
                        vertices, GL.GL_STATIC_DRAW)

        # Check for OpenGL errors
        err = GL.glGetError()
        if err != GL.GL_NO_ERROR:
            cls._release_buffers(vao, vbo_vertices)
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
            cls._release_buffers(vao, vbo_vertices, vbo_normals)
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
            cls._release_buffers(vao, vbo_vertices, vbo_normals, vbo_faces)
            raise RuntimeError(f"OpenGL error creating faces buffer: {err}")

        GL.glBindVertexArray(0)
        return vao, vbo_vertices, vbo_normals, vbo_faces, int(count / 3)

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
        GL.glBindVertexArray(self.__vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self.__vert_count, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)
