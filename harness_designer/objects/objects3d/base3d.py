from typing import TYPE_CHECKING, Union

import numpy as np
from OpenGL import GL

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

from ... import debug as _debug
from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ... import Config
from ... import gl_materials as _gl_materials
from ...wrappers import color as _color

if TYPE_CHECKING:
    from ...editor_3d.canvas import canvas as _canvas
    from ...database import project_db as _project_db
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui


Config = Config.editor3d


class Base3D:

    def __init__(self, parent: Union["_ObjectBase", "_ui.MainFrame"]):
        self._parent: Union["_ObjectBase", "_ui.MainFrame"] = parent

        try:
            self.editor3d = parent.mainframe.editor3d
        except AttributeError:
            self.editor3d = parent.editor3d

        self.canvas: "_canvas.Canvas" = self.editor3d.canvas
        self.mainframe: "_ui.MainFrame" = self.canvas.mainframe

        self._db_obj: _project_db.PJTEntryBase = None
        self._position: _point.Point = None
        self._material: _gl_materials.GLMaterial | None = None
        self._color: _color.Color = None
        self._is_selected = False
        self._position: _point.Point = None

        # stores the verticies and faces so normals or smooth normals
        # can be calculated if the user changes the setting for it.
        self._mesh: list[list[np.ndarray, np.ndarray]] = []

        # stores the build123d.Shape instances if any.
        # I am still hammering this one out specifically for the wires and
        # bundles because of the length of the wire/bundle needing to change
        # I am more than likely going to use some kind of an agnostic to
        # represent the wire/bundle as one of the ends are being dragged.
        # this is because it is far too expensive to build the shape using
        # build123d unless I can figure out the equations needed to build
        # the cylinder with optional stripe.

        # TODO: look into code for creating a cylinder and a helical spiral
        #       using numpy.

        self._models = []

        # [triangles, normals, triangle_count, material, color, is_opaque]
        self._triangles: list[Union["TriangleRenderer", "LineRenderer"]] = []

        self._rect: list[list[_point.Point, _point.Point]] = []
        self._bb: list[np.ndarray] = []

    @property
    def rect(self) -> list[list[_point.Point, _point.Point]]:
        return self._rect

    @property
    def triangles(self) -> list[Union["TriangleRenderer", "LineRenderer"]]:
        return self._triangles

    @property
    def position(self) -> _point.Point:
        return self._position

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
            color = Config.selected_color
            self._material.x_ray_color = color
            self._material.x_ray = True
        else:
            self._material.x_ray = False

        self._is_selected = flag

    def delete(self):
        self._db_obj.delete()

    # Performance between calculating smoothed normals and face normals can be
    # significant with smooth normals taking ~2x mopr time to calculate.
    # this only gets done when an item is added and the normals are cached. The only
    # impact would be seen when loading a project that has many objects defined
    # in it.

    # 26,060 triangles
    # compute_vertex_normals: 4.0ms
    # compute_smoothed_vertex_normals: 9.0ms
    @staticmethod
    @_debug.timeit
    def _compute_smoothed_vertex_normals(vertices, faces):
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

        # produce per-triangle per-vertex normals
        normals = vertex_normals[faces].reshape(-1, 3)  # shape (F, 3, 3)

        return triangles, normals, len(triangles) * 3

    @staticmethod
    @_debug.timeit
    def _compute_vertex_normals(vertices, faces):
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

        # (F, 3, 3)ach face normal to the 3 vertices of the triangle
        normals = np.repeat(face_normals[:, np.newaxis, :], 3, axis=1)

        return triangles, normals.reshape(-1, 3), len(triangles) * 3

    @staticmethod
    def _compute_bb(p1, p2):
        x1, y1, z1 = p1.as_float
        x2, y2, z2 = p2.as_float

        corners = np.array([[x1, y1, z1], [x1, y1, z2], [x1, y2, z1], [x1, y2, z2],
                           [x2, y1, z1], [x2, y1, z2], [x2, y2, z1], [x2, y2, z2]],
                           dtype=np.float64)

        return corners

    @staticmethod
    def _compute_rect(tris):
        verts = tris.reshape(-1, 3)

        col_min = verts.min(axis=0)  # shape (3,) -> array([-0.7,  0.3, -1. ])
        col_max = verts.max(axis=0)  # shape (3,) -> array([1.2, 3.1, 4. ])

        p1 = _point.Point(*[_decimal(item) for item in col_min])
        p2 = _point.Point(*[_decimal(item) for item in col_max])

        return p1, p2

    @staticmethod
    def _convert_model_to_mesh(model):
        loc = TopLoc_Location()
        BRepMesh_IncrementalMesh(theShape=model.wrapped, theLinDeflection=0.001,
                                 isRelative=True, theAngDeflection=0.1, isInParallel=True)

        vertices = []
        faces = []
        offset = 0
        for facet in model.faces():
            if not facet:
                continue

            poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

            if not poly_triangulation:
                continue

            trsf = loc.Transformation()

            node_count = poly_triangulation.NbNodes()
            for i in range(1, node_count + 1):
                gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
                pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
                vertices.append(pnt)

            facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

            order = [1, 3, 2] if facet_reversed else [1, 2, 3]
            for tri in poly_triangulation.Triangles():
                faces.append([tri.Value(i) + offset - 1 for i in order])

            offset += node_count

        vertices = np.array(vertices, dtype=np.dtypes.Float64DType)
        faces = np.array(faces, dtype=np.dtypes.Int32DType)

        return vertices, faces


# I moved some of the rendering code to the 2 below classes.
# This allows me to create an alternative representation of things like wires
# and bundles which become expensive if needing to redraw them as the mouse
# moves (click and drag). For those 2 cases the cylinder model gets replaced
# with a line that has a width that matches the diameter. There are no triangles
# to render so it should be able to keep up and provide a nice smooth user
# experiance.
class TriangleRenderer:

    def __init__(self, data: list[list[np.ndarray, np.ndarray, int]], material: _gl_materials.GLMaterial):
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
    def material(self) -> _gl_materials.GLMaterial:
        return self._material

    @material.setter
    def material(self, value: _gl_materials.GLMaterial):
        self._material = value

    def __call__(self):
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

        self._material.set()

        for tris, nrmls, count in self._data:
            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, tris)
            GL.glNormalPointer(GL.GL_DOUBLE, 0, nrmls)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

        self._material.unset()

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)


class LineRenderer:

    def __init__(self, p1, p2, width, material):
        self._p1 = p1
        self._p2 = p2
        self._material = material
        self._width = width

    @property
    def is_opaque(self) -> bool:
        return self._material.is_opaque

    @property
    def material(self) -> _gl_materials.GLMaterial:
        return self._material

    @material.setter
    def material(self, value: _gl_materials.GLMaterial):
        self._material = value

    @property
    def data(self) -> list:
        return []

    @data.setter
    def data(self, value: list):
        pass

    def __call__(self):
        self._material.set()
        # top
        GL.glLineWidth(float(self._width))
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(*self._p1.as_float)
        GL.glVertex3f(*self._p2.as_float)
        GL.glEnd()
        self._material.unset()
