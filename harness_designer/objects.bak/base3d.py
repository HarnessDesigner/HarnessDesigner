from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL


from ..geometry import point as _point
from ..geometry import angle as _angle
from .. import config as _config
from ..wrappers import materials as _materials
from ..ui.editor_3d import vbo_handler as _vbo_handler
from .. import debug as _debug

if TYPE_CHECKING:
    from ..ui import editor_3d as _editor_3d

Config = _config.Config


class Base3D:

    @_debug.logfunc
    def __init__(self, editor_3d: "_editor_3d.Editor3D", material: _materials.GLMaterial,
                 selected_material: _materials.GLMaterial, smooth: bool,
                 data: list[list[np.ndarray, np.ndarray]] | list[list[np.ndarray, np.ndarray, int]],
                 position: _point.Point | None, angle: _angle.Angle | None):

        self.editor_3d = editor_3d

        self._position: _point.Point = None
        self._material = material
        self._selected_material = selected_material
        self._is_selected = False

        if position is None:
            position = _point.Point(0, 0, 0)
        if angle is None:
            angle = _angle.Angle()

        self._position = position
        self._o_position = position.copy()
        self._angle = angle
        self._o_angle = angle.copy()
        self._reduce_settings = None
        self._smooth = smooth

        position.bind(self._update_position)
        angle.bind(self._update_angle)

        # stores the verticies and faces so normals or smooth normals
        # can be calculated if the user changes the setting for it.
        self._mesh: list[list[np.ndarray, np.ndarray]] = data

        self._rect: list[list[_point.Point, _point.Point]] | list[list[np.ndarray, np.ndarray, int]] = []
        self._bb: list[np.ndarray] = []
        self._triangles: list["TriangleRenderer"] = []

        self._build()
        editor_3d.AddObject(self)

    def delete(self):
        self.editor_3d.RemoveObject(self)

    @property
    def smooth(self) -> bool:
        return self._smooth

    @smooth.setter
    def smooth(self, value: bool):
        self._smooth = value
        self._build()

    @_debug.logfunc
    def _build(self):
        from .. import model_loader as _model_loader

        data = self._mesh
        angle = self._angle
        position = self._position

        triangles = []

        rect = []
        bb = []

        for items in data:
            if len(items) == 2:
                vertices, faces = items

                if self._reduce_settings is not None:
                    vertices, faces = _model_loader.reduce_triangles(
                        vertices, faces, *self._reduce_settings
                    )

                if self._smooth:
                    tris, nrmls, count = self._compute_smoothed_vertex_normals(vertices, faces)
                else:
                    tris, nrmls, count = self._compute_vertex_normals(vertices, faces)

                tris @= angle
                nrmls @= angle

                tris += position

            else:
                tris, nrmls, count = items

            p1, p2 = self._compute_rect(tris)
            rect.append([p1, p2])
            bb.append(self._compute_bb(p1, p2))
            self._adjust_hit_points(p1, p2)
            triangles.append([tris, nrmls, count])

        self._rect = rect
        self._bb = bb

        if self._triangles:
            material = self._triangles[0].material
        else:
            material = self._material

        self._triangles = [TriangleRenderer(triangles, material)]

        for p1, p2 in rect:
            if p1.y < Config.ground_height:
                self.position.y -= p1.y

    @property
    def vertices_count(self) -> int:
        res = 0

        for renderer in self._triangles:
            for item in renderer.data:
                res += item[2]

        return res

    @_debug.logfunc
    def reduce_mesh(self, target_vertice_count: int | None,
                    agressiveness: float = 4.5):

        if target_vertice_count is None:
            self._reduce_settings = None
        else:
            self._reduce_settings = [target_vertice_count, agressiveness]

        self._build()
        self.canvas.Refresh()

    @_debug.logfunc
    def _update_position(self, point: _point.Point):
        delta = point - self._o_position
        self._o_position = point.copy()

        for p1, p2 in self._rect:
            if p1.y + delta.y < Config.ground_height:
                self._position.y -= p1.y
                return

            if p2.y + delta.y < Config.ground_height:
                self._position.y -= p2.y
                return

        for renderer in self._triangles:
            data = renderer.data
            for i, (tris, nrmls, count) in enumerate(data):
                tris += delta

                data[i] = [tris, nrmls, count]

            renderer.data = data

        for p1, p2 in self._rect:
            p1 += delta
            p2 += delta
            self._adjust_hit_points(p1, p2)

        for i, bb in enumerate(self._bb):
            bb += delta
            self._bb[i] = bb

        self.canvas.Refresh(False)

    @_debug.logfunc
    def _update_angle(self, angle: _angle.Angle):
        delta = angle - self._o_angle
        self._o_angle = angle.copy()

        for renderer in self._triangles:
            data = renderer.data
            for i, (tris, nrmls, count) in enumerate(data):
                tris -= self._position
                tris @= delta
                tris += self._position

                nrmls @= delta

                data[i] = [tris, nrmls, count]

            renderer.data = data

        for p1, p2 in self._rect:
            p1 -= self._position
            p2 -= self._position

            p1 @= delta
            p2 @= delta

            p1 += self._position
            p2 += self._position

            self._adjust_hit_points(p1, p2)

        for i, bb in enumerate(self._bb):
            bb -= self._position
            bb @= delta
            bb += self._position
            self._bb[i] = bb

        self.canvas.Refresh(False)

    @property
    def rect(self) -> list[list[_point.Point, _point.Point]]:
        return self._rect

    @property
    def bb(self) -> list[np.ndarray]:
        return self._bb

    @property
    def triangles(self) -> list["TriangleRenderer"]:
        return self._triangles

    @property
    def position(self) -> _point.Point:
        return self._position

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    @staticmethod
    def _adjust_hit_points(p1: _point.Point, p2: _point.Point):
        xmin = min(p1.x, p2.x)
        ymin = min(p1.y, p2.y)
        zmin = min(p1.z, p2.z)
        xmax = max(p1.x, p2.x)
        ymax = max(p1.y, p2.y)
        zmax = max(p1.z, p2.z)

        delta = _point.Point(xmin, ymin, zmin) - p1
        p1 += delta

        delta = _point.Point(xmax, ymax, zmax) - p2
        p2 += delta

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, flag: bool):
        if flag:
            for renderer in self._triangles:
                renderer.material = self._selected_material
        else:
            for renderer in self._triangles:
                renderer.material = self._material

        self._is_selected = flag

    # Performance between calculating smoothed normals and face normals can be
    # significant with smooth normals taking ~2x mopr time to calculate.
    # this only gets done when an item is added and the normals are cached. The only
    # impact would be seen when loading a project that has many objects defined
    # in it.

    # 26,060 triangles
    # compute_vertex_normals: 4.0ms
    # compute_smoothed_vertex_normals: 9.0ms
    @staticmethod
    @_debug.logfunc
    def _compute_smoothed_vertex_normals(vertices, faces):
        """
        Compute smoothed vertex normals by averaging face normals at each vertex.

        Args:
            vertices: numpy array of shape (V, 3) - unique vertex positions
            faces: numpy array of shape (F, 3) - triangle indices into vertices array

        Returns:
            tuple: (vertices_array, normals_array, indices_array)
                - vertices_array: flattened array of vertex positions (V*3,)
                - normals_array: flattened array of vertex normals (V*3,)
                - indices_array: flattened array of triangle indices (F*3,)
        """
        # triangle coordinates (F, 3, 3)
        triangles = vertices[faces]

        # compute two edges per triangle
        v0 = triangles[:, 0, :]
        v1 = triangles[:, 1, :]
        v2 = triangles[:, 2, :]

        e1 = v1 - v0
        e2 = v2 - v0

        # raw face normal (not normalized): proportional to area * 2
        face_normals_raw = np.cross(e1, e2)  # shape (F, 3)  # NOQA

        # normalize face normals to unit vectors, but keep zeros for degenerate faces
        norm = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)
        # avoid dividing by zero
        safe_norm = np.maximum(norm, 1e-6)
        face_normals = face_normals_raw / safe_norm
        # optionally set truly tiny normals to zero to avoid adding noise
        tiny = (norm.squeeze() < 1e-6)

        if np.any(tiny):
            face_normals[tiny] = 0.0

        # accumulate face normals into per-vertex sum
        V = len(vertices)
        vertex_normal_sum = np.zeros((V, 3), dtype=float)

        # Add each face's normal to its three vertices (np.add.at handles repeated indices)
        # Repeat face normals 3 times so they match faces.ravel()
        repeated_face_normals = np.repeat(face_normals, 3, axis=0)  # shape (F*3, 3)
        vertex_indices = faces.ravel()  # shape (F*3,)
        np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

        # normalize per-vertex summed normals
        vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
        safe_vn_norm = np.maximum(vn_norm, 1e-6)
        vertex_normals = vertex_normal_sum / safe_vn_norm

        # set zero normals where there was no contribution (degenerate isolated vertices)
        isolated = (vn_norm.squeeze() < 1e-6)
        if np.any(isolated):
            vertex_normals[isolated] = 0.0

        # Return arrays suitable for VBO:
        # - vertices: flattened unique vertex positions
        # - normals: per-vertex normals (one per vertex, smoothed across faces)
        # - indices: triangle indices into the vertices array
        vertices_array = vertices.astype(np.float32).ravel()  # (V*3,)
        normals_array = vertex_normals.astype(np.float32).ravel()  # (V*3,)
        indices_array = faces.astype(np.uint32).ravel()  # (F*3,)

        return vertices_array, normals_array, indices_array, len(indices_array) * 3

    @staticmethod
    @_debug.logfunc
    def _compute_vertex_normals(vertices, faces):
        """
        Compute flat-shaded vertex normals (face normals replicated per vertex).
        For flat shading, each triangle gets its own vertices (no sharing).

        Args:
            vertices: numpy array of shape (V, 3) - original vertex positions
            faces: numpy array of shape (F, 3) - triangle indices into vertices array

        Returns:
            tuple: (vertices_array, normals_array, indices_array)
                - vertices_array: flattened array of vertex positions (F*9,)
                - normals_array: flattened array of face normals (F*9,)
                - indices_array: flattened array of sequential indices (F*3,)
        """
        triangles = vertices[faces]  # (F, 3, 3)
        v0 = triangles[:, 0, :]
        v1 = triangles[:, 1, :]
        v2 = triangles[:, 2, :]

        e1 = v1 - v0
        e2 = v2 - v0
        face_normals_raw = np.cross(e1, e2)  # (F, 3)  # NOQA

        norms = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)
        safe = np.maximum(norms, 1e-6)
        face_normals = face_normals_raw / safe

        # set exact-degenerate faces to zero if extremely small
        degenerate = (norms.squeeze() < 1e-6)
        if np.any(degenerate):
            face_normals[degenerate] = 0.0

        # Replicate each face normal to the 3 vertices of the triangle
        normals = np.repeat(face_normals[:, np.newaxis, :], 3, axis=1)  # (F, 3, 3)

        # For flat shading, we need unique vertices per triangle (no sharing)
        # So we expand triangles and create sequential indices
        num_triangles = len(triangles)
        vertices_array = triangles.astype(np.float32).ravel()  # (F*9,) - all triangle vertices
        normals_array = normals.astype(np.float32).ravel()  # (F*9,) - replicated face normals
        indices_array = np.arange(num_triangles * 3, dtype=np.uint32)  # (F*3,) - sequential 0,1,2,3,4,5...

        return vertices_array, normals_array, indices_array, len(indices_array) * 3

    @staticmethod
    @_debug.logfunc
    def _compute_bb(p1, p2):
        x1, y1, z1 = p1.as_float
        x2, y2, z2 = p2.as_float

        corners = np.array([[x1, y1, z1], [x1, y1, z2],
                            [x1, y2, z1], [x1, y2, z2],
                            [x2, y1, z1], [x2, y1, z2],
                            [x2, y2, z1], [x2, y2, z2]],
                           dtype=np.float64)

        return corners

    @staticmethod
    @_debug.logfunc
    def _compute_rect(tris):
        verts = tris.reshape(-1, 3)

        col_min = verts.min(axis=0)  # shape (3,) -> array([-0.7,  0.3, -1. ])
        col_max = verts.max(axis=0)  # shape (3,) -> array([1.2, 3.1, 4. ])

        p1 = _point.Point(*col_min)
        p2 = _point.Point(*col_max)

        return p1, p2



