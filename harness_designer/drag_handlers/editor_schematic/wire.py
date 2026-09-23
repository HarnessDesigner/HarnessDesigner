# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interior-segment drag for a Wire in the Schematic Editor.

Every schematic wire is a strictly orthogonal (horizontal/vertical-only)
chain of points: its true start, zero or more interior waypoints (each a
real ``WireLayout``), and its true stop -- consecutive segments always
alternate H/V (see ``wire_routing.routing``, the auto-router
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

Four things happen live, every move:

- **Straightening.** If the moved segment's own connecting segment to
  a fixed neighbor shrinks to zero length (the dragged point has
  reached that neighbor's own coordinate), the wire has gone straight
  through there and that waypoint is redundant. Rather than delete/
  recreate its ``WireLayout`` on every frame (thrashy, and wrong if the
  user backtracks a pixel later), it's simply hidden
  (``obj.objschematic.is_visible = False``) -- shown again the moment
  the drag moves back past straight. The actual DB delete only happens
  once, on release, for whichever side(s) are still collapsed then.
- **Obstacle clamp.** The two connecting edges (dragged-point to fixed
  neighbor on either side) are a hard clamp, exactly as before: blocked
  by ``routing.segment_blocked`` (crosses a housing/terminal stub, or
  runs closer than ``Config.layout.wire_spacing`` to another connected
  wire's own parallel lane) means the candidate move is rejected
  outright and both points stay at the last legal position. These two
  never push -- only the segment actually being dragged does (below).
- **Push/shove.** The dragged segment itself (near -> far) no longer
  just clamps the instant it would run too close to another wire's own
  parallel run. Instead (see :func:`_attempt_push`) it tries to shove
  that other wire's own segment further out of the way first -- which
  can in turn need to shove whatever IT'S now too close to, cascading
  as deep as the stack goes (:data:`_MAX_PUSH_DEPTH` deep) -- and only
  falls back to a hard clamp once some link in that chain genuinely
  can't move (it cuts through a housing/terminal stub, or it isn't a
  segment this mechanism can move at all -- one bounded by a true wire
  end rather than two real waypoints). A segment that crosses a housing
  or a terminal's own stub is always a hard clamp outright, same as
  ever -- nothing pushes a housing aside.

- **Partial move / jog.** A push can fail even though the blocking
  wire's segment doesn't actually run the dragged segment's WHOLE
  length -- it might only overlap part of it, leaving the rest genuinely
  clear. When that's the case, and the mouse itself is over the clear
  part (not over where the blocker actually is), clamping the entire
  segment is needlessly conservative: :meth:`Wire._maybe_partial_jog`
  splits the drag in two instead -- the still-blocked side is pinned
  exactly at the last legal lane, the side the mouse is actually over
  keeps following it, and 2 new waypoints are spliced in at the
  boundary between them for the resulting step. This re-plans the drag
  onto the newly freed segment for the rest of the gesture -- the
  pinned side becomes an ordinary fixed neighbor from here on, same as
  the wire's own true start/stop always were.

  Once a push chain fails outright -- no partial jog applies either --
  and the user keeps dragging well past where it gave up, continuing to
  just sit at the clamped position stops being useful -- so
  :func:`_maybe_reroute_past` gives up on this interactive per-segment
  drag entirely and asks the auto-router (``wire_routing.reroute.
  reroute_wire``) for a whole fresh path instead, the only way to
  actually get the wire past a stack it can't shove aside or jog around.
  From that point on this handler goes inert for the rest of the
  gesture (:attr:`Wire._rerouted`) -- the wire's own waypoint structure
  just changed out from under the plan this drag started with, so
  there's nothing left here to keep dragging.
"""

import math
from typing import TYPE_CHECKING

from .. import editor_schematic as _editor_schematic
from ...wire_routing import routing as _wire_routing
from ...wire_routing import reroute as _wire_reroute
from ...database.project_db import pjt_wire as _pjt_wire
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


# How many wires deep a single push can cascade through before giving up --
# a generous ceiling against a pathological stack, not a number expected to
# ever actually bind in practice (a real bundle is a handful of wires wide).
_MAX_PUSH_DEPTH = 12

# How close a candidate lane needs to be to a fixed neighbor's own coordinate
# (as a fraction of one lane spacing) before it snaps to dead straight and
# the connecting run between them is treated as collapsed -- see __call__'s
# own straightening snap. Tunable: this is a feel/UX threshold, not a
# geometric constant with one correct value.
_STRAIGHTEN_TOLERANCE_FRACTION = 0.2


class WireSegmentDragPlan:
    """What a click on a Wire's rendered strand should drag -- computed
    once at drag-start by :func:`plan_wire_segment_drag` (also reused,
    per arbitrary segment index rather than a click, by
    :func:`_pushable_segment_plan` when deciding whether some OTHER
    wire's segment can be shoved out of the way -- see
    :func:`_segment_plan_at`).

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
        row itself -- see ``wire_routing.reroute.reroute_wire``'s
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


def _chain_points(wire) -> tuple[list, list]:
    """*wire*'s own live 2D path, start to stop, as ``(points, waypoints)``
    -- ``points`` is every live Point along it (true start, each interior
    waypoint's own Point in order, true stop), ``waypoints`` the backing
    ``pjt_points2d`` rows for the interior ones only (``points[1:-1]``,
    one-to-one). Shared by :func:`plan_wire_segment_drag` (planning a
    click) and :func:`_pushable_segment_plan` (planning a push, given a
    segment index instead of a click position) so both build the exact
    same chain the exact same way.
    """
    objschematic = wire.objschematic
    waypoints = list(wire.db_obj.waypoints2d)
    points = [objschematic._p1] + [wp.point for wp in waypoints] + [objschematic._p2]  # NOQA
    return points, waypoints


def _segment_plan_at(wire, points: list, waypoints: list, i: int) -> WireSegmentDragPlan | None:
    """Build the :class:`WireSegmentDragPlan` for *wire*'s segment
    ``points[i] -> points[i + 1]`` -- None unless that segment is fully
    bounded by two real waypoints (``1 <= i <= len(points) - 3``, i.e.
    neither ``points[i]`` nor ``points[i + 1]`` is the wire's own true
    start/stop). The shared tail of both :func:`plan_wire_segment_drag`
    (which finds *i* from a click) and :func:`_pushable_segment_plan`
    (which already knows *i* -- it came from :func:`_find_blocking_wire`).
    """
    if i < 1 or i > len(points) - 3:
        return None

    az = float(points[i].z)
    bz = float(points[i + 1].z)
    horizontal = abs(az - bz) < 1e-9

    project = wire.mainframe.project

    return WireSegmentDragPlan(
        p_before=points[i - 1], p_near=points[i], p_far=points[i + 1],
        p_after=points[i + 2], horizontal=horizontal,
        layout_near=_find_layout(project, points[i]),
        layout_far=_find_layout(project, points[i + 1]),
        waypoint_near=waypoints[i - 1], waypoint_far=waypoints[i])


@_check_types.do
def plan_wire_segment_drag(wire: "_objects.ObjectBase", world_click: tuple) -> WireSegmentDragPlan | None:
    """Work out what a click on *wire*'s rendered strand at *world_click*
    (an ``(x, z)`` world position) should drag -- see the module
    docstring for the full rule. None if the click's nearest segment
    isn't fully bounded by two real waypoints.
    """
    points, waypoints = _chain_points(wire)

    if len(waypoints) < 2:
        return None

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

    return _segment_plan_at(wire, points, waypoints, best_i)


def _pushable_segment_plan(wire, seg_index: int) -> WireSegmentDragPlan | None:
    """The push-eligible plan for *wire*'s segment #*seg_index* (0-based,
    the edge from its chain's point *seg_index* to point *seg_index + 1*)
    -- None unless that segment is fully bounded by two real waypoints,
    the same "fully bounded" rule interactive dragging itself is limited
    to (see :func:`_segment_plan_at`) -- a segment touching a wire's own
    true end can't be shifted this way at all, since a true end never
    moves. This is exactly what makes a wire "not able to be pushed" (see
    the module docstring) when the blocking segment turns out to be one
    of these.
    """
    points, waypoints = _chain_points(wire)
    return _segment_plan_at(wire, points, waypoints, seg_index)


def _find_blocking_wire(project, exclude_wires: frozenset, edge_p1: tuple, edge_p2: tuple):
    """The first OTHER wire whose own segment runs parallel to, and
    within one lane spacing of, the axis-aligned edge *edge_p1* ->
    *edge_p2* over a real overlapping stretch -- mirrors
    ``routing._edge_too_close_to_wire``'s own rule exactly, but (unlike
    that pooled/numpy check, built for A*'s hot loop) resolves back to
    the actual ``Wire`` facade and its segment's own chain index, so the
    blocker can be inspected and -- via :func:`_pushable_segment_plan` --
    potentially shoved. A plain per-wire Python loop, not the segment
    pool: this only ever runs once or twice per interactive mouse move,
    never per A* neighbour.

    Returns ``(wire, seg_index, seg_p1, seg_p2)``, or ``None`` if nothing
    is close enough to matter.
    """
    x1, z1 = edge_p1
    x2, z2 = edge_p2
    horizontal = abs(z1 - z2) < _wire_routing._EPS  # NOQA
    spacing = _wire_routing._lane_spacing()  # NOQA

    if horizontal:
        this_lo, this_hi = min(x1, x2), max(x1, x2)
    else:
        this_lo, this_hi = min(z1, z2), max(z1, z2)

    for wire in project.wires:
        if wire in exclude_wires or not wire.is_connected:
            continue

        points, _waypoints = _chain_points(wire)
        positions = [(float(p.x), float(p.z)) for p in points]

        for idx in range(len(positions) - 1):
            (ax, az), (bx, bz) = positions[idx], positions[idx + 1]
            seg_horizontal = abs(az - bz) < _wire_routing._EPS  # NOQA
            if seg_horizontal != horizontal:
                continue

            if horizontal:
                if abs(az - z1) >= spacing - _wire_routing._LANE_EPS:  # NOQA
                    continue
                lo, hi = min(ax, bx), max(ax, bx)
            else:
                if abs(ax - x1) >= spacing - _wire_routing._LANE_EPS:  # NOQA
                    continue
                lo, hi = min(az, bz), max(az, bz)

            if max(this_lo, lo) < min(this_hi, hi) - _wire_routing._EPS:  # NOQA
                return wire, idx, positions[idx], positions[idx + 1]

    return None


def _attempt_push(project, wire, seg_index: int, candidate_lane: float, sign: float, horizontal: bool,
                  exclude_wires: frozenset, updates: list, depth: int = 0) -> bool:
    """Try to shove *wire*'s segment #*seg_index* far enough past
    *candidate_lane* (one full lane spacing beyond it, in the *sign*
    direction along the perpendicular axis) to make legal room for
    whatever is pushing it there -- cascading into whatever THAT segment
    then turns out to be too close to in turn, up to
    :data:`_MAX_PUSH_DEPTH` links deep.

    On success, appends every ``(Point, x, z)`` update the whole chain
    needs to *updates* (for a single batched
    ``wire_routing.reroute.apply_shifts`` call) and returns True.
    Returns False -- leaving *updates* exactly as it was on entry, since
    nothing partial from a failed link is ever appended -- the moment
    any link in the chain can't be pushed at all: a segment touching a
    true wire end (see :func:`_pushable_segment_plan`), a target
    position that cuts through a housing or a terminal's own stub, or
    the depth limit.

    A target position merely too close to yet ANOTHER wire is not a
    failure by itself -- that's the cascade case, handled by recursing
    into THAT wire next, still under the same *sign*/*horizontal*, with
    *wire* added to *exclude_wires* so the chain can't double back on
    itself.
    """
    if depth >= _MAX_PUSH_DEPTH or wire in exclude_wires:
        return False

    plan = _pushable_segment_plan(wire, seg_index)
    if plan is None or plan.horizontal != horizontal:
        return False

    spacing = _wire_routing._lane_spacing()  # NOQA
    target_lane = candidate_lane + sign * spacing

    if horizontal:
        near = (float(plan.p_near.x), target_lane)
        far = (float(plan.p_far.x), target_lane)
    else:
        near = (target_lane, float(plan.p_near.z))
        far = (target_lane, float(plan.p_far.z))

    before = (float(plan.p_before.x), float(plan.p_before.z))
    after = (float(plan.p_after.x), float(plan.p_after.z))

    # The two connecting runs never push, same as the live-dragged
    # segment's own connecting runs never do -- only the segment actually
    # being moved (here, the pushed one itself) ever tries to shove
    # something else out of the way.
    if (_wire_routing.segment_blocked(project, before, near, ignore_wire=wire) or
            _wire_routing.segment_blocked(project, far, after, ignore_wire=wire)):
        return False

    reason = _wire_routing.free_segment_blocked(project, near, far, ignore_wire=wire)

    if reason in ('housing', 'terminal'):
        return False

    chain_exclude = exclude_wires | {wire}

    if reason == 'wire':
        blocker = _find_blocking_wire(project, chain_exclude, near, far)
        if blocker is None:
            # free_segment_blocked disagreed with _find_blocking_wire's
            # own (numerically slightly different) test -- treat as
            # blocked rather than silently pushing into an unknown.
            return False

        if not _attempt_push(project, blocker[0], blocker[1], target_lane, sign, horizontal,
                             chain_exclude, updates, depth + 1):
            return False

    updates.append((plan.p_near, near[0], near[1]))
    updates.append((plan.p_far, far[0], far[1]))
    return True


class Wire(_editor_schematic.DragHandlerSchematic):
    """Interior-segment drag for a Wire -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
                plan: WireSegmentDragPlan):
        super().__init__(canvas, target)

        self._plan = plan
        self._collapsed_near = False
        self._collapsed_far = False

        # The perpendicular coordinate this drag started at -- the fixed
        # reference push direction (_origin_lane -> candidate) is judged
        # against, and the last position this drag actually reached
        # legally, used by _maybe_reroute_past to tell "still stuck at
        # the same wall" from "mouse has clearly carried on past it".
        origin = float(plan.p_near.z if plan.horizontal else plan.p_near.x)
        self._origin_lane = origin
        self._last_legal_lane = origin

        # Set True once a push chain has failed badly enough that this
        # drag gave up and asked the auto-router for a whole fresh path
        # instead (see _maybe_reroute_past) -- from that point on this
        # handler is inert for the rest of the gesture: the wire's own
        # waypoint structure changed out from under self._plan.
        self._rerouted = False

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, locked ortho camera gives an absolute world position directly
        if self._rerouted:
            return

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

        # Snap to dead straight once merely CLOSE to lining up with a
        # fixed neighbor -- pixel-perfect alignment with a mouse is
        # impractical, so "straight or close to being straight" (the
        # feature's own original wording) has to actually mean straight,
        # not almost. Whichever neighbor it's closer to wins the rare
        # case it's within tolerance of both. This has to happen before
        # the legality checks below, not just before the collapse
        # detection near the bottom of this method -- straightening a
        # single-mm-scale nudge into an exact match is what actually
        # makes the connecting run's own length hit zero (see the module
        # docstring's "Straightening" section), so the near/far positions
        # used everywhere below need to already be the snapped ones.
        straighten_tol = _wire_routing._lane_spacing() * _STRAIGHTEN_TOLERANCE_FRACTION  # NOQA
        if abs(candidate - before_fixed) < straighten_tol:
            candidate = before_fixed
        elif abs(candidate - after_fixed) < straighten_tol:
            candidate = after_fixed

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

        # The two connecting runs are always a hard clamp -- they never
        # push, only the dragged segment itself (near -> far) does.
        if (_wire_routing.segment_blocked(project, before, near, ignore_wire=self.target) or
                _wire_routing.segment_blocked(project, far, after, ignore_wire=self.target)):
            return

        reason = _wire_routing.free_segment_blocked(project, near, far, ignore_wire=self.target)

        if reason is not None:
            pushed = False

            if reason == 'wire':
                sign = 1.0 if candidate >= self._origin_lane else -1.0
                blocker = _find_blocking_wire(project, frozenset((self.target,)), near, far)

                if blocker is not None:
                    updates = []
                    if _attempt_push(project, blocker[0], blocker[1], candidate, sign, plan.horizontal,
                                     frozenset((self.target,)), updates):
                        _wire_reroute.apply_shifts(project, updates)
                        pushed = True
                    else:
                        along = float(world_pos.x if plan.horizontal else world_pos.z)
                        if self._maybe_partial_jog(project, candidate, along, blocker):
                            # Already fully applied -- including this
                            # frame's own move, on whichever side turned
                            # out to be free -- and re-planned onto the
                            # newly freed segment. Nothing left to do
                            # this frame.
                            return

            if not pushed:
                # A housing/terminal hit, a wire that couldn't be pushed
                # out of the way and didn't qualify for a partial jog
                # either -- last legal position holds, unless the mouse
                # has clearly carried on past it (see _maybe_reroute_past).
                self._maybe_reroute_past(project, candidate)
                return

        if plan.horizontal:
            plan.p_near.z = candidate
            plan.p_far.z = candidate
        else:
            plan.p_near.x = candidate
            plan.p_far.x = candidate

        self._last_legal_lane = candidate

        collapsed_near = abs(candidate - before_fixed) < 1e-6
        collapsed_far = abs(candidate - after_fixed) < 1e-6

        if collapsed_near != self._collapsed_near and plan.layout_near is not None:
            plan.layout_near.objschematic.is_visible = not collapsed_near
            self._collapsed_near = collapsed_near

        if collapsed_far != self._collapsed_far and plan.layout_far is not None:
            plan.layout_far.objschematic.is_visible = not collapsed_far
            self._collapsed_far = collapsed_far

    def _maybe_reroute_past(self, project, candidate: float) -> None:
        """Once a push has failed outright, give up on this interactive
        segment-drag and ask the auto-router for a whole fresh path
        instead -- but only once the mouse has clearly carried on well
        past whatever stopped it (see the module docstring's push/shove
        section), not on the very first frame that fails.

        "Clearly past" is approximated as more than one and a half lane
        spacings beyond the last position this drag actually reached
        legally -- there's no cheap exact "far edge of the whole stuck
        stack" available here short of walking the entire failed push
        chain's own footprints, and this reads close enough live to be
        worth tuning from there rather than getting exactly right up
        front (confirmed 2026-09-22, Kevin: build this the easy way
        first).
        """
        if self._rerouted:
            return

        spacing = _wire_routing._lane_spacing()  # NOQA
        if abs(candidate - self._last_legal_lane) > spacing * 1.5:
            _wire_reroute.reroute_wire(project, self.target)
            self._rerouted = True

    def _maybe_partial_jog(self, project, candidate: float, along: float, blocker) -> bool:
        """See the module docstring's "partial move" section: when the
        blocking segment only covers PART of the dragged segment's own
        length, and the mouse's own position along the segment (*along*
        -- X for a horizontal segment, Z for a vertical one) sits
        outside that blocked stretch, split the drag in two instead of
        clamping the whole thing at the last legal lane: pin whichever
        side is still blocked exactly where it last legally was, let the
        side the mouse is actually over keep following it to *candidate*,
        and splice in the 2 new waypoints the resulting step needs.

        Returns True -- having already applied everything (the DB
        writes, and re-planning this drag onto the newly freed segment
        for the rest of the gesture) -- on success. Returns False, having
        changed nothing, when this doesn't apply: the blocked stretch
        touches neither end of the segment alone (a strict interior
        island -- both sides would be simultaneously free, which isn't
        the single clean two-way split this handles) or covers the
        whole segment, or the mouse isn't actually over the side that's
        clear.
        """
        plan = self._plan
        _wire, _idx, seg_p1, seg_p2 = blocker

        if plan.horizontal:
            near_c, far_c = float(plan.p_near.x), float(plan.p_far.x)
            b_lo, b_hi = min(seg_p1[0], seg_p2[0]), max(seg_p1[0], seg_p2[0])
        else:
            near_c, far_c = float(plan.p_near.z), float(plan.p_far.z)
            b_lo, b_hi = min(seg_p1[1], seg_p2[1]), max(seg_p1[1], seg_p2[1])

        d_lo, d_hi = min(near_c, far_c), max(near_c, far_c)

        # Only the stretch where the blocker actually overlaps THIS
        # segment is "where the other wire is" -- clip to the segment's
        # own extent.
        blo = max(b_lo, d_lo)
        bhi = min(b_hi, d_hi)

        tol = _wire_routing._LANE_EPS  # NOQA
        if blo >= bhi - tol:
            return False

        touches_low = blo <= d_lo + tol
        touches_high = bhi >= d_hi - tol

        # The jog itself is stood off from the blocker's own edge by a
        # full lane spacing, not placed flush against it -- flush would
        # put the jog's own perpendicular step in direct alignment with
        # whatever the blocking wire does right at that edge (its own
        # corner turning out perpendicular there is the common case),
        # instead of clearing it the same way every other parallel run
        # in this router keeps its distance (confirmed 2026-09-22,
        # Kevin: the first version placed it flush and that was wrong).
        spacing = _wire_routing._lane_spacing()  # NOQA

        if touches_low and not touches_high:
            pinned_point = plan.p_near if near_c <= far_c else plan.p_far
            free_point = plan.p_far if pinned_point is plan.p_near else plan.p_near
            boundary = bhi + spacing
            if boundary >= d_hi - tol:
                return False
            mouse_clear = along > boundary + tol
        elif touches_high and not touches_low:
            pinned_point = plan.p_far if near_c <= far_c else plan.p_near
            free_point = plan.p_near if pinned_point is plan.p_far else plan.p_far
            boundary = blo - spacing
            if boundary <= d_lo + tol:
                return False
            mouse_clear = along < boundary - tol
        else:
            # Covers the whole segment, or is a strict interior island.
            return False

        if not mouse_clear:
            return False

        old_lane = self._last_legal_lane
        near_is_pinned = pinned_point is plan.p_near

        if plan.horizontal:
            new_a = (boundary, old_lane)
            new_b = (boundary, candidate)
            free_target = (float(free_point.x), candidate)
        else:
            new_a = (old_lane, boundary)
            new_b = (candidate, boundary)
            free_target = (candidate, float(free_point.z))

        # The jog step itself (new_a -> new_b, the perpendicular run
        # between the pinned and freed lanes) is the only genuinely new
        # geometry here -- the pinned side is an untouched subset of
        # what was already legal at old_lane, and the freed side's own
        # outer connecting edge (to whichever of p_before/p_after sits
        # beyond it) was already confirmed legal for *candidate* at the
        # top of __call__.
        if _wire_routing.segment_blocked(project, new_a, new_b, ignore_wire=self.target):
            return False

        if _wire_routing.free_segment_blocked(
                project, new_b, free_target, ignore_wire=self.target) is not None:
            return False

        points, waypoints = _chain_points(self.target)
        wi = None
        for k, wp in enumerate(waypoints):
            if wp.db_id == plan.waypoint_near.db_id:
                wi = k
                break

        if wi is None:
            # Shouldn't happen -- self._plan's own waypoint row, looked
            # up moments ago -- but never splice against a position that
            # can't be found.
            return False

        interior = [(float(p.x), float(p.z)) for p in points[1:-1]]

        if near_is_pinned:
            near_final = (float(plan.p_near.x), float(plan.p_near.z))
            splice = [near_final, new_a, new_b, free_target]
        else:
            far_final = (float(plan.p_far.x), float(plan.p_far.z))
            splice = [free_target, new_b, new_a, far_final]

        new_interior = interior[:wi] + splice + interior[wi + 2:]

        _wire_reroute.set_waypoints(project, self.target, new_interior)

        new_points, new_waypoints = _chain_points(self.target)
        new_i = wi + 3 if near_is_pinned else wi + 1

        new_plan = _segment_plan_at(self.target, new_points, new_waypoints, new_i)
        if new_plan is None:
            # Shouldn't happen (the indices are derived directly from
            # what was just written), but never leave the drag holding
            # a stale plan if it somehow does.
            return False

        self._plan = new_plan
        self._collapsed_near = False
        self._collapsed_far = False
        self._last_legal_lane = candidate

        return True

    @_check_types.do
    def delete(self) -> None:
        """Commit whatever's currently live: a still-collapsed side's
        waypoint is deleted for real (it was only ever hidden during the
        drag) -- both the WireLayout marker (proper facade teardown when
        one was found at drag-arm; a raw delete_layouts_at() sweep as a
        defensive fallback otherwise -- mirrors
        ``wire_routing.reroute.reroute_wire``'s own blind sweep, used there
        because it never holds a live facade reference to begin with)
        and its backing pjt_points2d row. Anything not collapsed keeps
        its own already-live position -- no full reroute() call needed,
        the drag already left every point exactly where it should be.

        If this drag ended in a mid-gesture reroute instead (see
        :meth:`_maybe_reroute_past`), there's nothing left to commit --
        ``reroute_wire`` already replaced the whole path, waypoints and
        all, the moment it ran.
        """
        if self._rerouted:
            super().delete()
            return

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
