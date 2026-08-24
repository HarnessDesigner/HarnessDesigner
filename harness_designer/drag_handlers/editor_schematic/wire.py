# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interior-segment drag for a Wire in the Schematic Editor.

Every schematic wire is a strictly orthogonal (horizontal/vertical-only)
chain of points: its true start, zero or more interior waypoints (each a
real ``WireLayout``), and its true stop -- consecutive segments always
alternate H/V (see ``objects_schematic.wire_routing``, the auto-router
that lays this out in the first place).

Only a segment fully bounded by two real waypoints (not the wire's own
true start/stop, which are anchored to whatever they're attached to and
never move here) is draggable -- clicking the segment nearest either
true end is a no-op for this handler; a wire with fewer than 2 interior
waypoints has no such segment at all. Dragging one moves both of its
bounding waypoints together by the same perpendicular delta (their
along-the-segment coordinate never changes -- it's shared with whichever
fixed point the *next* segment over connects to, so the path either side
stays orthogonal automatically, no re-derivation needed).

Two things happen live, every move:

- **Straightening.** If the moved segment's own connecting segment to
  a fixed neighbor shrinks to zero length (the dragged point has
  reached that neighbor's own coordinate), the wire has gone straight
  through there and that waypoint is redundant. Rather than delete/
  recreate its ``WireLayout`` on every frame (thrashy, and wrong if the
  user backtracks a pixel later), it's simply hidden
  (``obj.objschematic.is_visible = False``) -- shown again the moment
  the drag moves back past straight. The actual DB delete only happens
  once, on release, for whichever side(s) are still collapsed then.
- **Obstacle clamp.** Every candidate move is checked against
  ``wire_routing.segment_blocked`` (crosses a housing, or runs closer
  than ``Config.layout.wire_spacing`` to another connected wire's own
  parallel lane) before being applied -- a blocked candidate is
  rejected outright (the segment stops at the last legal position)
  rather than committed. This is intentionally a hard clamp, not a
  live rip-up-and-reroute around the obstacle (which would mean
  inserting/removing arbitrary extra waypoints mid-drag, not just the
  two already being dragged) -- a deliberately scoped first pass.
"""

import math
from typing import TYPE_CHECKING

from .. import editor_schematic as _editor_schematic
from ...objects.objects_schematic import wire_routing as _wire_routing
from ...database.project_db import pjt_wire as _pjt_wire
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class WireSegmentDragPlan:
    """What a click on a Wire's rendered strand should drag -- computed
    once at drag-start by :func:`plan_wire_segment_drag`.

    :ivar p_before: Live Point immediately before the dragged segment --
        fixed; may be the wire's own true start.
    :ivar p_near: Live Point at the dragged segment's own start -- moves.
    :ivar p_far: Live Point at the dragged segment's own end -- moves.
    :ivar p_after: Live Point immediately after the dragged segment --
        fixed; may be the wire's own true stop.
    :ivar horizontal: Whether the dragged segment itself is horizontal
        (True) or vertical (False) -- the drag moves it perpendicular
        to this, i.e. in Z when horizontal, X when vertical.
    :ivar layout_near: The real WireLayout facade at ``p_near`` --
        hidden/shown as the near-side connecting segment
        collapses/uncollapses.
    :ivar layout_far: Same, for ``p_far``/the far side.
    :ivar waypoint_near: The ``pjt_points2d`` row backing ``p_near`` --
        the actual row deleted on release if that side ends up
        collapsed (``layout_near`` only owns the marker, not the point
        row itself -- see ``objects_schematic.wire_reroute.reroute_wire``'s
        own delete-layout-then-delete-point pattern, mirrored exactly on
        commit here).
    :ivar waypoint_far: Same, for ``p_far``/the far side.
    """

    __slots__ = (
        'p_before', 'p_near', 'p_far', 'p_after', 'horizontal',
        'layout_near', 'layout_far', 'waypoint_near', 'waypoint_far')

    def __init__(self, p_before, p_near, p_far, p_after, horizontal: bool,
                layout_near, layout_far, waypoint_near, waypoint_far):
        self.p_before = p_before
        self.p_near = p_near
        self.p_far = p_far
        self.p_after = p_after
        self.horizontal = horizontal
        self.layout_near = layout_near
        self.layout_far = layout_far
        self.waypoint_near = waypoint_near
        self.waypoint_far = waypoint_far


@_check_types.do
def _find_layout(project, point) -> object | None:
    """Return the real WireLayout facade anchored at *point* (a live 2D
    Point), or None. One-time lookup at drag-arm -- see
    objects.wire.Wire.layouts for the exact same scan, done there for a
    whole wire's worth of points instead of just one.
    """
    for layout in project.wire_layouts:
        if layout.db_obj.position2d_id == point.db_id:
            return layout

    return None


@_check_types.do
def plan_wire_segment_drag(wire: "_objects.ObjectBase", world_click: tuple) -> "WireSegmentDragPlan | None":
    """Work out what a click on *wire*'s rendered strand at *world_click*
    (an ``(x, z)`` world position) should drag -- see the module
    docstring for the full rule. None if the click's nearest segment
    isn't fully bounded by two real waypoints.
    """
    objschematic = wire.objschematic
    waypoints = list(wire.db_obj.waypoints2d)

    if len(waypoints) < 2:
        return None

    points = [objschematic._p1] + [wp.point for wp in waypoints] + [objschematic._p2]  # NOQA
    positions = [(float(p.x), float(p.z)) for p in points]

    click_x, click_z = world_click
    best_i = None
    best_dist = math.inf

    # Only i in [1, len-3] has both bounding points as real waypoints
    # (index 0 and len-1 are the wire's own true start/stop).
    for i in range(1, len(points) - 2):
        ax, az = positions[i]
        bx, bz = positions[i + 1]

        if abs(az - bz) < 1e-9:  # horizontal segment
            t = 0.0 if bx == ax else max(0.0, min(1.0, (click_x - ax) / (bx - ax)))
            px, pz = ax + t * (bx - ax), az
        else:  # vertical segment
            t = 0.0 if bz == az else max(0.0, min(1.0, (click_z - az) / (bz - az)))
            px, pz = ax, az + t * (bz - az)

        dist = math.hypot(click_x - px, click_z - pz)
        if dist < best_dist:
            best_dist = dist
            best_i = i

    if best_i is None:
        return None

    i = best_i
    ax, az = positions[i]
    bx, bz = positions[i + 1]
    horizontal = abs(az - bz) < 1e-9

    project = wire.mainframe.project

    return WireSegmentDragPlan(
        p_before=points[i - 1], p_near=points[i], p_far=points[i + 1],
        p_after=points[i + 2], horizontal=horizontal,
        layout_near=_find_layout(project, points[i]),
        layout_far=_find_layout(project, points[i + 1]),
        waypoint_near=waypoints[i - 1], waypoint_far=waypoints[i])


class Wire(_editor_schematic.DragHandlerSchematic):
    """Interior-segment drag for a Wire -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
                plan: WireSegmentDragPlan):
        super().__init__(canvas, target)

        self._plan = plan
        self._collapsed_near = False
        self._collapsed_far = False

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, locked ortho camera gives an absolute world position directly
        plan = self._plan
        world_pos = self._world_xz(mouse_pos)

        if plan.horizontal:
            candidate = float(world_pos.z)
            before_fixed = float(plan.p_before.z)
            after_fixed = float(plan.p_after.z)
        else:
            candidate = float(world_pos.x)
            before_fixed = float(plan.p_before.x)
            after_fixed = float(plan.p_after.x)

        project = self.canvas.mainframe.project

        def _candidate_edges(value: float):
            if plan.horizontal:
                near = (float(plan.p_near.x), value)
                far = (float(plan.p_far.x), value)
                before = (float(plan.p_before.x), before_fixed)
                after = (float(plan.p_after.x), after_fixed)
            else:
                near = (value, float(plan.p_near.z))
                far = (value, float(plan.p_far.z))
                before = (float(plan.p_before.x), float(plan.p_before.z))
                after = (float(plan.p_after.x), float(plan.p_after.z))
            return before, near, far, after

        before, near, far, after = _candidate_edges(candidate)

        if (
            _wire_routing.segment_blocked(project, before, near, ignore_wire=self.target) or
            _wire_routing.segment_blocked(project, near, far, ignore_wire=self.target) or
            _wire_routing.segment_blocked(project, far, after, ignore_wire=self.target)
        ):
            # Illegal move -- leave both points exactly where they
            # already are (last legal position) instead of applying it.
            return

        if plan.horizontal:
            plan.p_near.z = candidate
            plan.p_far.z = candidate
        else:
            plan.p_near.x = candidate
            plan.p_far.x = candidate

        collapsed_near = abs(candidate - before_fixed) < 1e-6
        collapsed_far = abs(candidate - after_fixed) < 1e-6

        if collapsed_near != self._collapsed_near and plan.layout_near is not None:
            plan.layout_near.objschematic.is_visible = not collapsed_near
            self._collapsed_near = collapsed_near

        if collapsed_far != self._collapsed_far and plan.layout_far is not None:
            plan.layout_far.objschematic.is_visible = not collapsed_far
            self._collapsed_far = collapsed_far

    @_check_types.do
    def delete(self) -> None:
        """Commit whatever's currently live: a still-collapsed side's
        waypoint is deleted for real (it was only ever hidden during the
        drag) -- both the WireLayout marker (proper facade teardown when
        one was found at drag-arm; a raw delete_layouts_at() sweep as a
        defensive fallback otherwise -- mirrors
        ``wire_reroute.reroute_wire``'s own blind sweep, used there
        because it never holds a live facade reference to begin with)
        and its backing pjt_points2d row. Anything not collapsed keeps
        its own already-live position -- no full reroute() call needed,
        the drag already left every point exactly where it should be.
        """
        plan = self._plan
        project = self.canvas.mainframe.project
        layouts_table = project.ptables.pjt_wire_layouts_table

        if self._collapsed_near:
            if plan.layout_near is not None:
                plan.layout_near.delete()
            else:
                _pjt_wire.delete_layouts_at(layouts_table, 'point2d_id', plan.waypoint_near.db_id)
            plan.waypoint_near.delete()

        if self._collapsed_far:
            if plan.layout_far is not None:
                plan.layout_far.delete()
            else:
                _pjt_wire.delete_layouts_at(layouts_table, 'point2d_id', plan.waypoint_far.db_id)
            plan.waypoint_far.delete()

        self.target.objschematic.refresh_waypoints()

        super().delete()
