# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The one ring that rolls a wire service loop about the wire it sits in.

The ordinary three-axis gizmo (:class:`.generic.Rings3D`) turns a loop about its
centroid. A coil sits in a wire, though, and the line between the loop's start
and stop points is about 27 degrees off the coil's own axis, so to spin the
loop AROUND the wire the axle has to be the wire itself: the line through the
wire points either side of the loop. The pivot is where that line meets the
start/stop line (see ``objects_3d.wire_service_loop._wire_pivot``).

This gizmo is that axle as a ring: one ring, centered on the pivot, in the
plane perpendicular to the wire. Neither the pivot nor the wire moves when the
loop rolls (it is a rotation about a line through the pivot), so the ring stays
exactly where it is and only its protractor spins.

It reuses the ordinary gizmo's whole pick/drag/snap machinery by giving the
ring a private :class:`~geometry.angle.Angle` of its own to read, instead of
the loop's: its X and Y Euler values tilt the ring's plane to be perpendicular
to the wire, and its Z Euler value IS the roll, in degrees from the pose the
loop had when the ring came up. Writing that value (a drag, or a click on a
tick of the outer ring) rolls the loop to it, always from that starting pose
(see ``objects_3d.wire_service_loop.WireRoll``), so nothing drifts and a 0 on
the protractor means the loop is back where it began.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from . import generic as _generic
from .. import _axis
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...objects.objects_3d import base_3d as _base_3d


Config = _config.Config.editor_3d


class WireRollRings3D(_generic.Rings3D):
    """The single ring that rolls a wire service loop about its wire."""

    _HAS_TORUS = False

    @_check_types.do
    def _ring_axes(self) -> tuple:
        return ('z',)

    @_check_types.do
    def _make_center(self, obj3d: "_base_3d.Base3D") -> _point.Point:
        """The pivot, as a Point of the ring's own (never the loop's position
        or centroid, both of which move when the loop rolls).

        The roll is frozen here, before anything else is built: the radius and
        the ring's plane both come from it.
        """
        self._roll = obj3d.begin_wire_roll()

        pivot = self._roll.pivot

        return _point.Point(float(pivot[0]), float(pivot[1]), float(pivot[2]))

    @_check_types.do
    def _make_ring_angle(self, obj3d: "_base_3d.Base3D") -> _angle.Angle:
        """The ring's private Angle: its plane perpendicular to the wire and a
        roll of 0.

        The ring's plane normal is ``Ry(ey) Rx(ex) Z`` (``rotation_mesh.
        slot_ring_angle`` for the Z ring, Z being the innermost Euler slot and
        so left out of the plane), which for a unit axis ``(ax, ay, az)`` is
        ``(sin ey cos ex, -sin ex, cos ey cos ex)``. Solved for the axis:
        ``ex = -asin(ay)`` and ``ey = atan2(ax, az)``; straight up or down
        leaves ``ey`` free, and 0 does as well as any.
        """
        ax, ay, az = [float(v) for v in self._roll.axis]

        ex = -math.degrees(math.asin(max(-1.0, min(1.0, ay))))

        if abs(ay) > 1.0 - 1e-9:
            ey = 0.0
        else:
            ey = math.degrees(math.atan2(ax, az))

        return _angle.Angle.from_euler(ex, ey, 0.0)

    @_check_types.do
    def _ring_material(self) -> "_materials.GLMaterial":
        """No torus to borrow a material from; render() never uses it (see
        Rings3D.__init__), so this ring's own color does.
        """
        return _materials.Generic(self._colors[self._axes[-1]])

    @_check_types.do
    def _bind_object(self, obj3d: "_base_3d.Base3D") -> None:
        """Follow nothing. The loop's angle and position change because of
        this ring, and the ring does not depend on them: the pivot and the
        wire it is built from do not move when the loop rolls.
        """

    @_check_types.do
    def _unbind_object(self) -> None:
        """Nothing was bound; see :meth:`_bind_object`."""

    @_check_types.do
    def _compute_radius_values(self) -> tuple[float, float]:
        """(radius, object_radius) from how far the loop reaches from the pivot.

        The farthest corner of the loop's box from the pivot. A roll about a
        line through the pivot carries every corner round a circle about that
        line, so the distance does not change as the loop rolls and the ring
        never has to resize, and it always clears the loop. (Sized from the
        loop's box height, as the ordinary gizmo is from the diagonal, it
        would not: the pivot is at the coil's end, not its middle.)
        """
        corners = np.asarray(self._obj3d.obb, dtype=np.float64)
        reach = float(np.linalg.norm(corners - self._roll.pivot, axis=1).max())

        diameter = reach * 2.0 * float(Config.rotation_handler.diameter_scale)

        return max(diameter / 2.0, 1e-3), max(reach, 1e-3)

    @_check_types.do
    def apply_drag_angle(self, axis: str, value: float) -> None:
        """Roll the loop to *value* degrees from the pose it began in.

        :param axis: ``'z'``, the only axis this ring has.
        :param value: Roll in degrees, the ring's own Z Euler value.
        """
        _axis.set_axis(self._ring_angle, axis, value)

        # The protractor spins by this value, and the loop's box (what culling
        # reads) has moved
        self._refresh_rings()
        self._obj3d.roll_to(self._roll, value)

        self._compute_obb()
        self._compute_aabb()
