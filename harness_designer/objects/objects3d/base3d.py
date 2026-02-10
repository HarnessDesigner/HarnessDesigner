from typing import TYPE_CHECKING, Union

import numpy as np
from OpenGL import GL

from ... import debug as _debug
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import config as _config
from ...wrappers import color as _color
from ...wrappers import materials as _materials
from ... import utils as _utils
from ...ui.editor_3d import vbo_handler as _vbo_handler

if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui


Config = _config.Config.editor3d


class Base3D:

    def __init__(self, parent: Union["_ObjectBase", "_ui.MainFrame"]):
        self._parent: Union["_ObjectBase", "_ui.MainFrame"] = parent

        try:
            self.editor3d = parent.mainframe.editor3d
        except AttributeError:
            self.editor3d = parent.editor3d

        self.mainframe: "_ui.MainFrame" = self.editor3d.mainframe

        self._db_obj: _project_db.PJTEntryBase = None
        self._position: _point.Point = None
        self._material: _materials.GLMaterial = None
        self._selected_material: _materials.GLMaterial | None = None
        self._color: _color.Color = None
        self._selected_color: _color.Color | None = None
        self._is_selected = False
        self._position: _point.Point = _point.Point(0.0, 0.0, 0.0)
        self._angle: _angle.Angle = _angle.Angle()
        self._angle_inverse: _angle.Angle = -self._angle
        self._scale = _point.Point = _point.Point(0.0, 0.0, 0.0)
        self._vbo: _vbo_handler = None

        self._aabb: np.ndarray = None
        self._obb: np.ndarray = None

        # stores the verticies and faces so normals or smooth normals
        # can be calculated if the user changes the setting for it.
        self._mesh: list[list[np.ndarray, np.ndarray]] = []

        self._triangles: list["TriangleRenderer"] = []

    def ray_intersects_aabb(self, ray_origin, ray_direction):
        """
        Stage 1: Test against cached AABB

        Super fast - just uses pre-calculated bbox_min/max
        """
        inv_dir = 1.0 / (ray_direction + 1e-8)
        t = (self._aabb - ray_origin) * inv_dir
        tmin = np.minimum(t)
        tmax = np.maximum(t)

        return np.min(tmax) >= max(0, np.max(tmin))

    def ray_intersects_obb(self, ray_origin, ray_direction):
        """
        Stage 2: Test against cached OBB

        Fast - uses pre-calculated rotation_inverse
        """
        local_origin = (ray_origin - self.position) @ self._angle_inverse
        local_direction = ray_direction @ self._angle_inverse

        inv_dir = 1.0 / (local_direction + 1e-8)
        t = (self._vbo.local_aabb - local_origin) * inv_dir

        tmin = np.minimum(t)
        tmax = np.maximum(t)

        return np.min(tmax) >= max(0, np.max(tmin))

    def ray_intersects_mesh(self, ray_origin, ray_direction):
        """
        Stage 3: Vectorized ray-mesh intersection

        Uses NumPy broadcasting to test ray against ALL triangles at once
        Much faster than looping through triangles one by one
        """
        # Transform ray to object space (subtract position, no rotation yet)
        ray_origin_shifted = ray_origin - self._position

        # Get all triangles from VBO data
        for vertices, _, faces, __ in self._vbo.data:
            # Scale vertices to match object instance
            verts = vertices * self._scale  # (N, 3) * (3,) = (N, 3)

            # Apply rotation to all vertices at once
            verts @= self._angle

            # Now vertices_transformed are in world
            # space set to position 0, 0, 0

            # create "triangle soup", complete array of all vertices including
            # duplicated used for more than one face
            verts = verts[faces]  # (num_triangles, 3, 3)

            # Vectorized ray-triangle intersection
            hit_mask, distances = self._ray_triangles_intersect_vectorized(
                ray_origin_shifted,
                ray_direction,
                verts
            )

            # Find closest hit
            if np.any(hit_mask):
                valid_distances = distances[hit_mask]
                closest_idx = np.argmin(valid_distances)
                closest_distance = valid_distances[closest_idx]

                # Calculate hit point
                hit_point = ray_origin + closest_distance * ray_direction

                return True, closest_distance, hit_point

        return False, float('inf'), None

    def _update_bounding_boxes(self):
        local_aabb = self._vbo.local_aabb * self._scale
        local_obb = self._vbo.local_obb * self._scale

        local_aabb @= self._angle
        local_obb @= self._angle

        self._aabb = local_aabb + self._position
        self._obb = local_obb + self._position

    @staticmethod
    def _ray_triangles_intersect_vectorized(
        ray_origin, ray_direction, triangles):  # NOQA

        """
        Vectorized Möller-Trumbore ray-triangle intersection

        Tests ray against MANY triangles at once using NumPy broadcasting

        Args:
            ray_origin: (3,) array
            ray_direction: (3,) array
            triangles: (N, 3, 3) array - N triangles, each with 3 vertices of 3 coords

        Returns:
            hit_mask: (N,) boolean array - True where ray hits triangle
            distances: (N,) float array - distance to intersection (inf if no hit)
        """
        num_triangles = triangles.shape[0]  # NOQA

        # Extract vertices
        v0 = triangles[:, 0, :]  # (N, 3)
        v1 = triangles[:, 1, :]  # (N, 3)
        v2 = triangles[:, 2, :]  # (N, 3)

        # Edge vectors
        edge1 = v1 - v0  # (N, 3)  # NOQA
        edge2 = v2 - v0  # (N, 3)

        # Begin calculating determinant
        h = np.cross(ray_direction, edge2)  # (N, 3)  # NOQA
        det = np.sum(edge1 * h, axis=1)     # (N,) - dot product

        # Initialize output arrays
        hit_mask = np.zeros(num_triangles, dtype=bool)
        distances = np.full(num_triangles, np.inf, dtype=np.float32)

        # Check determinant (ray parallel to triangle)
        valid_det = np.abs(det) > 1e-6  # (N,)

        if not np.any(valid_det):
            return hit_mask, distances

        inv_det = np.zeros_like(det)
        inv_det[valid_det] = 1.0 / det[valid_det]

        # Calculate distance from v0 to ray origin
        s = ray_origin - v0  # (N, 3)

        # Calculate u parameter
        u = inv_det * np.sum(s * h, axis=1)  # (N,)

        # Test u bounds
        valid_u = valid_det & (u >= 0.0) & (u <= 1.0)

        if not np.any(valid_u):
            return hit_mask, distances

        # Calculate v parameter
        q = np.cross(s, edge1)  # (N, 3)  # NOQA
        v = inv_det * np.sum(ray_direction * q, axis=1)  # (N,)

        # Test v bounds
        valid_v = valid_u & (v >= 0.0) & (u + v <= 1.0)

        if not np.any(valid_v):
            return hit_mask, distances

        # Calculate t (distance along ray)
        t = inv_det * np.sum(edge2 * q, axis=1)  # (N,)

        # Final validation: t > epsilon (ray, not line)
        hit_mask = valid_v & (t > 1e-6)

        # Store distances for hits
        distances[hit_mask] = t[hit_mask]

        return hit_mask, distances

    def _update_position(self, position: _point.Point):
        local_aabb = self._vbo.local_aabb * self._scale
        local_obb = self._vbo.local_obb * self._scale

        local_aabb @= self._angle
        local_obb @= self._angle

        self._aabb = local_aabb + position
        self._obb = local_obb + position

    @property
    def obb(self) -> np.ndarray:
        return self._obb

    @property
    def aabb(self) -> list[_point.Point, _point.Point]:
        p1, p2 = [_point.Point(*item.tolist()) for item in self._aabb]
        return [p1, p2]

    @property
    def triangles(self) -> list["TriangleRenderer"]:
        return self._triangles

    @property
    def position(self) -> _point.Point:
        return self._position

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

    @staticmethod
    def _compute_vertex_normals(vertices, faces) -> tuple[np.ndarray, np.ndarray, int]:
        return _utils.compute_vertex_normals(vertices, faces)

    @staticmethod
    def _compute_smoothed_vertex_normals(vertices, faces) -> tuple[
        np.ndarray, np.ndarray, int]:
        return _utils.compute_smoothed_vertex_normals(vertices, faces)

    @staticmethod
    def _compute_aabb(triangles) -> tuple[_point.Point, _point.Point]:
        return _utils.compute_aabb(triangles)

    @staticmethod
    def _compute_obb(p1: _point.Point, p2: _point.Point) -> np.ndarray:
        return _utils.compute_obb(p1, p2)


