# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared wire/bundle-chain geometry, used identically by the 3D and
peg-board editors' own wire (and bundle) view objects.

A wire/bundle's path is a chain of straight segments: start, through
each interior waypoint in idx order, to stop. Working out "what point
on this chain is closest to a screen click" breaks into exactly two
pieces:

- Which interior waypoints to walk (:meth:`WireTypeMixin._waypoints`) --
  each view has its own independent waypoint set (``PJTWire.waypoints3d``
  vs. ``waypoints_pegboard`` -- see that class's own docstring on why
  the two counts genuinely differ), so this is a required override.
- How to resolve a screen position into a point on that chain
  (:meth:`WireTypeMixin._point_on_wire`) -- also a required override,
  and genuinely a different *algorithm* per view, not just a different
  data source: the 3D editor's free-orbit camera makes a screen click
  ambiguous in depth, so it has to cast a ray and intersect it against
  each segment's own tube radius (breaking ties by camera depth when a
  bent wire's segments visually cross on screen); the peg-board's locked
  top-down orthographic camera already resolves a screen position to an
  unambiguous world X/Z point directly, so it only needs plain 2D
  point-to-segment distance. Mirrors
  :class:`~harness_designer.handlers.wire_drag_base.WireDragBase`'s own
  ``_move_delta`` split (shared skeleton, one step genuinely differs by
  view) -- see that module's docstring for the same reasoning applied to
  dragging.

Once those two pieces are supplied, :meth:`_segments`/
:meth:`get_closest_point`/:meth:`get_closest_endpoint` are identical
for every view and live here exactly once. Per-view concrete mixins
(``objects_3d.mixins.wire_type.WireTypeMixin``,
``objects_pegboard.mixins.WireTypeMixin``) extend this class, adding
only their own ``_waypoints``/``_point_on_wire`` -- ``objects_3d.wire.
Wire``/``objects_3d.bundle.Bundle`` and ``objects_pegboard.wire.Wire``
keep mixing in their own view's concrete subclass unchanged; nothing
about those class declarations needs to change for this to be shared.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types


if TYPE_CHECKING:
    pass


class WireTypeMixin:
    start_position: _point.Point = None
    stop_position: _point.Point = None
    db_obj = None

    # ------------------------------------------------------------------
    # View-specific accessors -- every concrete per-view mixin MUST
    # override both of these. Never getattr/duck-typing, so IDE
    # navigation and static type-checking keep working.
    # ------------------------------------------------------------------

    def _waypoints(self, db_obj):
        """Return *db_obj*'s own ordered interior waypoints for this
        view (e.g. ``db_obj.waypoints3d`` / ``db_obj.waypoints_pegboard``).
        """
        raise NotImplementedError

    def _point_on_wire(
        self, mouse_pos: _point.Point
    ) -> tuple[np.ndarray, int] | tuple[None, None]:
        """Resolve *mouse_pos* to ``(closest_point, segment_index)`` on
        this wire's own current path -- see the module docstring for why
        this is a required override, not shared math.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared chain geometry.
    # ------------------------------------------------------------------

    @_check_types.do
    def _segments(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Every (p1, p2) sub-segment from start, through each interior
        waypoint (see :meth:`_waypoints`) in idx order, to stop -- a
        wire/bundle with no interior waypoints is just the one
        (start, stop) pair.
        """
        points = [self.start_position.as_numpy]
        for waypoint in self._waypoints(self.db_obj):
            points.append(waypoint.point.as_numpy)
        points.append(self.stop_position.as_numpy)

        return list(zip(points, points[1:]))

    @_check_types.do
    def get_closest_point(
        self, mouse_pos: _point.Point
    ) -> tuple[_point.Point | None, _angle.Angle | None, int | None]:
        """Find the closest point on this wire/bundle to where the user
        clicked.

        Returns ``(closest_point, wire_angle, segment_index)`` or
        ``(None, None, None)``. ``segment_index`` is exactly the
        insertion index a caller needs to add a new waypoint at this
        point (segment i sits between waypoint i-1 and waypoint i, see
        :meth:`_segments`) -- e.g.
        ``handlers.wire_layout_handler._create_wire_layout_on_wire``,
        ``handlers.wire_topology.split_wire_at_point``.
        """
        closest_point, seg_idx = self._point_on_wire(mouse_pos)

        if closest_point is None:
            return None, None, None

        seg_p1, seg_p2 = self._segments()[seg_idx]

        wire_direction = seg_p2 - seg_p1
        wire_length = np.linalg.norm(wire_direction)

        if wire_length < 0.001:
            return None, None, None

        wire_direction = wire_direction / wire_length
        wire_angle = _angle.Angle.from_direction(wire_direction)

        return _point.Point(*closest_point), wire_angle, seg_idx

    @_check_types.do
    def get_closest_endpoint(self, mouse_pos: _point.Point, endpoint_tolerance=5.0):
        """Find whether a picked wire/bundle location lands on an
        existing true endpoint.

        Only the wire's own true start/stop count as "an endpoint" here
        -- every interior bend already has its own pickable
        WireLayout/BundleLayout, which callers hit-test separately
        before ever falling back to this closest-point-on-the-raw-chain
        path.

        :returns: (position, is_endpoint, endpoint_name).
        """
        p1 = self.start_position.as_numpy
        p2 = self.stop_position.as_numpy

        closest_point, _seg_idx = self._point_on_wire(mouse_pos)
        if closest_point is None:
            return _point.Point(*p1), False, None

        dist_to_p1 = np.linalg.norm(closest_point - p1)
        dist_to_p2 = np.linalg.norm(closest_point - p2)

        wire_diameter = self.db_obj.part.od_mm
        tolerance = max(wire_diameter, endpoint_tolerance)

        if dist_to_p1 < tolerance:
            return _point.Point(*p1), True, 'start'
        elif dist_to_p2 < tolerance:
            return _point.Point(*p2), True, 'stop'
        else:
            return _point.Point(*closest_point), False, None
