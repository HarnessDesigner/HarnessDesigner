from OpenGL import GL
from OpenGL import GLU

from OCP.gp import gp_Vec, gp
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

import numpy as np

import math

from . import RendererBase, DrawWrapperBase
from ...geometry import point as _point
from ...geometry import angle as _angle
# from ...geometry import line as _line
# from ... import config as _config
from ... import gl_materials as _gl_materials
from ...wrappers.decimal import Decimal as _decimal


def _get_triangles(ocp_mesh) -> tuple[np.ndarray, np.ndarray, int]:
    loc = TopLoc_Location()  # Face locations
    mesh = BRepMesh_IncrementalMesh(
        theShape=ocp_mesh.wrapped,
        theLinDeflection=0.001,
        isRelative=True,
        theAngDeflection=0.1,
        isInParallel=True,
    )

    mesh.Perform()

    triangles = []
    normals = []
    triangle_count = 0

    for facet in ocp_mesh.faces():
        if not facet:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if poly_triangulation is None:
            continue

        trsf = loc.Transformation()

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        for tri in poly_triangulation.Triangles():
            id0, id1, id2 = tri.Get()

            if facet_reversed:
                id1, id2 = id2, id1

            aP1 = poly_triangulation.Node(id0).Transformed(trsf)
            aP2 = poly_triangulation.Node(id1).Transformed(trsf)
            aP3 = poly_triangulation.Node(id2).Transformed(trsf)

            triangles.append([[aP1.X(), aP1.Y(), aP1.Z()],
                              [aP2.X(), aP2.Y(), aP2.Z()],
                              [aP3.X(), aP3.Y(), aP3.Z()]])

            aVec1 = gp_Vec(aP1, aP2)
            aVec2 = gp_Vec(aP1, aP3)
            aVNorm = aVec1.Crossed(aVec2)

            if aVNorm.SquareMagnitude() > gp.Resolution_s():  # NOQA
                aVNorm.Normalize()
            else:
                aVNorm.SetCoord(0.0, 0.0, 0.0)

            for _ in range(3):
                normals.extend([aVNorm.X(), aVNorm.Y(), aVNorm.Z()])

            triangle_count += 3

    return (np.array(normals, dtype=np.dtypes.Float64DType),
            np.array(triangles, dtype=np.dtypes.Float64DType),
            triangle_count)


def _get_smooth_triangles(ocp_mesh) -> tuple[np.ndarray, np.ndarray, int]:
    from .. import Config

    loc = TopLoc_Location()  # Face locations
    BRepMesh_IncrementalMesh(
        theShape=ocp_mesh.wrapped,
        theLinDeflection=0.001,
        isRelative=True,
        theAngDeflection=0.1,
        isInParallel=True,
    )

    ocp_mesh_vertices = []
    triangles = []
    offset = 0
    for facet in ocp_mesh.faces():
        if not facet:
            continue

        # Triangulate the face
        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()
        # Store the vertices in the triangulated face
        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            ocp_mesh_vertices.append(pnt)

        # Store the triangles from the triangulated faces

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            triangles.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count

    ocp_mesh_vertices = np.array(ocp_mesh_vertices, dtype=np.dtypes.Float64DType)
    triangles = np.array(triangles, dtype=np.dtypes.Int32DType)

    normals, triangles = (
        _make_per_corner_arrays(ocp_mesh_vertices, triangles, Config.renderer.smooth_weight))

    return normals, triangles, len(triangles)


def _safe_normalize(v, eps=1e-12) -> np.ndarray:
    """Normalize rows of v (shape (...,3)). Avoid divide-by-zero."""
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    norms = np.where(norms <= eps, 1.0, norms)
    return v / norms


def _compute_face_normals(v0, v1, v2) -> np.ndarray:
    """Un-normalized face normals (cross product e1 x e2)."""
    return np.cross(v1 - v0, v2 - v0)