# I moved some of the rendering code to the 2 below classes.
# This allows me to create an alternative representation of things like wires
# and bundles which become expensive if needing to redraw them as the mouse
# moves (click and drag). For those 2 cases the cylinder model gets replaced
# with a line that has a width that matches the diameter. There are no triangles
# to render so it should be able to keep up and provide a nice smooth user
# experiance.
class TriangleRenderer:

    def __init__(self, position: _point.Point, angle: _angle.Angle,
                 scale: _point.Point, material: _materials.GLMaterial,
                 vbo: _vbo_handler.VBOHandler | None = None,
                 data: list[list[np.ndarray, np.ndarray, int]] | None = None):

        self.vbo = vbo
        self.position = position
        self.angle = angle
        self.scale = scale
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

        self.material.set(shader_program)

        pos_loc = GL.glGetUniformLocation(shader_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(shader_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(shader_program, "objectScale")
        if self.vbo is None:
            # we set these to values that will not cause anything to move
            # This is done because the processing is being done CPU side and
            # not GPU side. This is due to there not being enough memory
            # available on the GPU to preload the vertex arrays
            GL.glUniform3f(pos_loc, 0.0, 0.0, 0.0)
            GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
            GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)

            # Enable client state and render
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

            for verts, nrmls, count in self._data:
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, verts)
                GL.glNormalPointer(GL.GL_FLOAT, 0, nrmls)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        else:
            GL.glUniform3f(pos_loc, *self.position.as_float)
            GL.glUniform4f(rot_loc, *self.angle.as_quat.tolist())
            GL.glUniform3fv(scale_loc, *self.scale.as_float)

            self.vbo.render()
