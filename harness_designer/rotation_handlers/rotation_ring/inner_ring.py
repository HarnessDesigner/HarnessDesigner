# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The object-space protractor ring -- ticks, text and washer, rotating
with the tracked object.

Its own-slot spin tracks the object's current Euler value for this axis
directly (see :meth:`InnerRing._disc_rotation`), so its ``0`` tick
always points at wherever the object's own local zero currently is --
same nested-Euler ("gyroscope") plane orientation as the rest of this
gizmo, driven straight off ``obj3d.angle`` with no separate cached copy.

Grabbing anywhere along its band and dragging free-rotates the object
about this axis, replacing the old fixed-handle drag in
``rotation_handlers/rotation_rings.py``'s retired ``DragRotate``.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from . import _hit_test
from ._protractor_base import ProtractorRingBase
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl.canvas_base import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl.canvas_base import camera_base as _camera_base


class InnerRing(ProtractorRingBase):
    """One axis's object-space protractor ring.

    :param axis: ``'x'``, ``'y'`` or ``'z'`` -- which Euler slot this
        ring displays/drives.
    :param obj_angle: The tracked object's own :class:`Angle` instance
        (shared reference, not copied -- read directly every time this
        ring's orientation is needed, per the "just use the object's
        angle" design).
    """

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, radius: float,
                depth: float, material, label_size: float,
                obj_angle: _angle.Angle, context):

        self.axis = axis
        self._obj_angle = obj_angle

        self._dragging = False
        self._drag_start_value = 0.0
        self._drag_cx = 0.0
        self._drag_cy = 0.0
        self._drag_prev_phi = None
        self._drag_total = 0.0
        self._drag_sign = 1.0

        super().__init__(center, radius, depth, material, label_size, context)
        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
        euler = self._obj_angle.as_euler_float
        return _rotation_mesh.slot_ring_angle(self.axis, euler)

    @_check_types.do
    def on_object_angle_changed(self) -> None:
        """Refresh tick/label placement -- call whenever ``obj_angle``'s
        callback fires (the assembler owns the bind/unbind lifecycle so
        this stays a plain method, not a callback itself).
        """
        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def begin_drag(self, mouse_pos: _point.Point,
                   camera: "_camera_base.CameraBase") -> None:
        """Start a free-rotation drag anywhere along the ring's band.

        Mirrors the retired ``DragRotate.__init__``'s screen-space
        angle-tracking approach, just re-homed onto this ring instance
        instead of a standalone drag-session object.
        """
        self._dragging = True
        self._drag_start_value = float(getattr(self._obj_angle, self.axis))

        center_screen = camera.ProjectPoint(self.center)
        self._drag_cx = float(center_screen.x)
        self._drag_cy = float(center_screen.y)

        normal = _rotation_mesh.slot_normal(self.axis, self._obj_angle.as_euler_float)
        to_camera = (camera.position - self.center).as_numpy
        facing = float(np.dot(normal, np.asarray(to_camera[:3], dtype=np.float32)))
        self._drag_sign = 1.0 if facing >= 0.0 else -1.0

        self._drag_prev_phi = None
        self._drag_total = 0.0

    @_check_types.do
    def _screen_phi(self, mouse_pos: _point.Point) -> float:
        return math.atan2(-(float(mouse_pos.y) - self._drag_cy),
                          float(mouse_pos.x) - self._drag_cx)

    @_check_types.do
    def update_drag(self, mouse_pos: _point.Point) -> float | None:
        """Advance the active drag and return the new Euler value for
        this axis, or ``None`` if no drag is active or this is the
        drag's first sample (matching ``DragRotate.__call__``'s own
        first-sample-establishes-baseline behavior).

        The caller (the per-axis :class:`~..rotation_ring.RotationRing`
        assembler) is responsible for actually writing the value back
        to ``obj_angle`` -- this method only computes it, so the
        assembler can unbind/rebind its own change-tracking callback
        around the write exactly like the old ``apply_drag_angle`` did.
        """
        if not self._dragging:
            return None

        phi = self._screen_phi(mouse_pos)

        if self._drag_prev_phi is None:
            self._drag_prev_phi = phi
            return None

        step = math.atan2(math.sin(phi - self._drag_prev_phi),
                          math.cos(phi - self._drag_prev_phi))
        self._drag_prev_phi = phi
        self._drag_total += step

        return _rotation_mesh.wrap_angle(
            self._drag_start_value + self._drag_sign * math.degrees(self._drag_total))

    @_check_types.do
    def end_drag(self) -> None:
        self._dragging = False
        self._drag_prev_phi = None
        self._drag_total = 0.0

    @property
    @_check_types.do
    def is_dragging(self) -> bool:
        return self._dragging

    @_check_types.do
    def hit_test(self, mouse_pos: _point.Point,
                camera: "_camera_base.CameraBase", tolerance: float = 8.0,
                samples: int = 64) -> bool:
        """Same circumference-sampling approach as
        :meth:`.torus_ring.TorusRing.hit_test` -- grab anywhere along
        the band, no fixed handle.
        """
        if not self.is_visible:
            return False

        px = float(mouse_pos.x)
        py = float(mouse_pos.y)
        ring_angle = self._disc_rotation()

        prev = None
        for i in range(samples + 1):
            theta = 2.0 * math.pi * i / samples
            local = np.array(
                [math.cos(theta) * self.radius, math.sin(theta) * self.radius, 0.0],
                dtype=np.float32)
            world = ring_angle @ local

            world_pt = _point.Point(
                float(self.center.x) + float(world[0]),
                float(self.center.y) + float(world[1]),
                float(self.center.z) + float(world[2]))
            screen = camera.ProjectPoint(world_pt)

            cur = (float(screen.x), float(screen.y))
            if prev is not None:
                if _hit_test.point_near_segment(
                        px, py, prev[0], prev[1], cur[0], cur[1], tolerance):
                    return True

            prev = cur

        return False

    @_check_types.do
    def delete(self, context) -> None:
        pass