def _compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray,
                            method: str = "angle") -> np.ndarray:
    """
    Compute per-vertex smooth normals.

    method: "angle" (angle-weighted), "area" (area-weighted), "uniform" (unweighted).
    Returns (N,3) array of normalized vertex normals.
    """
    # Gather triangle corners
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    face_normals = _compute_face_normals(v0, v1, v2)  # (F,3)

    N = vertices.shape[0]
    accum = np.zeros((N, 3), dtype=np.dtypes.Float64DType)

    if method == "area":
        # area-weighted accumulation (face_normals magnitude ~ 2*area*unit_normal)
        np.add.at(accum, faces[:, 0], face_normals)
        np.add.at(accum, faces[:, 1], face_normals)
        np.add.at(accum, faces[:, 2], face_normals)

    elif method == "angle":
        # angle-weighted accumulation
        # edges for corner angles
        e0 = v1 - v0  # edge v0->v1
        e1 = v2 - v1  # edge v1->v2
        e2 = v0 - v2  # edge v2->v0

        def corner_angle(a, b):
            # angle between vectors a and b, per-face (F,)
            na = np.linalg.norm(a, axis=1)
            nb = np.linalg.norm(b, axis=1)
            denom = na * nb
            denom = np.where(denom == 0, 1.0, denom)
            cosang = np.sum(a * b, axis=1) / denom
            cosang = np.clip(cosang, -1.0, 1.0)
            return np.arccos(cosang)

        ang0 = corner_angle(-e2, e0)  # angle at v0
        ang1 = corner_angle(-e0, e1)  # angle at v1
        ang2 = corner_angle(-e1, e2)  # angle at v2

        np.add.at(accum, faces[:, 0], face_normals * ang0[:, None])
        np.add.at(accum, faces[:, 1], face_normals * ang1[:, None])
        np.add.at(accum, faces[:, 2], face_normals * ang2[:, None])

    elif method == "uniform":
        # unweighted (each face contributes equally, normalized face normal)
        unit_face = _safe_normalize(face_normals)
        np.add.at(accum, faces[:, 0], unit_face)
        np.add.at(accum, faces[:, 1], unit_face)
        np.add.at(accum, faces[:, 2], unit_face)

    else:
        raise ValueError("method must be 'angle', 'area', or 'uniform'")

    # normalize per-vertex and handle zero-length
    vertex_normals = _safe_normalize(accum)
    zero_mask = np.linalg.norm(accum, axis=1) < 1e-12
    if zero_mask.any():
        # fallback: set zero normals to +Z
        vertex_normals[zero_mask] = np.array([0.0, 0.0, 1.0], dtype=float)

    return vertex_normals


def _make_per_corner_arrays(vertices: np.ndarray, faces: np.ndarray,
                            method: str = "area") -> tuple[np.ndarray, np.ndarray]:
    """
    Given:
      vertices: (N,3) float
      faces: (F,3) int
    Returns:
      positions_flat: (F*3, 3) float32
      normals_flat:   (F*3, 3) float32
    Suitable for glVertexPointer(3, GL_FLOAT, 0, positions_flat) and
    glNormalPointer(GL_FLOAT, 0, normals_flat).
    """
    # compute smooth per-vertex normals
    v_normals = _compute_vertex_normals(vertices, faces, method=method)  # (N,3)

    # expand to per-corner arrays (flatten triangles in order)
    positions_flat = vertices[faces].reshape(-1, 3)
    normals_flat = v_normals[faces].reshape(-1, 3)

    # Ensure float32 contiguous arrays for OpenGL
    return (np.ascontiguousarray(normals_flat, dtype=np.dtypes.Float64DType),
            np.ascontiguousarray(positions_flat, dtype=np.dtypes.Float64DType))


