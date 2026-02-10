
import build123d
import numpy as np

from .mixins import angle as _arrow_angle
from .mixins import move as _arrow_move
from . import cavity as _cavity

try:
    from .. import gl_object as _gl_object
    from ..geometry import point as _point
    from ..geometry import angle as _angle
    from ..geometry import line as _line
    from ..wrappers.wrap_decimal import Decimal as _decimal
    from .. import debug as _debug
    from ..model_loaders import stl as _stl_loader
    from ..model_loaders import obj as _obj_loader
    from ..model_loaders import stp as _stp_loader

except ImportError:
    import gl_object as _gl_object # NOQA
    from geometry import point as _point  # NOQA
    from geometry import angle as _angle  # NOQA
    from geometry import line as _line
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA
    import debug as _debug  # NOQA
    from model_loaders import stl as _stl_loader  # NOQA
    from model_loaders import obj as _obj_loader  # NOQA
    from model_loaders import stp as _stp_loader  # NOQA


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value


@_debug.timeit
def _build_model(
    p1: _point.Point,
    p2: _point.Point,
    diameter: _decimal,
    has_stripe: bool
):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0)

    # path = build123d.Circle(float(wire_radius))
    #
    # model = build123d.extrude(path, float(wire_length), dir=[0.0, 0.0, 1.0])
    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    if has_stripe:
        # Extract the axis of rotation from the wire to create the stripe
        wire_axis = model.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

        # the stripe is actually a separate 3D object and it carries with it a thickness.
        # The the stripe is not thick enough the wire color will show through it. We don't
        # want to use a hard coded thickness because the threshold for for this happpening
        # causes the stripe thickness to increaseto keep the "bleed through" from happening.
        # A remap of the diameter to a thickness range is done to get a thickness where the
        # bleed through will not occur while keeping the stripe from looking like it is not
        # apart of the wire.
        stripe_thickness = remap(
            diameter, old_min=_decimal(0.5), old_max=_decimal(5.0),
            new_min=_decimal(0.005), new_max=_decimal(0.005)
            )

        edges = model.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(0, float(diameter / _decimal(3.0)))

        stripe_arc = build123d.Face(
            edges.offset_2d(0.01, side=build123d.Side.RIGHT))

        # Define the twist path to follow the wire
        twist = build123d.Helix(
            pitch=float(wire_length / _decimal(2.0)),
            height=float(wire_length),
            radius=float(wire_radius),
            center=wire_axis.position,
            direction=wire_axis.direction,
        )

        # Sweep the arc to create the stripe
        s_line = build123d.Line(
            wire_axis.position, float(wire_length) * wire_axis.direction)

        stripe = build123d.sweep(stripe_arc, s_line, binormal=twist)
    else:
        stripe = None

    return convert_model_to_mesh(stripe)


import math
import numpy as np
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location


def convert_model_to_mesh(model):
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

    return compute_smoothed_vertex_normals(vertices, faces)


@_debug.timeit
def create_cylinder(radius=0.5, height=1.0):
    resolution = 360
    split = 1

    count = resolution * (split + 1) + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

    vertices[0] = np.array([0.0, 0.0, height * 0.5], dtype=np.float64)
    vertices[1] = np.array([0.0, 0.0, -height * 0.5], dtype=np.float64)

    step = math.pi * 2.0 / float(resolution)
    h_step = height / float(split)

    for i in range(split + 1):
        for j in range(resolution):
            theta = float(step) * float(j)
            vertices[2 + resolution * i + j] = np.array(
                [math.cos(theta) * radius,
                 math.sin(theta) * radius,
                 height * 0.5 - h_step * i], dtype=np.float64)

    # // Triangles for top and bottom face.
    # for (int j = 0; j < resolution; j++) {
    #     int j1 = (j + 1) % resolution;
    #     int base = 2;
    #     mesh->triangles_.push_back(Eigen::Vector3i(0, base + j, base + j1));
    #     base = 2 + resolution * split;
    #     mesh->triangles_.push_back(Eigen::Vector3i(1, base + j1, base + j));
    # }

    # Triangles for cylindrical surface.

    vertices += np.array([0.0, 0.0, height / 2], dtype=np.float64)

    faces = []
    for i in range(split):
        base1 = 2 + resolution * i
        base2 = base1 + resolution

        for j in range(resolution):
            j1 = int((j + 1) % resolution)
            faces.append([base2 + j, base1 + j1, base1 + j])
            faces.append([base2 + j, base2 + j1, base1 + j1])

    faces = np.array(faces, dtype=np.int32)
    return compute_smoothed_vertex_normals(vertices, faces)

def compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:

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


def compute_smoothed_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:

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

    # normalize face normals to unit vectors,
    # but keep zeros for degenerate faces
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

    # Add each face's normal to its three vertices
    # (np.add.at handles repeated indices)
    # Repeat face normals 3 times so they match faces.ravel()

    repeated_face_normals = np.repeat(
        face_normals, 3, axis=0)  # shape (F*3, 3)

    vertex_indices = faces.ravel()  # shape (F*3,)
    np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

    # normalize per-vertex summed normals
    vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
    safe_vn_norm = np.maximum(vn_norm, 1e-6)
    vertex_normals = vertex_normal_sum / safe_vn_norm

    # set zero normals where there was no contribution
    # (degenerate isolated vertices)
    isolated = (vn_norm.squeeze() < 1e-6)
    if np.any(isolated):
        vertex_normals[isolated] = 0.0

    # produce per-triangle per-vertex normals
    normals = vertex_normals[faces].reshape(-1, 3)  # shape (F, 3, 3)

    return triangles, normals, len(triangles) * 3


