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
        
        # Ref-counting for shared VBO resources
        self._ref_count = 0

        # Compute AABB/OBB (CPU-side, doesn't need OpenGL context)
        local_aabb = _utils.compute_aabb(vertices.reshape(-1, 3))
        self.local_obb = _utils.compute_obb(*local_aabb)

        p1, p2 = local_aabb
        self.local_aabb = np.array([p1.as_numpy, p2.as_numpy], dtype=np.float64)

    @property
    def ready(self) -> bool:
        """Check if VBO resources are allocated and ready to use."""
        return self._ref_count > 0 and self.__vbo_vertices is not None

    def acquire(self):
        """
        Increment ref-count and allocate GPU resources on first acquire.
        
        This should be called by each canvas in initializeGL() to ensure
        the shared VBOs exist and to track that this context is using them.
        """
        if self._ref_count == 0:
            # First acquire - allocate shared VBOs
            ctx = QOpenGLContext.currentContext()
            if ctx is None:
                raise RuntimeError("No OpenGL context is current")
            
            (
                vao,
                self.__vbo_vertices,
                self.__vbo_normals,
                self.__vbo_faces,
                self.__vert_count
            ) = self._create_vbo(self.__vertices, self.__normals, self.__faces, self.__count)
            
            # Store the initial VAO for the context that created it
            ctx_id = id(ctx)
            self.__vaos[ctx_id] = vao
            
        self._ref_count += 1

    def release(self):
        """
        Decrement ref-count and free GPU resources when count reaches zero.
        
        This should be called by each canvas in cleanup() to indicate
        it's done using the shared VBOs.
        """
        if self._ref_count <= 0:
            return
            
        self._ref_count -= 1
        
        if self._ref_count == 0:
            # Last reference released - free all resources
            ctx = QOpenGLContext.currentContext()
            if ctx is None:
                # No context current — buffers will be leaked but won't crash
                return
            
            # Clean up all VAOs across all contexts
            for vao in self.__vaos.values():
                self._release_vao(vao)
            
            # Clean up shared VBOs
            self._release_vbos(self.__vbo_vertices, self.__vbo_normals, self.__vbo_faces)

            self.__vaos.clear()
            self.__vbo_vertices = None
            self.__vbo_normals = None
            self.__vbo_faces = None
            self.__vert_count = 0

    def release_context_vao(self):
        """
        Release the VAO for the current context only.
        
        This should be called when a specific canvas/context is being destroyed
        but other contexts may still be using the shared VBOs.
        """
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
            
        ctx_id = id(ctx)
        if ctx_id in self.__vaos:
            vao = self.__vaos[ctx_id]
            self._release_vao(vao)
            del self.__vaos[ctx_id]

    @property
    def vertices(self):
        return self.__vertices

    @property
    def faces(self):
        return self.__faces

    def __del__(self):
        # Safety net: If ref_count is still > 0, there's a cleanup bug
        # but we still need to free resources to avoid leaks
        if self._ref_count > 0:
            # Log warning if we had a way to do so
            pass
        
        # Add context guard to prevent crashes when no context is current
        if QOpenGLContext.currentContext() is None:
            # No context current — buffers will be leaked but won't crash
            return
        
        # Clean up all VAOs across all contexts
        for vao in self.__vaos.values():
            self._release_vao(vao)
        
        # Clean up shared VBOs
        self._release_vbos(self.__vbo_vertices, self.__vbo_normals, self.__vbo_faces)

        self.__vaos.clear()
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

    @staticmethod
    def _release_buffers(vao=None, vbo_vertices=None,
                         vbo_normals=None, vbo_faces=None):
        """Legacy method - kept for compatibility. Use _release_vao and _release_vbos instead."""
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

    def _get_or_create_vao(self):
        """Get or create a VAO for the current OpenGL context.
        
        VAOs are not shared across contexts, so we need to create one
        per context while reusing the shared VBOs.
        
        Automatically calls acquire() on first use by this context.
        
        Returns:
            int: VAO ID for the current context
        """
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError("No OpenGL context is current")
        
        # Use __builtins__.id to avoid shadowing by the 'id' parameter in __init__
        ctx_id = id(ctx)
        
        # Check if we already have a VAO for this context
        if ctx_id in self.__vaos:
            return self.__vaos[ctx_id]
        
        # New context is using this VBO - acquire it
        if self._ref_count == 0:
            # First acquire - allocate shared VBOs
            (
                vao,
                self.__vbo_vertices,
                self.__vbo_normals,
                self.__vbo_faces,
                self.__vert_count
            ) = self._create_vbo(self.__vertices, self.__normals, self.__faces, self.__count)
            
            # Store the VAO for this context
            self.__vaos[ctx_id] = vao
            self._ref_count += 1
            
            return vao
        
        # VBOs already exist, just create a new VAO for this context
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
        
        # Store the VAO for this context and increment ref count
        self.__vaos[ctx_id] = vao
        self._ref_count += 1
        
        return vao

    @classmethod
    def cleanup_all_for_context(cls):
        """
        Clean up VAOs and release resources for the current context across all VBOHandler instances.
        
        This should be called by each canvas in its cleanup() method.
        """
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        
        # Iterate through all VBOHandler instances
        for weak_ref in list(cls._instances.values()):
            instance = weak_ref()
            if instance is not None:
                # Release the VAO for this specific context
                instance.release_context_vao()
                # Release (decrement ref count)
                instance.release()

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
        # Get or create VAO for the current context
        vao = self._get_or_create_vao()
        
        GL.glBindVertexArray(vao)

        GL.glDrawElements(GL.GL_TRIANGLES, self.__vert_count,
                          GL.GL_UNSIGNED_INT, None)

        GL.glBindVertexArray(0)