class GLRenderer(RendererBase):

    def __init__(self):
        from .. import Config

        super().__init__()
        self.viewMatrix = None
        self._grid = None

        self.camera_pos = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height),
                                       _decimal(0.0))

        self.camera_eye = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height + 0.5),
                                       _decimal(75.0))

    @staticmethod
    def get_world_coords(mx: int, my: int) -> _point.Point:
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        depth = GL.glReadPixels(float(mx), float(my), 1.0, 1.0,
                                GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)

        x, y, z = GLU.gluUnProject(float(mx), float(my), depth,
                                   modelview, projection, viewport)

        return _point.Point(_decimal(x), _decimal(y), _decimal(z))

    def rotate(self, dx, dy):
        from .. import Config

        # Orbit camera_eye around camera_pos.
        # dx/dy are degree deltas (consistent with prior code).
        dx *= _decimal(Config.look.sensitivity)
        dy *= _decimal(Config.look.sensitivity)  # NOQA

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = eye - pos

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        # Yaw around world up (y axis)
        yaw_r = math.radians(dx)
        cos_y = math.cos(yaw_r)
        sin_y = math.sin(yaw_r)  # NOQA
        up = np.array([0.0, 1.0, 0.0], dtype=float)

        # Rodrigues rotation around up
        yaw = (forward * cos_y + np.cross(up, forward) *
               sin_y + up * (np.dot(up, forward) * (1.0 - cos_y)))  # NOQA

        # Pitch around camera right axis (right is cross of forward and up)
        forward = -yaw / np.linalg.norm(yaw)
        right = np.cross(forward, up)  # NOQA
        rn = np.linalg.norm(right)
        if rn < 1e-6:
            # cannot pitch; avoid degenerate
            rotated = yaw
        else:
            right = right / rn
            pitch_rad = math.radians(dy)
            cos_p = math.cos(pitch_rad)
            sin_p = math.sin(pitch_rad)  # NOQA
            rotated = (yaw * cos_p + np.cross(right, yaw) *
                       sin_p + right * (np.dot(right, yaw) * (1.0 - cos_p)))  # NOQA

        new_eye = pos + rotated

        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z
        ) = _decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2])

        self.Refresh(False)

    def look(self, dx, dy):
        from .. import Config

        # Orbit camera_pos around camera_eye (opposite of look)
        dx *= _decimal(Config.rotate.sensitivity)
        dy *= _decimal(Config.rotate.sensitivity)

        dx = -dx

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)

        if fn < 1e-6:
            return

        # Yaw around world up
        yaw_rad = math.radians(dx)
        cos_y = math.cos(yaw_rad)
        sin_y = math.sin(yaw_rad)  # NOQA
        up = np.array([0.0, 1.0, 0.0], dtype=np.dtypes.Float64DType)

        k = up
        yaw = (forward * cos_y + np.cross(k, forward) *
               sin_y + k * (np.dot(k, forward) * (1.0 - cos_y)))  # NOQA

        yawn = np.linalg.norm(yaw)
        if yawn < 1e-6:
            return

        # Pitch around right axis (right based on new forward)
        yawn = -yaw / yawn
        right = np.cross(yawn, up)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            yaw_r = yaw
        else:
            right = right / rn
            pitch_rad = math.radians(dy)
            cos_p = math.cos(pitch_rad)
            sin_p = math.sin(pitch_rad)  # NOQA
            k = right
            yaw_r = (yaw * cos_p + np.cross(k, yaw) *
                     sin_p + k * (np.dot(k, yaw) * (1.0 - cos_p)))  # NOQA

        new_pos = eye + yaw_r

        (
            self.camera_pos.x,
            self.camera_pos.y,
            self.camera_pos.z
        ) = _decimal(new_pos[0]), _decimal(new_pos[1]), _decimal(new_pos[2])

        self.Refresh(False)

    def zoom(self, delta, *_):
        from .. import Config

        # Move camera_eye along forward direction (toward/away from camera_pos)
        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        step = delta * _decimal(Config.zoom.sensitivity)
        move = (forward / fn) * float(step)

        # If moving would invert eye and pos, prevent crossing pos
        if np.linalg.norm(forward) - np.linalg.norm(move) < 1e-6:
            # clamp to a small distance to avoid crossing
            move = forward * (0.999 / np.linalg.norm(forward))

        new_eye = eye + move
        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z
        ) = _decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2])

    def walk(self, dx, dy):
        from .. import Config

        # Use camera forward vector (from eye to pos).
        # Move both camera_pos and camera_eye.
        look_dx = dx

        if dy == 0.0:
            self.look(-look_dx * _decimal(10.0), _decimal(0.0))
            return

        dx *= _decimal(Config.walk.sensitivity)
        dy *= _decimal(Config.walk.sensitivity)

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            # degenerate, nothing to do
            return

        forward = forward / fn

        # Project forward onto XZ (ground) plane so walking does not change height
        forward_ground = np.array([forward[0], 0.0, forward[2]],
                                  dtype=np.dtypes.Float64DType)

        gf = np.linalg.norm(forward_ground)
        if gf < 1e-6:
            # looking straight up/down: fallback to world -Z so walking still works
            forward_ground = np.array([0.0, 0.0, -1.0],
                                      dtype=np.dtypes.Float64DType)
        else:
            forward_ground = forward_ground / gf

        # compute right consistent with pan/OnDraw: right = cross(world_up, forward_ground)
        world_up = np.array([0.0, 1.0, 0.0],
                            dtype=np.dtypes.Float64DType)

        right = np.cross(world_up, forward_ground)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0],
                             dtype=np.dtypes.Float64DType)
        else:
            right = right / rn

        # Build desired move from input
        input_mag = math.sqrt((dx * dx) + (dy * dy))
        if input_mag == 0:
            return

        move_dir = right * float(dx) + forward_ground * float(dy)

        mdn = np.linalg.norm(move_dir)
        if mdn < 1e-6:
            return

        move_dir = move_dir / mdn

        # Make total movement proportional to the original input magnitude
        move = move_dir * (input_mag * Config.walk.speed)

        new_eye = eye + move
        new_pos = pos + move

        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z,
            self.camera_pos.x,
            self.camera_pos.y,
            self.camera_pos.z
        ) = (
            _decimal(new_eye[0]),
            _decimal(new_eye[1]),
            _decimal(new_eye[2]),
            _decimal(new_pos[0]),
            _decimal(new_pos[1]),
            _decimal(new_pos[2])
        )

        self.look(-(look_dx * _decimal(20.0)), _decimal(0.0))

    def pan(self, dx, dy):
        from .. import Config

        # Translate both camera_pos and camera_eye in camera's right/up directions
        dx *= _decimal(Config.pan.sensitivity)
        dy *= _decimal(Config.pan.sensitivity)

        dy = -dy

        move = _point.Point(dx, dy, _decimal(0.0))
        angle = _angle.Angle.from_points(self.camera_pos, self.camera_eye)

        move @= angle

        self.camera_eye += move
        self.camera_pos += move

    @property
    def grid(self):
        GRID_SIZE = 1000
        GRID_STEP = 50

        # --- Tiles ---
        TILE_SIZE = GRID_STEP
        HALF = GRID_SIZE

        if self._grid is None:
            self._grid = [[], []]
            for x in range(-HALF, HALF, TILE_SIZE):
                for y in range(-HALF, HALF, TILE_SIZE):
                    # Alternate coloring for checkerboard effect
                    is_even = ((x // TILE_SIZE) + (y // TILE_SIZE)) % 2 == 0

                    p2 = (x, 0, y + TILE_SIZE)
                    p3 = (x + TILE_SIZE, 0, y + TILE_SIZE)

                    if is_even:
                        p1 = (x, 0, y)
                        self._grid[0].append([p1, p2, p3])
                    else:
                        p1 = (x + TILE_SIZE, 0, y)
                        self._grid[1].append([p1, p2, p3])

            self._grid[0] = np.array(self._grid[0], dtype=np.dtypes.Float64DType)
            self._grid[1] = np.array(self._grid[1], dtype=np.dtypes.Float64DType)

        return self._grid

    @staticmethod
    def set_viewport(width: int | float, height: int | float):
        GL.glViewport(0, 0, width, height)

    def init(self, w: int | float, h: int | float):
        GL.glClearColor(0.20, 0.20, 0.20, 0.0)
        GL.glViewport(0, 0, w, h)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        # glEnable(GL_ALPHA_TEST)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        # glEnable(GL_FOG)
        GL.glDepthMask(GL.GL_TRUE)
        # glShadeModel(GL_FLAT)

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        # glEnable(GL_NORMALIZE)
        GL.glEnable(GL.GL_RESCALE_NORMAL)
        # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glEnable(GL.GL_LIGHT0)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(45, w / float(h), 0.1, 1000.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GLU.gluLookAt(0.0, 2.0, -16.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

    @staticmethod
    def build_mesh(model) -> tuple[np.ndarray, np.ndarray, int]:
        from .. import Config

        if Config.renderer.smooth_normals:
            return _get_smooth_triangles(model)

        return _get_triangles(model)

    def draw(self) -> "DrawWrapper":
        wrapper = DrawWrapper(self)
        return wrapper


class DrawWrapper(DrawWrapperBase):

    def __init__(self, renderer):
        self.renderer = renderer
        self.camera_pos = renderer.camera_pos
        self.camera_eye = renderer.camera_eye
        self._grid = renderer.grid

    def __enter__(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        forward = (self.camera_pos - self.camera_eye).as_numpy

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            forward = np.array([0.0, 0.0, -1.0],
                               dtype=np.dtypes.Float64DType)
        else:
            forward = forward / fn

        temp_up = np.array([0.0, 1.0, 0.0],
                           dtype=np.dtypes.Float64DType)

        right = np.cross(temp_up, forward)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0],
                             dtype=np.dtypes.Float64DType)
        else:
            right = right / rn

        up = np.cross(forward, right)  # NOQA

        un = np.linalg.norm(up)
        if un < 1e-6:
            up = np.array([0.0, 1.0, 0.0],
                          dtype=np.dtypes.Float64DType)
        else:
            up = up / un

        GLU.gluLookAt(self.camera_eye.x, self.camera_eye.y, self.camera_eye.z,
                      self.camera_pos.x, self.camera_pos.y, self.camera_pos.z,
                      up[0], up[1], up[2])

        GL.glPushMatrix()
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        GL.glPopMatrix()

    def reset_camera(self, *_):
        from .. import Config

        self.camera_pos = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height),
                                       _decimal(0.0))

        self.camera_eye = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height + 0.5),
                                       _decimal(75.0))

    def grid(self):
        if self.grid:
            GL.glColor4f(0.8, 0.8, 0.8, 0.4)
            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, self._grid[0])
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(self._grid[0]) * 3)
            GL.glColor4f(0.3, 0.3, 0.3, 0.4)
            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, self._grid[1])
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(self._grid[1]) * 3)

    @staticmethod
    def model(
        normals: np.ndarray | None,
        triangles: np.ndarray | None,
        triangle_count: int,
        color: tuple[float, float, float, float],
        material: _gl_materials.GLMaterial | None,
        is_selected: bool
    ):

        if triangle_count != 0:
            if is_selected:
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [1.0, 1.0, 1.0, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.8, 0.8, 0.8, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
                GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 100.0)

            elif material is not None:
                material.set()

            GL.glColor4f(*color)

            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, triangles)

            if normals:
                GL.glNormalPointer(GL.GL_DOUBLE, 0, normals)

            GL.glDrawArrays(GL.GL_TRIANGLES, 0, triangle_count)

            if is_selected:
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

                GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
                GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)


GLRenderer.set_active()
