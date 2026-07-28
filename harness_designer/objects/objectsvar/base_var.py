# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ... import color as _color
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import config as _config
from ...gl import materials as _materials
from ... import utils as _utils
from ...gl import vbo as _vbo


Config = _config.Config.colors


if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from .. import ObjectBase as _ObjectBase


class BaseVar:

    # Tie-breaker for gl.object_picker.find_object when multiple
    # OBB/AABB hits land on the same ray -- see Base3D._pick_priority
    # (WireMarker/WireLayout/BundleLayout bump this to 1 to win over the
    # wire they sit on/inside).
    _pick_priority: int = 0

    def __init__(self, parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.PooledVBOHandler, angle: _angle.Angle,
                 position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial):

        self._is_selected = False
        self._is_visible = False

        self.parent = parent
        self.db_obj = db_obj
        self._vbo = vbo
        self._angle = angle
        self._position = position
        self._scale = scale
        self._material = material
        self._unselected_material = material

        self._selected_material = _materials.Generic(self._selected_color)

        if angle is None:
            self._o_angle = None
            self._angle_inverse = None
        else:
            self._o_angle = angle.copy()
            self._angle_inverse = -angle
            angle.bind(self._update_angle)

        if position is None:
            self._o_position = None
            self.numpy_position = None
        else:
            self._o_position = position.copy()
            position.bind(self._update_position)
            self.numpy_position = self._position.as_numpy

        if scale is None:
            self._o_scale = None
        else:
            self._o_scale = scale.copy()
            scale.bind(self._update_scale)

        if material is None:
            self._is_opaque = np.array([1], dtype=np.uint8)
        else:
            self._is_opaque = np.array([int(material.is_opaque)], dtype=np.uint8)

        self._aabb: np.ndarray = np.ascontiguousarray(np.array(
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float32))

        self._obb: np.ndarray = None

        self._compute_obb()
        self._compute_aabb()

    @property
    def _selected_color(self) -> _color.Color:
        raise NotImplementedError

    @property
    def selected_material(self) -> _materials.GLMaterial:
        """This object's own "selected" material -- exposed publicly so
        other objects can identify() themselves with it (e.g. a Wire
        showing its own WireLayouts in the selected color while the
        layouts themselves aren't the true selection; see
        objects.wire.Wire.set_selected)."""
        return self._selected_material

    @property
    def vbo(self):
        return self._vbo

    @property
    def editor(self):
        raise NotImplementedError

    def _is_visible_callback(self, *_, **__):
        raise NotImplementedError

    def _compute_obb(self):
        if self._vbo is None:
            return

        if self._position is None:
            return

        if self._scale is None:
            return

        if self._angle is None:
            return

        local_obb = self._vbo.local_obb * self._scale
        local_obb @= self._angle
        self._obb = local_obb + self._position

    def _compute_aabb(self):
        if self._vbo is None:
            return

        if self._position is None:
            return

        if self._scale is None:
            return

        if self._angle is None:
            return

        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]

        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        corners = np.array([
            [x1, y1, z1], [x1, y1, z2],
            [x1, y2, z1], [x1, y2, z2],
            [x2, y1, z1], [x2, y1, z2],
            [x2, y2, z1], [x2, y2, z2]
        ], dtype=np.float32)

        corners *= self._scale.as_numpy
        corners @= self._angle
        corners += self._position.as_numpy

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    def hit_test_step1(self, ray_origin, ray_direction):
        """
        Stage 1: Test against cached AABB

        Super fast - just uses pre-calculated bbox_min/max
        """
        inv_dir = 1.0 / (ray_direction + 1e-8)
        t = (self._aabb - ray_origin) * inv_dir
        tmin = np.minimum(t[0], t[1])
        tmax = np.maximum(t[0], t[1])

        return np.min(tmax) >= max(0, np.max(tmin))

    def hit_test_step2(self, ray_origin, ray_direction):
        """
        Stage 2: Test against cached OBB

        Fast - uses pre-calculated rotation_inverse
        """
        if self._vbo is None:
            return False

        local_origin = (ray_origin - self._position) @ self._angle_inverse
        local_direction = ray_direction @ self._angle_inverse

        inv_dir = 1.0 / (local_direction + 1e-8)

        t = (self._vbo.local_aabb - local_origin) * inv_dir

        tmin = np.minimum(t[0], t[1])
        tmax = np.maximum(t[0], t[1])

        return np.min(tmax) >= max(0, np.max(tmin))

    def hit_test_step3(self, ray_origin, ray_dir):
        """
        Stage 3: Vectorized ray-mesh intersection

        Uses NumPy broadcasting to test ray against ALL triangles at once
        Much faster than looping through triangles one by one
        """
        if self._vbo is None:
            return False

        ray_object = ray_origin - self._position

        vertices = (self._vbo.vertices.reshape(-1, 3) * self._scale) @ self._angle

        if len(vertices) % 3:
            return False

        verts = vertices.reshape(-1, 3, 3)

        # Vectorized ray-triangle intersection
        hit = self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts)

        return hit

    @staticmethod
    def _ray_triangles_intersect_vectorized(
        ray_origin, ray_dir, vertices, max_t=None):  # NOQA

        """
        Vectorized Möller-Trumbore ray-triangle intersection

        Tests ray against MANY triangles at once using NumPy broadcasting

        Args:
            ray_origin: (3,) array
            ray_dir: (3,) array
            vertices: (N, 3, 3) array - N triangles, each with 3 vertices of 3 coords
            max_t: optional upper bound on the hit distance -- pass the
                edge's own length (with ray_dir as the unnormalized edge
                vector, i.e. t=1 reaches the far endpoint) to test a finite
                segment instead of an infinite ray. None (default) preserves
                the original unbounded-ray behavior used for picking.

        Returns:
            hit_mask: (N,) boolean array - True where ray hits triangle
            distances: (N,) float array - distance to intersection (inf if no hit)
        """
        num_triangles = vertices.shape[0]  # NOQA

        # Extract vertices
        v0 = vertices[:, 0, :]  # (N, 3)
        v1 = vertices[:, 1, :]  # (N, 3)
        v2 = vertices[:, 2, :]  # (N, 3)

        # Edge vectors
        edge1 = v1 - v0  # (N, 3)  # NOQA
        edge2 = v2 - v0  # (N, 3)

        # Begin calculating determinant
        h = np.cross(ray_dir, edge2)  # (N, 3)  # NOQA
        det = np.sum(edge1 * h, axis=1)     # (N,) - dot product

        # Initialize output arrays
        hit_mask = np.zeros(num_triangles, dtype=bool)

        # Check determinant (ray parallel to triangle)
        valid_det = np.abs(det) > 1e-6  # (N,)

        if not np.any(valid_det):
            return np.any(hit_mask)

        inv_det = np.zeros_like(det)
        inv_det[valid_det] = 1.0 / det[valid_det]

        # Calculate distance from v0 to ray origin
        s = ray_origin - v0  # (N, 3)

        # Calculate u parameter
        u = inv_det * np.sum(s * h, axis=1)  # (N,)

        # Test u bounds
        valid_u = valid_det & (u >= 0.0) & (u <= 1.0)

        if not np.any(valid_u):
            return np.any(hit_mask)

        # Calculate v parameter
        q = np.cross(s, edge1)  # (N, 3)  # NOQA
        v = inv_det * np.sum(ray_dir * q, axis=1)  # (N,)

        # Test v bounds
        valid_v = valid_u & (v >= 0.0) & (u + v <= 1.0)

        if not np.any(valid_v):
            return np.any(hit_mask)

        # Calculate t (distance along ray)
        t = inv_det * np.sum(edge2 * q, axis=1)  # (N,)

        # Final validation: t > epsilon (ray, not line)
        hit_mask = valid_v & (t > 1e-6)
        if max_t is not None:
            hit_mask = hit_mask & (t <= max_t)

        return np.any(hit_mask)

    def identify(self, material: _materials.GLMaterial | None) -> None:
        """
        Temporarily override this object's own display material.

        Handler classes use this to highlight objects compatible with
        whatever is currently being added/placed (see e.g.
        handlers.bundle_handler._highlight_compatible_wires), and
        objects.wire.Wire.set_selected uses it to show a wire's own
        WireLayouts in the selected color while the layouts themselves
        aren't the true selection (mainframe only ever tracks one true
        selected object at a time).

        An object is only ever identified with one material or the
        other, never both -- passing a new one simply replaces whatever
        is currently showing, independent of is_selected; passing None
        clears the override and falls back to whatever is_selected
        would normally show (see set_selected, whose own _material/
        _is_opaque assignment this mirrors).

        :param material: The material to display this object as, or
            None to clear the override.
        :type material: :class:`_materials.GLMaterial` | None
        """
        if material is not None:
            self._material = material
        elif self._is_selected:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        self._is_opaque[0] = int(self._material.is_opaque)

    def _update_position(self, position: _point.Point):
        """
        Update the position.

        Internal Use.

        :type position: :class:`_point.Point`
        """
        self.editor.context.acquire()

        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

        self.editor.context.release()
        self.editor.Refresh(False)

    def _update_angle(self, angle: _angle.Angle):
        """
        Update the angle.

        Internal Use.

        :type angle: :class:`_angle.Angle`
        """

        self.editor.context.acquire()

        self._o_angle = angle.copy()
        self._angle_inverse = -angle

        self._compute_obb()
        self._compute_aabb()

        self.editor.context.release()
        self.editor.Refresh(False)

    def _update_scale(self, scale: _point.Point):
        """
        Update the scale.

        Internal Use.

        :type scale: :class:`_point.Point`
        """

        self.editor.context.acquire()

        self._o_scale = scale.copy()

        self._compute_obb()
        self._compute_aabb()

        self.editor.context.release()

        self.editor.Refresh(False)

    @property
    def position(self) -> _point.Point:
        """
        Get the position.

        :rtype: :class:`_point.Point`
        """
        return self._position

    @position.setter
    def position(self, value: _point.Point):
        """
        Set the position.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._position:
            raise AttributeError('Position is only able to be modified not set')

        self._position = value

    @property
    def angle(self) -> _angle.Angle:
        """
        Get the angle.

        :rtype: :class:`_angle.Angle`
        """

        return self._angle

    @angle.setter
    def angle(self, value: _angle.Angle):
        """
        Set the angle.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_angle.Angle`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._angle:
            raise AttributeError('Angle is only able to be modified not set')

        self._angle = value

    @property
    def scale(self) -> _point.Point:
        """
        Get the scale.

        :rtype: :class:`_point.Point`
        """

        return self._scale

    @scale.setter
    def scale(self, value: _point.Point):
        """
        Set the scale.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._scale:
            raise AttributeError('Scale is only able to be modified not set')

        self._scale = value

    @property
    def obb(self) -> np.ndarray:
        """
        Return the OBB.

        :rtype: :class:`np.ndarray`
        """

        return self._obb

    @property
    def aabb(self) -> np.ndarray:
        """
        Return the AABB.

        :rtype: :class:`np.ndarray`
        """

        return self._aabb

    @property
    def is_selected(self) -> bool:
        """
        Get if the object is selected.

        :returns: True if selected else False
        :rtype: bool
        """

        return self._is_selected

    def set_selected(self, flag: bool):
        """
        Set if the object is selected.

        :param flag: True if selected else False
        :type flag: bool
        """

        if flag:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        self._is_opaque[0] = int(self._material.is_opaque)
        self._is_selected = flag

    def delete(self):
        """
        Execute the delete operation.

        Row deletion and canvas de-registration are handled once, centrally,
        by :meth:`ObjectBase.delete`. Subclasses override this as their hook
        for view-local teardown.
        """

        self.parent.delete()

    def _delete(self):
        """
        Any object specific taredown should occur in this function
        """
        self._is_deleted = True
        self.editor.Refresh()

    @property
    def material(self) -> _materials.GLMaterial:
        """
        Gets the current GL material being used

        :rtype: `_materials.GLMaterial`
        """

        if self._is_selected:
            return self._selected_material

        return self._material

    @property
    def is_opaque(self) -> np.ndarray:
        """
        Get the objects opacity

        :returns: True if object is 100% opaque
        :rtype: `np.ndarray`
        """

        return self._is_opaque

    def get_context_menu(self):  # NOQA
        """
        Get the context menu.

        :returns: Context menu or None
        """

        return None

    @property
    def is_visible(self) -> bool:
        """
        Get object visibility

        :rtype: bool
        """

        raise NotImplementedError

    @is_visible.setter
    def is_visible(self, value: bool):
        """
        Set object visibility.

        :type value: bool
        """

        raise NotImplementedError
