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
from .. import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl.canvas_base import camera_base as _camera_base


# Fixed, light label color -- same reasoning as _TICK_COLOR above, but
# labels need the OPPOSITE end of the brightness scale from ticks:
# they're read against the dark scene background (past the washer's
# own outer/inner edge, see _recompute_local_geometry's label_gap),
# not against the washer's own face, so a dark color nearly disappears
# there instead of standing out.
_LABEL_COLORS = {'x': (0.8, 0.2, 0.2, 1.0),
                 'y': (0.2, 0.8, 0.2, 1.0),
                 'z': (0.2, 0.2, 0.8, 1.0)}


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
    def __init__(self, axis: str, center: _point.Point, inner_radius: float,
                outer_radius: float, depth: float, material, label_size: float,
                obj_angle: _angle.Angle, context, camera=None):


        self._obj_angle = obj_angle

        self._dragging = False
        self._drag_start_value = 0.0
        self._drag_cx = 0.0
        self._drag_cy = 0.0
        self._drag_prev_phi = None
        self._drag_total = 0.0
        self._drag_sign = 1.0

        # The inner protractor's OD sits at the torus ring -- the only
        # side clear of it is the ID, toward the object -- see
        # ProtractorRingBase's own docstring.
        super().__init__(axis, center, inner_radius, outer_radius, depth, material, label_size, context,
                         camera, labels_outward=False)
        self.reposition_all(self._disc_rotation())
        self.start_camera_tracking()

    def _get_label_color(self):
        return _LABEL_COLORS[self.axis]

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
        """This axis's own Euler value, applied as an extra spin about
        the ring's own local-Z normal, composed UNDER
        ``slot_ring_angle``'s nesting transform (spin first in local
        space, then place the already-spun ring into world space via
        the other two axes' current values).

        ``slot_ring_angle`` alone deliberately leaves this axis's own
        value out -- it was written for the always-on torus ring, a
        plain tube that's rotationally symmetric about its own normal,
        so that value never showed up in its orientation regardless.
        This ring is not symmetric -- it has real tick marks with an
        actual ``0`` that has to visibly track this axis's current
        value (that's the entire point of it being the free-rotate
        ring) -- so that spin has to be added back in here.
        """
        ex, ey, ez = self._obj_angle.as_euler_float
        own_degrees = {'x': ex, 'y': ey, 'z': ez}[self.axis]

        outer_matrix = _rotation_mesh.slot_ring_angle(
            self.axis, (ex, ey, ez)).as_matrix_numpy

        theta = math.radians(own_degrees)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        local_spin = np.array([
            [cos_t, -sin_t, 0.0],
            [sin_t, cos_t, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float32)

        total_matrix = (outer_matrix @ local_spin).astype(np.float32)
        return _angle.Angle.from_matrix(total_matrix)

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
        if center_screen is None:
            # Degenerate projection (behind the camera's own eye plane,
            # w == 0) -- fall back to the mouse's own position so the
            # drag still starts cleanly instead of crashing; the first
            # motion sample will just read as zero delta.
            center_screen = mouse_pos

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
        """Grab anywhere within the band's full radial extent (ID to OD),
        not just a thin nominal circumference -- for each angular sample,
        projects both the outer- and inner-edge points and accepts a hit
        within *tolerance* screen pixels of either edge polyline or the
        radial spoke between them (approximating the wide annulus as a
        strip of quads -- same "sample the circumference, check segment
        proximity" approach :meth:`.torus_ring.TorusRing.hit_test` uses
        for a thin ring, just applied to both edges of a wide one so it
        stays correct regardless of viewing angle).
        """
        if not self.is_visible:
            return False

        px = float(mouse_pos.x)
        py = float(mouse_pos.y)
        ring_angle = self._disc_rotation()

        prev_outer = None
        prev_inner = None
        for i in range(samples + 1):
            theta = 2.0 * math.pi * i / samples
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            local_outer = np.array(
                [cos_t * self.outer_radius, sin_t * self.outer_radius, 0.0], dtype=np.float32)
            local_inner = np.array(
                [cos_t * self.inner_radius, sin_t * self.inner_radius, 0.0], dtype=np.float32)

            world_outer = ring_angle @ local_outer
            world_inner = ring_angle @ local_inner

            outer_pt = _point.Point(
                float(self.center.x) + float(world_outer[0]),
                float(self.center.y) + float(world_outer[1]),
                float(self.center.z) + float(world_outer[2]))
            inner_pt = _point.Point(
                float(self.center.x) + float(world_inner[0]),
                float(self.center.y) + float(world_inner[1]),
                float(self.center.z) + float(world_inner[2]))

            screen_outer = camera.ProjectPoint(outer_pt)
            screen_inner = camera.ProjectPoint(inner_pt)

            if screen_outer is None or screen_inner is None:
                # Degenerate projection (behind the camera's own eye
                # plane, w == 0) -- skip this sample; not connecting
                # across it to a stale previous point avoids a bogus
                # segment spanning the gap.
                prev_outer = None
                prev_inner = None
                continue

            cur_outer = (float(screen_outer.x), float(screen_outer.y))
            cur_inner = (float(screen_inner.x), float(screen_inner.y))

            if prev_outer is not None:
                if (
                    _hit_test.point_near_segment(
                        px, py, prev_outer[0], prev_outer[1], cur_outer[0], cur_outer[1], tolerance) or
                    _hit_test.point_near_segment(
                        px, py, prev_inner[0], prev_inner[1], cur_inner[0], cur_inner[1], tolerance) or
                    _hit_test.point_near_segment(
                        px, py, cur_outer[0], cur_outer[1], cur_inner[0], cur_inner[1], tolerance)
                ):
                    return True

            prev_outer = cur_outer
            prev_inner = cur_inner

        return False

    @_check_types.do
    def delete(self, context) -> None:
        super().delete(context)