# I moved some of the rendering code to the 2 below classes.
# This allows me to create an alternative representation of things like wires
# and bundles which become expensive if needing to redraw them as the mouse
# moves (click and drag). For those 2 cases the cylinder model gets replaced
# with a line that has a width that matches the diameter. There are no triangles
# to render so it should be able to keep up and provide a nice smooth user
# experiance.
class TriangleRenderer:

    def __init__(self, position: _point.Point, angle: _angle.Angle, material: _materials.GLMaterial,
                 vbo: _vbo_handler.VBOHandler | None = None, data: list[list[np.ndarray, np.ndarray, int]] | None = None):

        self.vbo = vbo
        self.position = position
        self.angle = angle
        self._data = data
        self._material = material

    @property
    def is_opaque(self) -> bool:
        return self._material.is_opaque

    @property
    def data(self) -> list[list[np.ndarray, np.ndarray, int]]:
        return self._data

    @data.setter
    def data(self, value: list[list[np.ndarray, np.ndarray, int]]):
        self._data = value

    @property
    def material(self) -> _materials.GLMaterial:
        return self._material

    @material.setter
    def material(self, value: _materials.GLMaterial):
        self._material = value

    @_debug.logfunc
    def __call__(self, shader_program):
        # There are some objects that are going to have a known existance
        # of only 1 and using the GPU to store these objects would not be a
        # good use if available resources. Some of the objects are also very
        # dynamic in nature and are handled by the CPU. Obejcts like Transitions,
        # Wires and Bundles are some examples.
        # Wire layouts and Bundle layouts will reside on the GPU due to their
        # simple nature and being used multiple times. These will not use
        # a GUID as identifiction. They will have an ID of "LAYOUT-{diameter}"
        # where diameter is the diameter of the layout. Another object type is
        # wire service loops. These will also reside on the GPU and their id
        # will be "WIRE_SERVICE_LOOP-{size}" where size will be the cross
        # section in mm's.

        # TODO: Work out the handling for specifying multiple materials for
        #       objects that have multiple sets of triangles being rendered

        if self.vbo is None:
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

            for tris, nrmls, count in self._data:
                GL.glVertexPointer(3, GL.GL_DOUBLE, 0, tris)
                GL.glNormalPointer(GL.GL_DOUBLE, 0, nrmls)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

        else:
            self.vbo.render(shader_program, self.position, self.angle, self.material)
        