class Housing(_gl_object.GLObject, _arrow_move.MoveMixin, _arrow_angle.AngleMixin):

    def __init__(self, parent, file, position: _point.Point, num_pins=6, num_rows=1, blade_size=1.5):
        super().__init__()
        self.parent = parent
        self._detent_update_counter: int = 0

        self.cavities = []

        self.num_pins = num_pins
        self.num_rows = num_rows
        self.blade_size = blade_size

        tris, normals, count = create_cylinder()

        position = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        scale = _point.Point(_decimal(10.0), _decimal(10.0), _decimal(50.0))
        sscale = _point.Point(_decimal(10.0), _decimal(10.0), _decimal(50.0))

        stris, snrmls, scount = _build_model(position, _point.Point(_decimal(0.0), _decimal(0.0), _decimal(1.0)), _decimal(1.0), True)

        tris *= scale
        stris *= sscale

        # self._verts, self._faces = self._read_mesh(file)
        #
        # tris, normals, count = self.get_mesh_triangles(self._verts, self._faces)

        verts = tris.reshape(-1, 3)

        col_min = verts.min(axis=0)  # shape (3,) -> array([-0.7,  0.3, -1. ])
        col_max = verts.max(axis=0)  # shape (3,) -> array([1.2, 3.1, 4. ])

        p1 = _point.Point(*[_decimal(item) for item in col_min])
        p2 = _point.Point(*[_decimal(item) for item in col_max])

        self.hit_test_rect = [[p1, p2]]
        self.adjust_hit_points()

        p1, p2 = self.hit_test_rect[0]

        # center = ((p2 - p1) / _decimal(2.0)) + p1
        # c_offset = _point.Point(-center.x, -center.y, -center.z)
        # tris += c_offset
        #
        # p1 += c_offset
        # p2 += c_offset

        self._point = position
        self._o_point = self._point.copy()
        self._point.bind(self._update_point)

        self._angle = _angle.Angle()

        self._o_angle = self._angle.copy()
        self._angle.bind(self._update_angle)

        self._colors = [
            np.full((count, 4), [0.4, 0.4, 0.4, 1.0], dtype=np.float32),
            np.full((count, 4), [0.5, 0.5, 1.0, 0.40], dtype=np.float32),
            np.full((count, 4), [0.5, 1.0, 0.5, 0.40], dtype=np.float32),
            np.full((count, 4), [0.4, 1.0, 1.0, 1.0], dtype=np.float32),
            np.full((count, 4), [1.0, 1.0, 0.5, 0.40], dtype=np.float32),
            np.full((count, 4), [1.0, 0.3, 0.3, 0.40], dtype=np.float32),

        ]

        normals @= self.angle
        tris @= self.angle
        tris += position

        p1 @= self.angle
        p2 @= self.angle

        p1 += position
        p2 += position

        self.adjust_hit_points()
        self._triangles = [[tris, normals, count], [stris, snrmls, scount]]

        parent.canvas.add_object(self)

    def release_mouse(self):
        self._detent_update_counter = 0

    def get_first_points(self):
        tris = self._triangles[0][0]
        p = _point.Point(_decimal(tris[0][0][0]), _decimal(tris[0][0][1]), _decimal(tris[0][0][2]))
        return [p]

    @property
    def triangles(self):
        triangles = []
        for i, (tris, norms, count) in enumerate(self._triangles):
            if self._is_selected and self._detent_update_counter:
                color = self._colors[(i + 1) * 2]
            else:
                color = self._colors[(i + 1) * ((int(self._is_selected)) + 1) - 1]

            triangles.append([tris, norms, color, count, color[0][-1] == 1.0])
        return triangles

    def get_canvas(self):
        return self.parent.canvas

    @property
    def position(self) -> _point.Point:
        return self._point

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    @_debug.timeit
    def _update_point(self, point: _point.Point):
        delta = point - self._o_point
        self._o_point = point.copy()

        self._triangles[0][0] += delta

        for p in self.hit_test_rect[0]:
            p += delta

        self.adjust_hit_points()

    @_debug.timeit
    def _update_angle(self, angle: _angle.Angle):
        delta = angle - self._o_angle
        self._o_angle = angle.copy()

        self._triangles[0][0] -= self._point

        self._triangles[0][0] @= delta
        self._triangles[0][1] @= delta

        # self.triangles[3][0] += self._point
        self._triangles[0][0] += self._point

        for p in self.hit_test_rect[0]:
            p -= self._point
            p @= delta
            p += self._point

        self.adjust_hit_points()

    def add_cavity(self):
        if len(self.cavities) < 6:
            index = len(self.cavities)
            name = 'ABCDEF'[index]

            pos = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
            angle = _angle.Angle.from_quat(np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64))
            length = _decimal(40.0)

            self.cavities.append(_cavity.Cavity(self, index, name, angle=angle, point=pos,
                                                length=length, terminal_size=_decimal(1.5)))

    @staticmethod
    def _read_mesh(file: str):
        if file.endswith('.stl'):
            verts, faces = _stl_loader.load_from_stl(file)

        elif file.endswith('obj'):
            verts, faces = _obj_loader.load_from_obj(file)

        elif file.endswith('3mf'):
            raise NotImplementedError

        elif file.endswith('step') or file.endswith('stp'):
            verts, faces = _stp_loader.load_from_stp(file)

        else:
            raise NotImplementedError

        return verts, faces
