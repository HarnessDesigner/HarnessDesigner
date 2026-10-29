# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Skeleton-first wire routing -- the engine half of BUNDLE_DESIGN.md
section 2.7. Read that section (and 2.6, the ``pjt_wire_paths`` storage
design) in full before touching this module.

**What this module does:** given a wire, the section of it the user
grabbed (the stretch between two consecutive existing wire points, per
2.7's own "where the route starts" rule), an entry terminus (a bundle's
free end, or a transition's free branch) and, for every transition the
route subsequently reaches, either the branch to continue down or an
instruction to end at a splice there -- this module walks the skeleton,
computes the two mandatory guard waypoints, and writes the result into
``pjt_wire_paths`` (see :mod:`...database.project_db.pjt_wire_path`),
replacing the single straight segment between the grabbed points with
the detour, exactly as 2.7 specifies.

**Both views, one engine.** Every function here takes a ``view``
argument (``'3d'`` or ``'pegboard'``) and resolves the right per-view
point columns/accessors throughout -- a bundle's
``start_position3d_id``/``start_position_pegboard_id``, a branch's
``position3d_id``/``position_pegboard_id``, a transition's own centre
point, a wire's own start/stop, a housing's/terminal's own position for
the guard group-center rule, and which of ``pjt_points3d_table``/
``pjt_points_pegboard_table`` a new guard point gets inserted into. The
SKELETON TOPOLOGY being walked (which bundles, which transitions, which
branches) is identical regardless of view -- only the geometry differs,
per BUNDLE_DESIGN.md 2.7's own "A wire's route is topology... its
pjt_wire_path rows are generated FROM IT for each view" rule -- so the
same ``EnterBundle``/``EnterBranch``/``ContinueBranch``/``EndAtSplice``
objects, wrapping the very same ``PJTBundle``/``PJTTransitionBranch``
rows, drive a call for either view; only *grabbed_position*, the two
guard points, and which of the wire's own two independent per-view
point lists get spliced differ. The 3D and peg-board calls for one wire
are two separate, independent ``route_wire`` calls (this module's own
docstring originally scoped it to 3D only, deferring peg-board per
BUNDLE_DESIGN.md section 6's "one view at a time" rule -- that rule
covered getting the ENGINE right once before generalizing it, not a
permanent 3D-only restriction).

**Known gaps, deliberately left for a later pass (flagged, not hidden):**

1. **No shared-guard-across-wires lookup.** BUNDLE_PLACEMENT.md section
   2.7 ("Guards are shared per group") says every wire of one group
   (by housing, by terminal, or the free-wire-end centroid) at one bundle
   end should reference the SAME guard point, not one each. This module
   always creates a fresh guard point and never searches for an existing
   one to join -- there is no schema marker that identifies "this point
   is a guard" to search by (adding one is a real, if small, schema
   change -- both ``create_database`` locations, per MEMORY.md -- left
   for whoever builds the multi-wire reuse pass). Routing two wires into
   the same bundle end today gives each its own guard at the same
   computed position rather than one shared row. Applies identically to
   both views.
2. **Splice placement is caller-resolved.** This module accepts the exit
   splice's own connection point id directly (an :class:`EndAtSplice`
   hop) rather than picking a point on a ``PJTSplice`` itself -- the
   splice model's own rewrite (its module docstring's "accept models and
   a set number of splice points" TODO) is a separate, not-yet-scoped
   task; this module stays agnostic to it. The id passed must be a row
   in whichever view's point table the call's own ``view`` names.
3. **Splice inside a bundle's own span** (BUNDLE_DESIGN.md 2.4e's new
   splice-placement rule -- allowed when the bundle is not concentric-
   twisted) is not implemented -- only "splice inside the transition just
   reached" (:class:`EndAtSplice` consumed where a branch choice would
   otherwise go). Mid-bundle splice termination is a follow-up.
4. **A guard's live follow of its bundle end** (BUNDLE_PLACEMENT.md
   2.7's "driven by the bundle end through a point callback") is not
   wired up -- a guard is placed correctly once, at commit time, but does
   not yet move when the bundle end it belongs to is later dragged. Same
   two-step precedent as the rope-pull solver (written standalone, wired
   into the drag handlers the next day) -- this is that first step. Note
   that the peg-board view's own rope-pull solver (``rope_pull_handler.
   py``) already re-solves chains through a dragged waypoint -- once a
   guard is a real tagged point rather than a plain one, it should fall
   out of that same machinery rather than needing its own.
5. **Housing breakout point's "wire side" direction** is derived from
   the housing's own local -Z axis (``[0, 0, -1] @ housing.angle3d.
   matrix`` for the 3D view, ``@ housing.angle_pegboard.matrix`` for
   peg-board), by analogy with the one confirmed convention in this
   codebase for an analogous question -- ``PJTCavity.wire_position3d_id``
   's own docstring, "the cavity's own OBB... local -Z per the
   cavity-frame convention" -- applied one level up, to the housing
   instead of the cavity, and carried over unchanged to
   ``angle_pegboard`` on the strength of that mixin's own docstring
   ("mirroring Angle3DMixin exactly"). Neither is independently
   confirmed for the housing level; verify against a real housing before
   trusting it on one whose cavities are not all aligned with their own
   housing's frame the usual way.

