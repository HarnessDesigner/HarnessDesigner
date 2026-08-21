# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The world-space protractor ring -- ticks, text and washer, with its
own-slot spin held fixed regardless of drag.

Its plane orientation still nests under the *other* two axes exactly
like every other ring in this gizmo (the "gyroscope" behavior) -- only
this axis's own Euler value is zeroed out before computing the plane,
so this ring's own ``0`` tick never moves even while the inner ring
(and the object) spin past it. See :meth:`OuterRing._disc_rotation`.

Owns the hover-highlight-nearest-tick / click-to-snap-to-that-exact-
angle interaction -- there is no drag here, only discrete picks.
"""

import math
from typing import TYPE_CHECKING

from ._protractor_base import ProtractorRingBase
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl.canvas_base import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl.canvas_base import camera_base as _camera_base


# Nearest-tick highlight color -- bright red, per "if the user clicks
# when a mark is red the rotation would be set to that exact angle."
_HOVER_TICK_COLOR = (1.0, 0.15, 0.15)


class OuterRing(ProtractorRingBase):
    """One axis's world-space, fixed-spin protractor ring.

    :param axis: ``'x'``, ``'y'`` or ``'z'`` -- which Euler slot this
        ring displays a snap target for.
    :param obj_angle: The tracked object's own :class:`Angle` instance,
        read (not written) to keep this ring's plane nested under the
        other two axes' current values.
    """

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, radius: float,
                depth: float, material, label_size: float,
                obj_angle: _angle.Angle, context):

        self.axis = axis
        self._obj_angle = obj_angle
        self._hovered_tick = None

        super().__init__(center, radius, depth, material, label_size, context)
        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
        ex, ey, ez = self._obj_angle.as_euler_float

        if self.axis == 'x':
            ex = 0.0
        elif self.axis == 'y':
            ey = 0.0
        else:
            ez = 0.0

        return _rotation_mesh.slot_ring_angle(self.axis, (ex, ey, ez))

    @_check_types.do
    def on_object_angle_changed(self) -> None:
        """Refresh tick/label placement when either of the *other* two
        axes changes (this ring's own axis never moves it -- see
        :meth:`_disc_rotation`).
        """
        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def update_hover(self, mouse_pos: _point.Point,
                     camera: "_camera_base.CameraBase",
                     tolerance: float = 10.0) -> bool:
        """Find the nearest tick to *mouse_pos* in screen space and mark
        it hovered if within *tolerance* pixels; clears the hover
        otherwise.

        :returns: Whether a tick is now hovered.
        """
        if not self.is_visible or not self._ticks:
            self._hovered_tick = None
            return False

        px = float(mouse_pos.x)
        py = float(mouse_pos.y)

        best = None
        best_dist = tolerance

        for tick in self._ticks:
            screen = camera.ProjectPoint(tick.position)
            dx = float(screen.x) - px
            dy = float(screen.y) - py
            dist = math.hypot(dx, dy)

            if dist <= best_dist:
                best_dist = dist
                best = tick

        self._hovered_tick = best
        return best is not None

    @_check_types.do
    def click_hovered(self) -> float | None:
        """Return the Euler value the hovered tick snaps this axis to,
        or ``None`` if nothing is currently hovered. The caller writes
        the value back to ``obj_angle`` (same reasoning as
        :meth:`.inner_ring.InnerRing.update_drag` -- this class only
        computes, the assembler owns the write/unbind-rebind).
        """
        if self._hovered_tick is None:
            return None

        return _rotation_mesh.wrap_angle(self._hovered_tick.degrees)

    @property
    @_check_types.do
    def hovered_degrees(self) -> float | None:
        if self._hovered_tick is None:
            return None
        return self._hovered_tick.degrees

    @_check_types.do
    def clear_hover(self) -> None:
        self._hovered_tick = None

    @_check_types.do
    def _tick_override_color(self, degrees: float) -> "tuple[float, float, float] | None":
        if self._hovered_tick is not None and self._hovered_tick.degrees == degrees:
            return _HOVER_TICK_COLOR
        return None

    @_check_types.do
    def delete(self, context) -> None:
        pass
