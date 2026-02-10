import numpy as np
import weakref
from OpenGL import GL

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers import materials as _materials
from ... import utils as _utils


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

    def __call__(cls, guid: str, data: list[list[np.ndarray, np.ndarray, np.ndarray, int]]) -> "VBOHandler":

        if guid not in cls._instances:
            instance = super().__call__(guid, data)
            cls._instances[guid] = weakref.ref(instance, cls._remove_ref)

        elif cls._instances[guid]() is None:
            # Handle edge case where a reference has been removed
            # but the reference object has not yet been removed from
            # the dict. We have to make sure that we delete the key
            # before adding the object again because of the internal
            # mechanics in weakref and not wanting it to remove
            # the newly added reference
            del cls._instances[guid]
            instance = super().__call__(guid, data)
            cls._instances[guid] = weakref.ref(instance, cls._remove_ref)
        else:
            instance = cls._instances[guid]()

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

    def __init__(self, guid: str, data: list[list[np.ndarray, np.ndarray, np.ndarray, int]]):
        self.guid = guid
        self.data = data

        self.vaos = []
        self.vbo_vertices = []
        self.vbo_normals = []
        self.ebos = []
        self.counts = []

        self.data = data

        vertices = []

        for line in data:
            vertices.append(line[0])
            try:
                vao, vbo_vertices, vbo_normals, ebo, count = self._create_vbo(*line)

            except (RuntimeError, Exception) as e:
                # we need to clean up any vbo buffers that may have been
                # allocated prior to the error.
                for vao, vbo_vertices, vbo_normals, ebo in zip(
                        self.vaos, self.vbo_vertices, self.vbo_normals, self.ebos):
                    self._release_buffers(vao, vbo_vertices, vbo_normals, ebo)

                del self.vaos[:]
                del self.vbo_vertices[:]
                del self.vbo_normals[:]
                del self.ebos[:]
                del self.counts[:]

                # reraise the error so it can be caught and CPU processing will
                # take place instead.
                raise e

            else:
                self.vaos.append(vao)
                self.vbo_vertices.append(vbo_vertices)
                self.vbo_normals.append(vbo_normals)
                self.ebos.append(ebo)
                self.counts.append(count)

        local_aabb = _utils.compute_aabb(*vertices)
        self.local_obb = _utils.compute_obb(*local_aabb)
        self.local_aabb = np.array([item.as_numpy for item in local_aabb])

    def __del__(self):
        for vao, vbo_vertices, vbo_normals, ebo in zip(
            self.vaos, self.vbo_vertices, self.vbo_normals, self.ebos
        ):
            self._release_buffers(vao, vbo_vertices, vbo_normals, ebo)

        del self.vaos[:]
        del self.vbo_vertices[:]
        del self.vbo_normals[:]
        del self.ebos[:]
        del self.counts[:]

    @staticmethod
    def _release_buffers(vao=None, vbo_vertices=None, vbo_normals=None, ebo=None):
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

        if ebo is not None:
            try:
                GL.glDeleteBuffers(1, [ebo])
            except:  # NOQA
                pass

    @classmethod
    def _create_vbo(cls, vertices, normals, indices, count):
        vao = None
        vbo_vertices = None
        vbo_normals = None
        ebo = None

        try:
            # Create VAO
            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)
            # Check for OpenGL errors
            err = GL.glGetError()
            if err != GL.GL_NO_ERROR:
                raise RuntimeError(f"OpenGL error creating vao: {err}")

            # Vertex buffer
            vbo_vertices = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_vertices)

            GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes,
                            vertices, GL.GL_STATIC_DRAW)

            # Check for OpenGL errors
            err = GL.glGetError()
            if err != GL.GL_NO_ERROR:
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
                raise RuntimeError(f"OpenGL error creating normals buffer: {err}")

            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

            # Element buffer
            ebo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)

            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes,
                            indices, GL.GL_STATIC_DRAW)

            # Check for OpenGL errors
            err = GL.glGetError()
            if err != GL.GL_NO_ERROR:
                raise RuntimeError(f"OpenGL error creating ebo: {err}")

            GL.glBindVertexArray(0)
            return vao, vbo_vertices, vbo_normals, ebo, int(count / 3)

        except (Exception, RuntimeError) as e:
            cls._release_buffers(vao, vbo_vertices, vbo_normals, ebo)
            raise e

    def render(self):

        for i, vao in enumerate(self.vaos):
            GL.glBindVertexArray(vao)
            GL.glDrawElements(GL.GL_TRIANGLES, self.counts[i], GL.GL_UNSIGNED_INT, None)
            GL.glBindVertexArray(0)