Everything here is pure Python plus direct ``ptables`` calls -- no GL, no
mouse/canvas state -- so it can be exercised with a script against a real
or fake project DB, per this codebase's own established verification
convention (see MEMORY.md's rope-pull entries). It has not been run
against the live app; see the module docstring convention used
throughout BUNDLE_PLACEMENT.md/TRANSITION_DESIGN.md for what that means
here too.
"""

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ..geometry.point import Point as _Point
from .. import config as _config
from .. import check_types as _check_types
from . import wire_topology as _wire_topology
from ..objects import terminal as _terminal_obj
from ..objects import wire_layout as _wire_layout_obj


if TYPE_CHECKING:
    from ..database.project_db import pjt_point3d as _pjt_point3d
    from ..database.project_db import pjt_point_pegboard as _pjt_point_pegboard
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db.pjt_bases import ProjectTables as _ProjectTables
    from ..database.project_db.pjt_bundle import PJTBundle as _PJTBundle
    from ..database.project_db.pjt_transition_branch import PJTTransitionBranch as _PJTTransitionBranch
    from ..database.project_db.pjt_transition import PJTTransition as _PJTTransition
    from ..database.project_db.pjt_housing import PJTHousing as _PJTHousing
    from ..objects import wire as _wire_obj
    from ..objects import splice as _splice_obj
    from ..objects import wire_service_loop as _wsl_obj


_VIEWS = ('3d', 'pegboard')

# Which ptables point table a guard/new point gets inserted into, per view.

# The real pjt_transition_branches column name for a branch's own point,
# per view -- used for the reverse "is this point a branch" lookup.
_VIEW_BRANCH_COLUMN = {'3d': 'point3d_id', 'pegboard': 'point_pegboard_id'}


@_check_types.do
def check_view(view: str) -> None:
    """Public (not module-private) because handlers.wire_routing_drag
    calls this from outside this module."""
    if view not in _VIEWS:
        raise ValueError(f"view must be one of {_VIEWS!r}, got {view!r}")


@_check_types.do
def _points_table(ptables: "_ProjectTables", view: str) -> _Union["_pjt_point3d.PJTPoints3DTable", "_pjt_point_pegboard.PJTPointsPegboardTable"]:
    """The ptables point table for *view* -- ``pjt_points3d_table`` or
    ``pjt_points_pegboard_table``.
    """
    check_view(view)
    if view == '3d':
        return ptables.pjt_points3d_table
    return ptables.pjt_points_pegboard_table


@_check_types.do
def _branch_point_id(branch: "_PJTTransitionBranch", view: str) -> bytes:
    """*branch*'s own position point id for *view*."""
    check_view(view)
    return branch.position3d_id if view == '3d' else branch.position_pegboard_id


@_check_types.do
def _transition_centre_point_id(transition: "_PJTTransition", view: str) -> bytes:
    """*transition*'s own centre point id for *view*."""
    check_view(view)
    return transition.position3d_id if view == '3d' else transition.position_pegboard_id


@_check_types.do
def _wire_end_point(wire_db: "_pjt_wire.PJTWire", is_start: bool, view: str) -> _Point:
    """*wire_db*'s own start/stop ``Point`` for *view*."""
    check_view(view)
    if view == '3d':
        return wire_db.start_position3d if is_start else wire_db.stop_position3d

    return wire_db.start_position_pegboard if is_start else wire_db.stop_position_pegboard


class EnterBundle:
    """Entry terminus: a bundle's own free end.

    :param bundle: The bundle being entered.
    :param point: The actual ``Point`` of whichever of the bundle's own
        ends is free and being entered -- not a 'start'/'stop' label.
    """

    @_check_types.do
    def __init__(self, bundle: "_PJTBundle", point: _Point):
        self.bundle = bundle
        self.point = point


class EnterBranch:
    """Entry terminus: a transition's own free branch, with no bundle
    plugged into it -- the route enters the transition directly.

    :param branch: The free branch being entered.
    """

    @_check_types.do
    def __init__(self, branch: "_PJTTransitionBranch"):
        self.branch = branch


class ContinueBranch:
    """A hop choice: at the transition just reached, continue the route
    down this branch (must belong to that same transition). If the
    branch already has a bundle attached, the walk continues down it
    automatically; if the branch is free, the route ends there.

    :param branch: The branch to continue down.
    """

    @_check_types.do
    def __init__(self, branch: "_PJTTransitionBranch"):
        self.branch = branch


class EndAtSplice:
    """A hop choice: at the transition just reached, end the route here
    by attaching to a splice located inside that transition (the
    BUNDLE_DESIGN.md 2.4e splice-placement rule), rather than continuing
    down another branch.

    :param point_id: The splice's own connection point -- a row id in
        whichever view's point table (``pjt_points3d``/
        ``pjt_points_pegboard``) the enclosing :func:`route_wire` call's
        own ``view`` names. Which of the splice's own points that is is
        resolved by the caller (see this module's own docstring, gap 2).
    """

    @_check_types.do
    def __init__(self, point_id: bytes):
        self.point_id = point_id


@_check_types.do
def guard_distance(diameter: float) -> float:
    """The shared standoff-distance floor BUNDLE_DESIGN.md 2.7 defines
    for both a wire guard's distance from the bundle end it attaches to,
    and (reused as the housing breakout point's own lower clamp) a
    housing breakout point's distance from the back of the housing: the
    larger of a configured minimum and a configured multiple of
    *diameter* (a bundle's own diameter, or a free branch's own catalog
    diameter when there is no bundle -- see the callers below). View-
    independent: a bundle's physical diameter does not change per view.
    """
    cfg = _config.Config.bundle.routing
    return max(cfg.guard_distance_min_mm, cfg.guard_distance_diameter_multiple * diameter)


@_check_types.do
def _centroid(points: list[_Point]) -> np.ndarray:
    """Plain centroid of *points* -- used both for a housing breakout
    point's cavity-point centroid and (degenerate, single/zero-member
    case covered by the callers) a guard's free-group centroid.
    """
    if not points:
        raise ValueError('need at least one point')

    acc = np.zeros(3, dtype=np.float64)
    for p in points:
        acc += p.as_numpy

    return acc / len(points)


@_check_types.do
def _bundle_end_direction(bundle: "_PJTBundle", end_point: _Point, view: str) -> np.ndarray:
    """The unit vector pointing OUTWARD from *bundle*'s own end
    (*end_point*, the actual Point -- not a 'start'/'stop' label),
    continuing the direction of its own last section there -- the
    direction a wire guard's stub should travel in, per BUNDLE_PLACEMENT.md
    section 12's 2026-10-10 fix ("the stub should travel in the same
    direction the bundle is", superseding the group-center-based guard
    direction below for the bundle-end case specifically).

    The "last section" is the one between *end_point* and whichever point
    sits next to it: the nearest interior waypoint if the bundle has any
    at that end, else the bundle's OTHER end (a bundle with no waypoints
    at all is just the one straight section between its two ends).
    """
    check_view(view)

    start_point = bundle.start_position3d if view == '3d' else bundle.start_position_pegboard

    if end_point is start_point:
        other_point = bundle.stop_position3d if view == '3d' else bundle.stop_position_pegboard
        waypoints = bundle.waypoints3d if view == '3d' else bundle.waypoints_pegboard
        adjacent = waypoints[0].point if waypoints else other_point
    else:
        other_point = start_point
        waypoints = bundle.waypoints3d if view == '3d' else bundle.waypoints_pegboard
        adjacent = waypoints[-1].point if waypoints else other_point

    direction = end_point.as_numpy - adjacent.as_numpy
    length = float(np.linalg.norm(direction))

    if length < 1e-9:
        # Degenerate: the end coincides with its own adjacent point (a
        # zero-length bundle/section -- not expected, but guarded rather
        # than dividing by zero).
        return np.array([1.0, 0.0, 0.0])

    return direction / length


@_check_types.do
def compute_guard_position(
    bundle_end: _Point, group_center: np.ndarray, diameter: float,
    direction_override: np.ndarray | None = None,
) -> _Point:
    """A guard's position, :func:`guard_distance` (*diameter*) out from
    *bundle_end*.

    When *direction_override* is given (the bundle's own outward end
    tangent -- see :func:`_bundle_end_direction`), the guard continues
    straight out along it, so the stub leaving the bundle/branch travels
    in the SAME direction the bundle itself does there, before anything
    about the wire's own remaining path comes into play.

    Otherwise (no bundle at this terminus -- a bare free branch, which
    has no "bundle direction" of its own) falls back to
    BUNDLE_PLACEMENT.md 2.7's original rule: along the line from
    *group_center* to *bundle_end*. *group_center* is a plain world-space
    vector (not a live ``Point``): this is a one-shot placement, not a
    thing the guard stays bound to (see this module's own docstring, gap
    4) -- so there is nothing to hold a reference to.
    """
    end_pos = bundle_end.as_numpy

    if direction_override is not None:
        length = float(np.linalg.norm(direction_override))
        direction = direction_override if length >= 1e-9 else None
    else:
        direction = None

    if direction is None:
        direction = group_center - end_pos
        length = float(np.linalg.norm(direction))

        if length < 1e-9:
            # Degenerate: the group's center coincides with the bundle end
            # itself (not expected in the normal single-wire case -- see
            # the module docstring's gap 1 -- but guarded rather than
            # dividing by zero). Falls back to an arbitrary horizontal
            # direction so the guard still lands somewhere sane instead of
            # raising.
            direction = np.array([1.0, 0.0, 0.0])
            length = 1.0

    unit = direction / length
    guard_pos = end_pos + unit * guard_distance(diameter)

    return _Point(float(guard_pos[0]), float(guard_pos[1]), float(guard_pos[2]))


@_check_types.do
def guard_points_at(ptables: "_ProjectTables", view: str, point_id: bytes) -> list[bytes]:
    """Every guard point sitting immediately next to *point_id* (usually
    a bundle's own start/stop point -- what actually moved) in some
    wire's route for *view*, de-duplicated.

    No schema marker is needed for this (user, 2026-10-10): a guard is
    simply whichever route point is next to *point_id*, one index up or
    down, that is NOT itself part of a bundle's own span (no ``bundle_id``
    tag -- which also rules out *point_id* being an ordinary interior
    bundle waypoint rather than a true end, and rules out the OTHER
    direction's neighbor when *point_id* is the first/last point of a
    wire's own route). This is only ever run once per drag, not per
    frame of anything else, so a plain per-wire scan is fine -- no
    caching, no stored "is this a guard" flag.

    Callers move each returned point by the same delta they just moved
    *point_id* by -- the whole of BUNDLE_PLACEMENT.md section 12's "only
    movable when the bundle moves" rule.
    """
    paths_table = ptables.pjt_wire_paths_table
    guard_ids: list[bytes] = []
    seen: set = set()

    for wire_id in paths_table.wire_ids_for_point(view, point_id):
        ordered = paths_table.for_wire(wire_id, view)
        point_ids = [row.point_id for row in ordered]

        try:
            idx = point_ids.index(point_id)
        except ValueError:
            continue

        for neighbor_idx in (idx - 1, idx + 1):
            if neighbor_idx < 0 or neighbor_idx >= len(ordered):
                continue

            neighbor_row = ordered[neighbor_idx]
            if neighbor_row.bundle_id is not None:
                continue  # still inside a bundle's own span -- not a guard

            if neighbor_row.point_id not in seen:
                seen.add(neighbor_row.point_id)
                guard_ids.append(neighbor_row.point_id)

    return guard_ids


@_check_types.do
def is_guard_point(ptables: "_ProjectTables", view: str, point_id: bytes) -> bool:
    """Whether *point_id* is itself a guard waypoint in some wire's
    route for *view* -- the direct lock check for a ``WireLayout``'s own
    ``can_drag()`` (BUNDLE_PLACEMENT.md section 12: a guard cannot be
    dragged directly). Mirrors :func:`guard_points_at`'s own neighbor
    check from the other point's side: *point_id* carries no ``bundle_id``
    tag of its own, but sits immediately next to a point that does, in
    the same wire's route.
    """
    paths_table = ptables.pjt_wire_paths_table

    for wire_id in paths_table.wire_ids_for_point(view, point_id):
        ordered = paths_table.for_wire(wire_id, view)
        point_ids = [row.point_id for row in ordered]

        try:
            idx = point_ids.index(point_id)
        except ValueError:
            continue

        if ordered[idx].bundle_id is not None:
            continue  # part of a bundle's own span itself, not a guard

        for neighbor_idx in (idx - 1, idx + 1):
            if 0 <= neighbor_idx < len(ordered) and ordered[neighbor_idx].bundle_id is not None:
                return True

    return False


@_check_types.do
def reposition_guards_for_bundle_end(ptables: "_ProjectTables", bundle: "_PJTBundle", end_position: _Point, view: str) -> None:
    """Move every guard at *bundle*'s own end (*end_position*, the actual
    Point -- not a 'start'/'stop' label) to where it belongs NOW -- call
    whenever something changes the bundle's SHAPE near that end (the end
    itself moved independently of the rest of the bundle -- an attached
    transition was dragged -- or the bundle's own nearest waypoint there
    moved), not just its position: a plain rigid translation of the whole
    bundle (``drag_handlers.editor_3d.bundle.Bundle``'s own whole-body
    drag) keeps every direction unchanged and needs no recompute, only a
    matching delta -- this is for every OTHER case, where the end's own
    outward tangent (:func:`_bundle_end_direction`) can have changed too,
    not just its position.

    Safe (and cheap enough -- user, 2026-10-10: "not something where the
    calculation gets done over and over again") to call unconditionally
    on every drag frame that could matter; a no-op when *end_position* has
    no guards at all.
    """
    check_view(view)

    if view == '3d':
        start_id, stop_id = bundle.start_position3d_id, bundle.stop_position3d_id
    else:
        start_id, stop_id = bundle.start_position_pegboard_id, bundle.stop_position_pegboard_id

    start_point = bundle.start_position3d if view == '3d' else bundle.start_position_pegboard
    end_point_id = start_id if end_position is start_point else stop_id

    direction = _bundle_end_direction(bundle, end_position, view)
    diameter = float(bundle.diameter)
    points_table = _points_table(ptables, view)

    for guard_id in guard_points_at(ptables, view, end_point_id):
        guard_point = points_table[guard_id].point
        target = compute_guard_position(end_position, np.zeros(3), diameter, direction)
        delta = target.as_numpy - guard_point.as_numpy
        guard_point += _Point(float(delta[0]), float(delta[1]), float(delta[2]))


@_check_types.do
def compute_housing_breakout_point(
    housing: "_PJTHousing", cavity_points: list[_Point], diameter: float, view: str = '3d',
) -> _Point:
    """BUNDLE_DESIGN.md 2.7's housing-breakout-point algorithm: centroid
    *C* of *cavity_points*, *R* = the furthest of them from *C*, pulled
    away from the housing (along its own local -Z -- see this module's
    docstring, gap 5) by ``max(sqrt(3) * R, guard_distance(diameter))``.

    *cavity_points* is every wire-side cavity point
    (``PJTCavity.wire_position3d``/``wire_position_pegboard``, matching
    *view*) common to whichever group of wires is joining a bundle right
    now -- gathering the right subset (ALL wires common to the housing,
    not just the ones in this bundle, per 2.7) is the caller's job; this
    function is pure geometry. *view* only selects which of the
    housing's own angle properties (``angle3d``/``angle_pegboard``)
    supplies the "local -Z" rotation.
    """
    check_view(view)
    center = _centroid(cavity_points)

    r = 0.0
    for p in cavity_points:
        dist = float(np.linalg.norm(p.as_numpy - center))
        if dist > r:
            r = dist

    distance = max(np.sqrt(3.0) * r, guard_distance(diameter))

    angle = housing.angle3d if view == '3d' else housing.angle_pegboard
    local_back = np.array([0.0, 0.0, -1.0])
    direction = local_back @ angle.matrix
    norm = float(np.linalg.norm(direction))
    if norm < 1e-9:
        direction = local_back
    else:
        direction = direction / norm

    breakout = center + direction * distance

    return _Point(float(breakout[0]), float(breakout[1]), float(breakout[2]))


@_check_types.do
def _branch_at_point(ptables: "_ProjectTables", point_id: bytes, view: str) -> _Union["_PJTTransitionBranch", None]:
    """Whether *point_id* (a row in *view*'s own point table) is a
    transition branch's own position -- the same query shape as
    ``handlers.transition_handler.is_bundle_end_free``, just returning
    the branch itself instead of a bool.
    """
    check_view(view)
    column = _VIEW_BRANCH_COLUMN[view]
    rows = ptables.pjt_transition_branches_table.select('id', **{column: point_id})
    if not rows:
        return None

    return ptables.pjt_transition_branches_table[rows[0][0]]


@_check_types.do
def _group_center_for_wire_point(
    sibling: _Union["_terminal_obj.Terminal", "_splice_obj.Splice", "_wsl_obj.WireServiceLoop", None],
    point: _Point,
    view: str,
) -> np.ndarray:
    """The guard group-center for the single wire being routed right
    now: the housing's own center if *sibling* is a seated Terminal; the
    terminal's own center if it is a free (cavity-less) Terminal; else
    *point*'s own position (the free/single-wire case, and also the case
    where *point* is an interior waypoint rather than a true wire end --
    *sibling* is ``None`` then, never consulted. See this module's
    docstring, gap 1, for why this never looks at any OTHER wire's own
    ends to form a real multi-wire centroid yet. *view* selects the
    housing's/terminal's own ``position3d``/``position_pegboard``.
    """
    check_view(view)

    if isinstance(sibling, _terminal_obj.Terminal):
        cavity = sibling.db_obj.cavity
        if cavity is not None:
            housing = cavity.housing
            pos = housing.position3d if view == '3d' else housing.position_pegboard
            return pos.as_numpy

        pos = sibling.db_obj.position3d if view == '3d' else sibling.db_obj.position_pegboard
        return pos.as_numpy

    return point.as_numpy


@_check_types.do
def _diameter_of_terminus(entry: _Union[EnterBundle, EnterBranch, "_PJTBundle", "_PJTTransitionBranch"]) -> float:
    """The diameter to drive :func:`guard_distance` with for whichever
    terminus *entry* names -- a bundle's own (wire-driven/branch-floor)
    diameter, or a free branch's own project-level diameter when there
    is no bundle there at all. View-independent (a bundle/branch's own
    diameter is a single project fact, not per-view).
    """
    if isinstance(entry, EnterBundle):
        return float(entry.bundle.diameter)
    if isinstance(entry, EnterBranch):
        return float(entry.branch.diameter)

    # A bare PJTBundle or PJTTransitionBranch, as route_wire's own walk
    # passes once it is past the initial entry (a far bundle end with no
    # transition, or a branch reached mid-walk with no bundle of its
    # own) -- both expose a plain .diameter property, so no further
    # isinstance split is needed here.
    return float(entry.diameter)


class RouteWalk:
    """Resumable version of the skeleton chain-walk -- lets an
    interactive session (the drag-and-drop UI, BUNDLE_PLACEMENT.md
    section 12) drive the engine ONE hop at a time, pausing at each
    transition reached (:attr:`pending_transition`) instead of requiring
    every hop to be known up front the way a single :func:`route_wire`
    call does. :func:`route_wire` itself is now a thin wrapper around
    this, for the already-resolved-hops-list case every existing
    caller/test uses -- its own behavior and signature are unchanged.

    Usage: construct with the entry terminus; while not
    :attr:`is_finished`, read :attr:`pending_transition` to know which
    transition needs a choice and call :meth:`choose` with it; once
    :attr:`is_finished`, call :meth:`commit` exactly once to write the
    result into ``pjt_wire_paths``.
    """

    @_check_types.do
    def __init__(
        self, ptables: "_ProjectTables", wire: "_wire_obj.Wire",
        grabbed_position: np.ndarray, entry: _Union[EnterBundle, EnterBranch], view: str,
    ):
        check_view(view)

        self._ptables = ptables
        self._wire = wire
        self._view = view
        self._points_table = _points_table(ptables, view)
        self._section_idx = _wire_topology.segment_index(wire, grabbed_position, view)  # same helper split_wire_at_point uses

        if view == 'pegboard':
            # Companion-view routing (wire_routing_drag._route_companion_view)
            # has no real click to constrain where the detour lands --
            # segment_index just picks whichever existing segment is
            # geometrically nearest the bundle/branch position, with no
            # awareness that this wire's own leading/trailing peg-board
            # interior points might be a terminal/cavity structural stub
            # (rope_pull_handler._structural_stub_ids) rather than ordinary
            # free slack. Splicing the detour BEFORE such a stub point (a
            # raw section_idx of 0, or len(existing interior)) pushes that
            # stub out of array position 0/-1 -- which defeats
            # rope_pull_handler._stub_boundary's own by-POSITION identity
            # check (it only ever reads old_ids[0]/old_ids[-1], never a
            # tag) -- and the stub then gets reconciled away as ordinary,
            # disposable slack the next time this wire's peg-board chain is
            # re-solved (the exact class of corruption _structural_stub_ids
            # was built to prevent, confirmed live 2026-10-13). A real
            # interactive drag can never land here on its own -- its own
            # eligibility precondition (WireRouteMixin._is_routing_eligible)
            # already forbids a grab touching the wire's true start/stop --
            # but nothing stops it from landing on the segment immediately
            # next to a stub either, so this clamp is unconditional here,
            # not companion-view-specific.
            from . import rope_pull_handler as _rope_pull_handler  # NOQA -- avoid a cycle at import time

            leading, trailing = _rope_pull_handler.stub_boundary_for_chain(ptables, wire.db_obj)
            interior_count = len(wire.db_obj.waypoints_pegboard)
            self._section_idx = max(leading, min(self._section_idx, interior_count - trailing))

        self._point_tags: dict[bytes, dict] = {}
        self._ordered: list[bytes] = []
        self._bundle = None
        self._current_point: _Union[_Point, None] = None
        self._branch = None
        self._exit_diameter = None
        # (bundle, point) when the entry/exit terminus is a bundle's own
        # end -- None for a bare branch or a splice, which have no
        # "bundle direction" of their own. Drives the guard's direction
        # (bundle's own outward tangent, see _bundle_end_direction) and
        # its guard_bundle_id/guard_end tags, set in _commit_route.
        self._entry_bundle_end: _Union[tuple["_PJTBundle", _Point], None] = None
        self._exit_bundle_end: _Union[tuple["_PJTBundle", _Point], None] = None
        self._finished = False

        if isinstance(entry, EnterBundle):
            self._bundle = entry.bundle
            self._current_point = entry.point
            self._entry_bundle_end = (self._bundle, self._current_point)
            self._add(self._current_point.db_id[:-2], bundle_id=self._bundle.db_id)
        elif isinstance(entry, EnterBranch):
            self._branch = entry.branch
            self._add(
                _branch_point_id(self._branch, view),
                transition_id=self._branch.transition_id, transition_branch_id=self._branch.db_id)
        else:
            raise TypeError('entry must be EnterBundle or EnterBranch')

        self._entry_diameter = _diameter_of_terminus(entry)
        self._advance()

    @_check_types.do
    def _add(self, point_id: bytes, **tags: int | bytes | None) -> None:
        self._ordered.append(point_id)
        d = self._point_tags.setdefault(point_id, {})
        for key, value in tags.items():
            if value is not None:
                d[key] = value

    @_check_types.do
    def _advance(self) -> None:
        """Auto-walk ``self._bundle`` (if any) to its far end, then
        either finish (a genuinely free end reached) or add the
        transition centre at ``self._branch`` and pause there, waiting
        for :meth:`choose`.
        """
        if self._bundle is not None:
            bundle = self._bundle
            start_point = bundle.start_position3d if self._view == '3d' else bundle.start_position_pegboard
            stop_point = bundle.stop_position3d if self._view == '3d' else bundle.stop_position_pegboard

            waypoint_ids = self._ptables.pjt_bundle_paths_table.point_ids(bundle.db_id, self._view)
            if self._current_point is not start_point:
                waypoint_ids = list(reversed(waypoint_ids))

            for point_id in waypoint_ids:
                self._add(point_id, bundle_id=bundle.db_id)

            far_point = stop_point if self._current_point is start_point else start_point
            far_point_id = far_point.db_id[:-2]

            far_branch = _branch_at_point(self._ptables, far_point_id, self._view)
            if far_branch is None:
                self._add(far_point_id, bundle_id=bundle.db_id)
                self._exit_diameter = _diameter_of_terminus(bundle)
                self._exit_bundle_end = (bundle, far_point)
                self._finished = True
                self._bundle = None
                return

            self._add(
                far_point_id, bundle_id=bundle.db_id,
                transition_id=far_branch.transition_id, transition_branch_id=far_branch.db_id)
            self._branch = far_branch
            self._bundle = None

        transition = self._branch.transition
        self._add(_transition_centre_point_id(transition, self._view), transition_id=transition.db_id)

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finished

    @property
    @_check_types.do
    def pending_transition(self) -> _Union["_PJTTransition", None]:
        """The transition currently awaiting a :meth:`choose` call, or
        ``None`` once :attr:`is_finished`."""
        return None if self._finished else self._branch.transition

    @property
    @_check_types.do
    def touched_bundles(self) -> list["_PJTBundle"]:
        """Every bundle this walk actually routed the wire through, in
        walk order, de-duplicated -- read from the ``bundle_id`` tags
        collected while walking (section 2.6), so the common case of
        entering directly onto a free end (no transition in the way)
        still returns that one bundle. Callers use this after
        :meth:`commit` to refresh each bundle's own wire-driven diameter
        (``handlers.bundle_diameter.refresh_diameter``).
        """
        bundles_table = self._ptables.pjt_bundles_table
        ids: list[bytes] = []
        seen = set()
        for tags in self._point_tags.values():
            bundle_id = tags.get('bundle_id')
            if bundle_id is not None and bundle_id not in seen:
                seen.add(bundle_id)
                ids.append(bundle_id)

        return [bundles_table[bundle_id] for bundle_id in ids]

    @_check_types.do
    def choose(self, hop: _Union[ContinueBranch, EndAtSplice]) -> None:
        """Resolve the hop at :attr:`pending_transition`. May finish the
        walk immediately (a free exit branch, or an
        :class:`EndAtSplice`), or may need another :meth:`choose` call if
        the chosen branch's own attached bundle leads to yet another
        transition (handled automatically via :meth:`_advance`).

        Raises ``RuntimeError`` if already :attr:`is_finished`,
        ``ValueError`` if the chosen branch does not belong to
        :attr:`pending_transition`.
        """
        if self._finished:
            raise RuntimeError('walk is already finished')

        transition = self._branch.transition

        if isinstance(hop, EndAtSplice):
            self._add(hop.point_id)
            self._exit_diameter = _diameter_of_terminus(self._branch)
            self._finished = True
            self._branch = None
            return

        if not isinstance(hop, ContinueBranch):
            raise TypeError('each hop must be ContinueBranch or EndAtSplice')

        next_branch = hop.branch
        if next_branch.transition_id != transition.db_id:
            raise ValueError('chosen branch does not belong to the transition just reached')

        next_bundle = next_branch.bundle
        branch_point = next_branch.position3d if self._view == '3d' else next_branch.position_pegboard

        # A branch's own point row carries the attached bundle's id too
        # (2.6: "a branch with a bundle plugged in always carries that
        # bundle's id") -- next_bundle must be resolved before this _add()
        # call, not after, or that tag is silently dropped.
        self._add(
            branch_point.db_id[:-2],
            bundle_id=(next_bundle.db_id if next_bundle is not None else None),
            transition_id=transition.db_id, transition_branch_id=next_branch.db_id)

        if next_bundle is None:
            self._exit_diameter = _diameter_of_terminus(next_branch)
            self._finished = True
            self._branch = None
            return

        # The branch's own point IS one of next_bundle's two end points
        # (the same shared row, by BUNDLE_DESIGN.md 2.6's point-sharing
        # design) -- no need to work out which one, just carry it over
        # directly as the walk's new current point.
        self._bundle, self._current_point = next_bundle, branch_point
        self._branch = None

        self._advance()

    @_check_types.do
    def commit(self) -> None:
        """Write the finished route into ``pjt_wire_paths``. Call
        exactly once, only once :attr:`is_finished`.
        """
        if not self._finished:
            raise RuntimeError('cannot commit an unfinished route walk')

        first_point = self._points_table[self._ordered[0]].point
        last_point = self._points_table[self._ordered[-1]].point

        _commit_route(
            self._ptables, self._wire, self._section_idx, self._view,
            entry_point=first_point, entry_diameter=self._entry_diameter,
            exit_point=last_point, exit_diameter=self._exit_diameter,
            skeleton_point_ids=self._ordered, point_tags=self._point_tags,
            entry_bundle_end=self._entry_bundle_end, exit_bundle_end=self._exit_bundle_end)


@_check_types.do
def route_wire(
    ptables: "_ProjectTables",
    wire: "_wire_obj.Wire",
    grabbed_position: np.ndarray,
    entry: _Union[EnterBundle, EnterBranch],
    hops: list,
    view: str = '3d',
) -> None:
    """Route *wire* into the skeleton, starting at *entry* and consuming
    *hops* (a list of :class:`ContinueBranch`/:class:`EndAtSplice`, one
    per transition the walk reaches, in order) until the route reaches a
    genuinely free end or an :class:`EndAtSplice` hop, then commits the
    result to ``pjt_wire_paths`` for *view* (``'3d'`` or ``'pegboard'``).
    A thin wrapper around :class:`RouteWalk` for callers that already
    have the complete hop sequence resolved; the interactive drag UI
    uses :class:`RouteWalk` directly instead, one hop at a time, since it
    doesn't know the later hops until the user clicks each one.

    Routing the SAME wire into the SAME skeleton edges for both views is
    two separate calls -- one per view -- since each view keeps its own
    independent ``pjt_wire_paths`` rows and its own grabbed-section index
    (see module docstring). The *entry*/*hops* objects themselves are
    view-agnostic (they wrap ``PJTBundle``/``PJTTransitionBranch`` rows,
    which carry both views' own points) and can be reused across both
    calls; only *grabbed_position* must be given in that call's own
    view's own world coordinates.

    *grabbed_position* is the world-space position used to find which
    existing section of *wire* (P(i), P(i+1)), IN *view*'S OWN POINT
    LIST, the drag started from, via ``handlers.wire_topology.
    segment_index`` -- exactly the "where the route starts" rule from
    BUNDLE_DESIGN.md 2.7.

    Raises ``ValueError`` if *hops* runs out before the walk reaches a
    free end (a transition was reached with no corresponding hop) or a
    chosen branch does not belong to the transition the walk is actually
    at; raises nothing on a merely "unusual but legal" route -- there is
    no dangling-wire/loop validation here beyond what 2.7 itself already
    enforces by construction (a route can only ever walk real skeleton
    edges).
    """
    walk = RouteWalk(ptables, wire, grabbed_position, entry, view)

    for hop in hops:
        if walk.is_finished:
            break
        walk.choose(hop)

    if not walk.is_finished:
        transition = walk.pending_transition
        raise ValueError(
            f'route reached transition {transition.db_id!r} with no hop supplied for it')

    walk.commit()


@_check_types.do
def _commit_route(
    ptables: "_ProjectTables", wire: "_wire_obj.Wire", section_idx: int, view: str,
    entry_point: _Point, entry_diameter: float,
    exit_point: _Point, exit_diameter: float,
    skeleton_point_ids: list[bytes], point_tags: dict,
    entry_bundle_end: _Union[tuple["_PJTBundle", _Point], None],
    exit_bundle_end: _Union[tuple["_PJTBundle", _Point], None],
) -> None:
    """Splice [entry guard, *skeleton_point_ids*, exit guard] into
    *wire*'s own *view* interior waypoint list at *section_idx* (see
    ``handlers.wire_topology.segment_index`` for what that index means
    against ``[start] + interior + [stop]``), preserving every OTHER
    interior point's own existing route tags (``pjt_wire_paths_table.
    set_route`` wholesale-replaces and drops tags -- see that method's
    own docstring) and applying *point_tags* to the newly-inserted ones.

    *entry_bundle_end*/*exit_bundle_end* are ``(bundle, end_point)`` when
    that terminus is a bundle's own end (``None`` for a bare branch or a
    splice, which have no bundle direction of their own) -- used to point
    each guard's stub straight out along the bundle's own end tangent
    (see :func:`_bundle_end_direction`) instead of toward the wire's own
    remaining path. Each guard also gets a real ``WireLayout`` marker, so
    it renders and behaves like any other waypoint.
    """
    wire_db = wire.db_obj
    paths_table = ptables.pjt_wire_paths_table
    points_table = _points_table(ptables, view)

    existing_rows = paths_table.for_wire(wire_db.db_id, view)
    existing_interior_ids = [row.point_id for row in existing_rows]
    old_tags = {
        row.point_id: {
            'bundle_id': row.bundle_id, 'concentric_id': row.concentric_id,
            'transition_id': row.transition_id, 'transition_branch_id': row.transition_branch_id,
        }
        for row in existing_rows
    }

    # P(i)/P(i+1) -- the wire's own two points bracketing the grabbed
    # section (section_idx indexes into [start] + interior + [stop], see
    # wire_topology.segment_index) -- needed only to find each side's
    # own sibling (Terminal/Splice), for the guard group-center rule.
    # Neither is otherwise touched: both stay exactly where they are,
    # per 2.7's "the wire's own points up to P(i) stay"/"P(i+1) onward
    # resume from there" rule -- only what sits BETWEEN them changes.
    is_p_i_start = section_idx == 0
    is_p_i1_stop = section_idx == len(existing_interior_ids)

    p_i_sibling = wire.start_sibling if is_p_i_start else None
    p_i1_sibling = wire.stop_sibling if is_p_i1_stop else None

    if is_p_i_start:
        p_i_point = _wire_end_point(wire_db, True, view)
    else:
        p_i_point = points_table[existing_interior_ids[section_idx - 1]].point

    if is_p_i1_stop:
        p_i1_point = _wire_end_point(wire_db, False, view)
    else:
        p_i1_point = points_table[existing_interior_ids[section_idx]].point

    entry_group_center = _group_center_for_wire_point(p_i_sibling, p_i_point, view)
    exit_group_center = _group_center_for_wire_point(p_i1_sibling, p_i1_point, view)

    entry_direction = (
        _bundle_end_direction(entry_bundle_end[0], entry_bundle_end[1], view)
        if entry_bundle_end is not None else None)
    exit_direction = (
        _bundle_end_direction(exit_bundle_end[0], exit_bundle_end[1], view)
        if exit_bundle_end is not None else None)

    entry_guard_point = compute_guard_position(
        entry_point, entry_group_center, entry_diameter, entry_direction)
    exit_guard_point = compute_guard_position(
        exit_point, exit_group_center, exit_diameter, exit_direction)

    entry_guard_row = points_table.insert(entry_guard_point.x, entry_guard_point.y, entry_guard_point.z)
    exit_guard_row = points_table.insert(exit_guard_point.x, exit_guard_point.y, exit_guard_point.z)

    # Route the wire through the guards BEFORE either gets its own
    # WireLayout marker (below) -- the view object's own diameter/color
    # (objects_3d/objects_pegboard WireLayout.__init__) are read ONCE at
    # construction from PJTWireLayout.attached_wires, which resolves via
    # pjt_wire_paths_table.wire_ids_for_point. Creating the marker first
    # and routing second left that lookup with nothing to find yet, so
    # every guard fell back to WireLayout.__init__'s own hardcoded
    # default (3.0mm plain gray plastic) instead of the wire's actual
    # part diameter/color, permanently -- nothing re-reads it later.
    detour = [entry_guard_row.db_id] + list(skeleton_point_ids) + [exit_guard_row.db_id]
    new_interior_ids = existing_interior_ids[:section_idx] + detour + existing_interior_ids[section_idx:]

    paths_table.set_route(wire_db.db_id, view, new_interior_ids)

    # Each guard gets a real WireLayout marker, like any other waypoint
    # (BUNDLE_DESIGN.md 2.7) -- so it renders and is reachable the same
    # way; whether it's a GUARD specifically (locked against a direct
    # drag, only moved by its bundle end) is derived on demand from the
    # route itself (see guard_points_at/is_guard_point), not stored here.
    layouts_table = ptables.pjt_wire_layouts_table
    mainframe = wire.mainframe
    for guard_row in (entry_guard_row, exit_guard_row):
        point_kwargs = {'point3d_id': guard_row.db_id} if view == '3d' else {'point_pegboard_id': guard_row.db_id}
        layout_db = layouts_table.insert(**point_kwargs)
        layout_obj = _wire_layout_obj.WireLayout(mainframe, layout_db)
        mainframe.project.add_wire_layout(layout_obj)

    new_rows = paths_table.for_wire(wire_db.db_id, view)
    new_tags_by_point = point_tags
    for row in new_rows:
        tags = new_tags_by_point.get(row.point_id) or old_tags.get(row.point_id)
        if not tags:
            continue

        row.bundle_id = tags.get('bundle_id')
        row.concentric_id = tags.get('concentric_id')
        row.transition_id = tags.get('transition_id')
        row.transition_branch_id = tags.get('transition_branch_id')
