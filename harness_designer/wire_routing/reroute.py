# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared "reroute one wire" transaction for the 2D schematic editor's
auto-router (see ``routing.py``) -- the single choke point every
caller (initial wire finalize, live drag rerouting, the release-time
overlap sweep, Auto Arrange's full-project pass) goes through to
replace a wire's interior 2D waypoints. Owns deleting the old waypoint
rows -- and any ``WireLayout`` handle anchored to one of them, via
``database/project_db/pjt_wire.py``'s ``delete_layouts_at`` -- inserting
the newly routed ones, and refreshing the live ``Wire`` object's
bindings, so callers never touch ``pjt_points2d_table`` directly.

Also owns resolving "every wire directly attached to this object" (used
by both the live per-frame drag hook and Auto Arrange) and the cheap
release-time overlap sweep that catches a wire elsewhere in the project
left crossing an object that was just moved.
"""

from typing import TYPE_CHECKING
import math

from . import routing as _wire_routing
from ..database.project_db import pjt_wire as _pjt_wire
from ..database.project_db import pjt_point2d as _pjt_point2d
from .. import config as _config
from .. import check_types as _check_types


Config = _config.Config.editor_schematic

if TYPE_CHECKING:
    from ..objects import project as _project
    from ..objects import wire as _wire_obj
    from ..objects import terminal as _terminal_obj
    from ..objects import splice as _splice_obj
    from ..objects import housing as _housing_obj


@_check_types.do
def on_wire_attached(project: "_project.Project", wire: "_wire_obj.Wire") -> None:
    """Call once, right after a fresh Terminal/Splice attach completes on
    either of *wire*'s ends -- ``objects.terminal.Terminal.add_wire``'s own
    internal ``set_sibling`` call for a terminal, or the explicit
    ``wire.set_sibling(splice, end)`` each splice-attach call site makes
    right after ``objects.splice.Splice.add_wire`` (``handlers.wire_snap
    .commit_snap``, and the ``_attach_splice``-shaped code in every
    editor's wire add-handler) -- covers a fresh attach regardless of
    which editor (3D, schematic, peg board) performed it, and regardless
    of whether it happens during the wire's own initial add session or
    much later (a dangling end dragged onto a terminal/splice separately).

    If *wire* just became fully connected (both ends now a real Terminal/
    Splice -- see :attr:`objects.wire.Wire.is_connected`), marks it
    visible in the schematic (``PJTWire.is_visible2d`` -- both wire-
    creation paths, ``objects.objects_3d.wire.Wire._start_from_terminal``/
    ``_start_from_splice`` and ``objects.objects_schematic.wire.Wire
    .start_add``, insert a brand-new wire row with this ``False``, and
    nothing else ever flips it back -- ``objects_schematic/base_schematic
    .py``'s ``BaseSchematic.__init__`` seeds ``_is_visible`` straight from
    it, and ``BaseVar.render`` skips drawing entirely while it's ``False``,
    so a wire stayed permanently invisible in the schematic regardless of
    connection state until this call sets it), routes its schematic path,
    and registers it with the schematic canvas, which otherwise never
    draws/picks an unconnected wire at all (see
    ``gl/canvas_schematic/canvas.py``'s ``Canvas.add_object``). A no-op if
    the wire isn't (yet) fully connected -- safe to call unconditionally
    from every attach call site, including the end that doesn't complete
    the connection.

    Deliberately NOT hooked into ``Wire.set_sibling`` itself -- that also
    runs during project-reload sibling-graph reconciliation
    (``Project._reconcile_wire_sibling_graph``), which must never re-route
    or re-touch the canvas for a wire whose path is already persisted.
    """
    if not wire.is_connected:
        return

    wire.db_obj.is_visible2d = True

    # A wire whose path the user placed by hand (see add_handlers.
    # editor_schematic.wire) keeps those points and only has the rest routed.
    # Read here, not passed in: Terminal.add_wire calls this itself, deep
    # inside the attach, where the add handler can't reach it.
    reroute_wire(project, wire, fixed_prefix=wire.route_prefix)
    wire.mainframe.editor2d.add_object(wire)


@_check_types.do
def _terminal_exit_stub_point(wire: "_wire_obj.Wire", end: str) -> tuple[float, float] | None:
    """If *wire*'s *end* ('start'/'stop') is attached to a Terminal, the
    world ``(x, z)`` point ``Config.layout.terminal_stub_length`` out
    from that end along the terminal's own wire-stub cylinder's real
    direction -- ``cylinder_start -> wire_position``, the same two
    already-housing-rotation-correct world points
    ``objects_schematic/terminal.py``'s ``Terminal`` itself renders that
    black cylinder between (the *only* place this direction is
    authoritatively defined -- deriving it independently from the
    housing's own angle would be duplicating that same math and risk
    drifting out of sync with it).

    A mandatory first/last waypoint any route must pass through, so a
    wire always leaves/arrives at a terminal running straight in the
    terminal's own direction for at least that distance before it's
    allowed to turn -- otherwise a wire departing a terminal at a hard
    right angle immediately can cut across a neighboring terminal's own
    wire attachment point.

    ``None`` if this end isn't attached to a Terminal at all (a splice
    has no fixed exit direction of its own), the terminal has more than
    one wire (see below), or the direction isn't resolvable yet (e.g. a
    bare terminal with no seated cavity).

    A terminal with more than one wire is a junction, not a single fixed
    exit, the moment it gains its second one (see ``objects.terminal.
    Terminal._make_room_for_second_wire``/``objects_schematic.terminal.
    Terminal.render``'s own ``wire_junction`` sphere) -- every wire on it
    shares the SAME ``wire_position2d``, so forcing each one through its
    own copy of this same mandatory straight run made them overlap each
    other along the whole stretch out to it (worse than before the
    junction point existed, not better) instead of just meeting there like
    a splice's own wires already do (a splice has no exit stub of its own
    either, for exactly this reason). None of a junction terminal's wires
    get a stub any more, the first (now shared) one included -- not only
    whichever arrived after the second.
    """
    from ..objects import terminal as _terminal

    sibling = wire.start_sibling if end == 'start' else wire.stop_sibling
    if not isinstance(sibling, _terminal.Terminal):
        return None

    if len(sibling.wires) > 1:
        return None

    term_schematic = sibling.objschematic

    # _cylinder_start/_wire_position are only ever set as INSTANCE
    # attributes, inside Terminal.__init__'s `if cavity is not None:`
    # branch (same branch that sets self._geometry, which DOES have a
    # class-level None default) -- a bare terminal (no seated cavity)
    # never gets them at all, so gate on _geometry first rather than
    # touching either directly, which would raise AttributeError.
    if term_schematic._geometry is None:  # NOQA
        return None

    cyl_start = term_schematic._cylinder_start  # NOQA
    wire_pos = term_schematic._wire_position  # NOQA

    dx = float(wire_pos.x) - float(cyl_start.x)
    dz = float(wire_pos.z) - float(cyl_start.z)
    if math.hypot(dx, dz) < 1e-6:
        return None

    stub_length = Config.layout.terminal_stub_length
    wire_x, wire_z = float(wire_pos.x), float(wire_pos.z)

    # Snapped to the dominant axis, NOT a general unit-vector scale
    # (dx / length, dz / length) -- a terminal's exit is always exactly
    # cardinal (the owning housing only ever rotates in 90 degree steps,
    # see PJTHousing._update_angle2d), so the non-moving axis should be
    # EXACTLY wire_pos's own coordinate, zero drift. The rotation math
    # that produced cyl_start/wire_pos in the first place accumulates
    # enough floating-point noise that the "should be zero" axis instead
    # comes out as a tiny (~1e-6) nonzero value -- small enough to be
    # invisible, but just large enough to clear routing._collapse's
    # own _EPS threshold, which then misreads this stub segment as not
    # actually horizontal/vertical and drops it as a false non-turn
    # (confirmed 2026-09-16 from a live capture: a stub's own z differed
    # from its terminal's by ~2.4e-6, _EPS is 1e-6). Snapping removes
    # that drift at the source instead of loosening the tolerance, which
    # would just mask smaller real diagonal cases elsewhere.
    if abs(dx) >= abs(dz):
        sign = 1.0 if dx >= 0.0 else -1.0
        return wire_x + sign * stub_length, wire_z

    sign = 1.0 if dz >= 0.0 else -1.0
    return wire_x, wire_z + sign * stub_length


def wire_ends(project: "_project.Project", wire: "_wire_obj.Wire") -> _wire_routing.WireEnds:
    """*wire*'s two true 2D ends, the terminal exit stub (if any) at each,
    and the splice/terminal-cylinder rects it's attached to -- what a
    routing frame needs to know about it.

    ``ignore_rects`` carries both the splices (:func:`~.routing.
    attached_splice_rects`) AND the terminal cylinders (:func:`~.routing.
    attached_terminal_cylinder_rects`) *wire* is directly attached to --
    :class:`~.routing.RoutingFrame` bakes every terminal's cylinder into
    its shared grid as a hard obstacle (see :func:`~.routing.
    _obstacle_rects`), same as it does housings/splices/notes, so a wire's
    own attach point -- which legitimately sits right on/at its own
    terminal's cylinder rect -- needs the same "un-paint just for my own
    search turn" treatment a splice-attached end already gets (see
    :meth:`~.routing.RoutingFrame.route`).
    """
    db_obj = wire.db_obj
    start = db_obj.start_position2d
    stop = db_obj.stop_position2d

    return _wire_routing.WireEnds(
        (float(start.x), float(start.z)), (float(stop.x), float(stop.z)),
        _terminal_exit_stub_point(wire, 'start'), _terminal_exit_stub_point(wire, 'stop'),
        _wire_routing.attached_splice_rects(project, wire)
        + _wire_routing.attached_terminal_cylinder_rects(project, wire))


def build_frame(project: "_project.Project", wires: list["_wire_obj.Wire"],
                pack_with: list["_wire_obj.Wire"] = ()):
    """One shared routing grid for *wires* (see
    :class:`~.routing.RoutingFrame`), to pass to :func:`reroute_wire` as
    ``frame`` for each of them -- or ``None`` if it can't be built (nothing
    to route, or the compiled search isn't available), in which case
    :func:`reroute_wire` simply routes each wire on its own.

    :param pack_with: Wires outside *wires* that sit on the same housing --
        the routes prefer to run right alongside these (and alongside each
        other as they settle); see :meth:`~.routing.RoutingFrame.__init__`."""
    if not wires:
        return None

    return _wire_routing.build_frame(
        project, {wire: wire_ends(project, wire) for wire in wires}, pack_with)


def shift_targets(waypoint_points: list, at_start: bool, updates: list[tuple[int, tuple[float, float]]]
                  ) -> list[tuple[object, float, float]]:
    """Turn a wire's *updates* -- ``(index into the wire's path with the
    moving end first, new (x, z))``, as :func:`~.routing.plan_shift` returns
    them -- into ``(waypoint Point, x, z)`` triples.

    *waypoint_points* is the wire's interior waypoint ``Point`` objects in
    stored order (start to stop). The planner numbers points from the MOVING
    end, so for a wire that moves at its stop end the numbering runs the
    other way.
    """
    count = len(waypoint_points)
    targets = []

    for at, (x, z) in updates:
        # path[0] is the moving end itself; path[1] is the first waypoint.
        if at_start:
            point = waypoint_points[at - 1]
        else:
            point = waypoint_points[count - at]

        targets.append((point, x, z))

    return targets


def apply_shifts(project: "_project.Project", targets: list[tuple[object, float, float]]) -> None:
    """Move every ``(waypoint Point, x, z)`` in *targets* -- across ALL the
    wires being shifted -- with a SINGLE database write.

    A ``Point``'s own callback writes its row and commits, and a commit costs
    the same (a few milliseconds: it waits for the disk) whether it carries
    one row or a hundred. So letting each moved waypoint write for itself
    made a drag pay one commit per waypoint per mouse move, on top of the
    housing's own. This does what ``PJTHousing._update_position2d`` does for
    the terminals it carries: one ``batch_update`` for all of them, then the
    points move with the per-point write switched off (their callbacks -- the
    ones that redraw -- still fire).
    """
    if not targets:
        return

    rows = [[float(x), float(z), point.db_id[:-2]] for point, x, z in targets]
    project.ptables.pjt_points2d_table.batch_update(['x', 'y'], rows)

    _pjt_point2d.PJTPoint2D._skip_db_write = True
    try:
        for point, x, z in targets:
            with point:
                point.x = x
                point.z = z

            # Callbacks are suppressed inside ``with point:`` and the caller
            # is responsible for firing them afterwards (see reroute_wire).
            point._process_callbacks()  # NOQA
    finally:
        _pjt_point2d.PJTPoint2D._skip_db_write = False


def follow_moved(project: "_project.Project", obj, wires: list["_wire_obj.Wire"],
                 delta: tuple[float, float]) -> list["_wire_obj.Wire"]:
    """Let the wires of a housing that has just moved by *delta* follow it
    without a new route wherever their existing path can (see
    :func:`~.routing.plan_shift`), and return the ones that can't -- those
    still need :func:`reroute_wire`. A route is worth keeping until it
    collides: nothing is searched here.

    Only a housing has terminals with exit stubs to follow; for anything else
    (a splice, a lone terminal) every wire is returned.

    :param wires: The wires attached to *obj* (see :func:`wires_attached_to`),
        in the order they should be placed -- shortest first.
    """
    from ..objects import housing as _housing

    if not isinstance(obj, _housing.Housing):
        return list(wires)

    terminals = {cavity.terminal for cavity in obj.cavities if cavity.terminal is not None}

    jobs = []
    at_start = {}
    rest = []

    for wire in wires:
        starts_here = wire.start_sibling in terminals
        stops_here = wire.stop_sibling in terminals

        if starts_here == stops_here:
            # Both ends on this housing (the whole path moves) or, oddly, neither.
            rest.append(wire)
            continue

        end = 'start' if starts_here else 'stop'
        stub = _terminal_exit_stub_point(wire, end)
        if stub is None:
            rest.append(wire)
            continue

        objs = wire.objschematic
        path = [(float(p.x), float(p.z)) for p in [objs._p1] + list(objs._waypoint_points) + [objs._p2]]  # NOQA
        if not starts_here:
            path.reverse()

        out_x = stub[0] - path[0][0]
        out_z = stub[1] - path[0][1]

        if abs(out_x) >= abs(out_z):
            axis = 0
            sign = 1 if out_x >= 0.0 else -1
        else:
            axis = 1
            sign = 1 if out_z >= 0.0 else -1

        jobs.append(_wire_routing.ShiftJob(wire, path, axis, sign, math.hypot(out_x, out_z)))
        at_start[wire] = starts_here

    plan = _wire_routing.plan_shift(project, jobs, delta) if jobs else {}

    targets = []
    for job in jobs:
        updates = plan[job.wire]

        if updates is None:
            rest.append(job.wire)
            continue

        targets.extend(shift_targets(job.wire.objschematic._waypoint_points, at_start[job.wire], updates))  # NOQA

    # One write for the whole batch, not one commit per waypoint.
    apply_shifts(project, targets)

    # Back into the order the caller gave (shortest first).
    order = {wire: index for index, wire in enumerate(wires)}
    rest.sort(key=order.__getitem__)

    return rest


@_check_types.do
def _skipped_stub_segments(skip_wires) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The fixed terminal-exit stubs (true end -> stub point) of every wire
    in *skip_wires*, as ``((x1, z1), (x2, z2))`` segments.

    A skipped (unsettled) sibling's current path is deliberately ignored,
    but the short straight run out of each of its terminals is mandatory
    geometry that will exist whatever route it ends up with -- a wire
    routed before it must keep out of that lane, or it can leave the
    sibling's own start boxed in (terminals are only a few mm apart).
    """
    segments = []

    for skipped in skip_wires:
        db_obj = skipped.db_obj

        for end, point in (('start', db_obj.start_position2d), ('stop', db_obj.stop_position2d)):
            stub = _terminal_exit_stub_point(skipped, end)
            if stub is not None:
                segments.append(((float(point.x), float(point.z)), stub))

    return segments


def add_waypoint(project: "_project.Project", wire: "_wire_obj.Wire", x: float, z: float, idx: int):
    """Append a new interior 2D waypoint at ``(x, z)`` as index *idx* of
    *wire*'s path, with its own WireLayout handle -- every interior bend has
    one, so it is a real selectable/draggable object. Returns the new point
    row. The caller refreshes the wire (``objschematic.refresh_waypoints()``)
    once it is done adding."""
    from ..objects import wire_layout as _wire_layout

    ptables = project.ptables

    point = ptables.pjt_points2d_table.insert(x, z, wire_id=wire.db_obj.db_id, idx=idx)

    layout_db = ptables.pjt_wire_layouts_table.insert(point2d_id=point.db_id)
    layout_obj = _wire_layout.WireLayout(wire.mainframe, layout_db)
    project.add_wire_layout(layout_obj)

    return point


def remove_waypoint(project: "_project.Project", point) -> None:
    """Delete a waypoint row *point* (a ``PJTPoint2D``) and its WireLayout.

    ``wire_id`` has to be cleared first: it counts as a reference on its own,
    and ``PJTPoint2D.delete()`` silently refuses while the point is still
    referenced (see the note in :func:`reroute_wire`). The caller refreshes
    the wire afterwards."""
    _pjt_wire.delete_layouts_at(project.ptables.pjt_wire_layouts_table, 'point2d_id', point.db_id)

    point.wire_id = None
    point.delete()


def set_waypoints(project: "_project.Project", wire: "_wire_obj.Wire",
                  waypoints: list[tuple[float, float]]) -> None:
    """Reconcile *wire*'s interior 2D waypoint rows to match *waypoints*
    exactly, in order -- the shared "make the DB match this exact path"
    tail of :func:`reroute_wire`, factored out so a caller that already
    knows the exact path it wants (not one that needs A* to find it) can
    reuse the same reconciliation instead of hand-rolling its own
    delete/insert bookkeeping. Used by :func:`reroute_wire` itself, and
    by ``drag_handlers.editor_schematic.wire``'s own partial-move jog,
    which inserts 2 new waypoints mid-chain by hand (splitting a segment
    that's only partly blocked) rather than rerouting.

    Reuses whatever old waypoint rows it can -- one DB write per point
    moved, no delete/insert at all -- and only deletes/inserts the
    DIFFERENCE in count against *waypoints*' own length. Positional, not
    by identity: row *k* is simply repointed at ``waypoints[k]``,
    whatever it meant before, so a caller that wants a specific existing
    point left exactly where it is must include that point's own
    current position in *waypoints* at the same slot it already
    occupies -- this doesn't try to detect or preserve "the same
    logical bend" on its own.
    """
    ptables = project.ptables
    db_obj = wire.db_obj

    old_waypoints = list(db_obj.waypoints2d)
    common = min(len(old_waypoints), len(waypoints))

    from ..objects import wire_layout as _wire_layout

    layouts_table = ptables.pjt_wire_layouts_table

    # See reroute_wire's own identical block for why every write here is
    # unconditional (even a "no-op" reuse) and why the explicit
    # _process_callbacks() call after `with point:` is required, not
    # optional.
    for old_point, (x, z) in zip(old_waypoints[:common], waypoints[:common]):
        point = old_point.point
        with point:
            point.x = x
            point.z = z
        point._process_callbacks()  # NOQA

        if layouts_table.for_point2d_id(old_point.db_id) is None:
            layout_db = layouts_table.insert(point2d_id=old_point.db_id)
            layout_obj = _wire_layout.WireLayout(wire.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

    if len(waypoints) > len(old_waypoints):
        for i in range(common, len(waypoints)):
            x, z = waypoints[i]
            add_waypoint(project, wire, x, z, i)

    elif len(waypoints) < len(old_waypoints):
        for point in old_waypoints[common:]:
            remove_waypoint(project, point)

    wire.objschematic.refresh_waypoints()


def _axis_aligned(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Whether *a* -> *b* is a real horizontal or vertical run (not a point)."""
    dx = abs(a[0] - b[0])
    dz = abs(a[1] - b[1])

    if dx < 1e-6 and dz < 1e-6:
        return False

    return dx < 1e-6 or dz < 1e-6


@_check_types.do
def reroute_wire(project: "_project.Project", wire: "_wire_obj.Wire",
                 skip_wires=frozenset(), frame=None, fixed_prefix=None) -> None:
    """Recompute *wire*'s orthogonal 2D path and reconcile its interior
    waypoint rows against the result -- moves whatever old waypoints can
    be reused (one DB write per point moved, no delete/insert at all)
    and only deletes/inserts the DIFFERENCE in count when the new path
    has more or fewer bends than the current one, never the whole set.
    Always runs, even when the new path needs zero interior waypoints,
    so stale bindings never linger.

    Routes between each end's own :func:`_terminal_exit_stub_point`
    (falling back to the end itself when not attached to a Terminal)
    rather than directly between the wire's own true start/stop --
    guarantees the mandatory straight terminal-exit run without needing
    A*/the compressed grid to know anything about it, since a stub leg
    is a straight cardinal-direction hop by construction. The stub
    points aren't unconditionally kept as real waypoints, though --
    :func:`routing._collapse` runs over the FULL point list
    (true start, stub(s), routed interior bends, true stop) so a stub
    that doesn't actually represent a turn (the common case: a route
    that continues straight past it, or needs no bend at all) is
    dropped, same as any other non-turning node.

    Whenever an end has a stub, its true endpoint is passed to
    :func:`routing.route` as that end's anchor -- forbids the interior
    route from immediately folding back over that already-placed stub
    segment (see ``routing.route``'s own ``start_anchor``/``stop_anchor``
    docs), which nothing else here would otherwise catch: A* itself
    physically can't retrace its own interior (a simple grid path can't
    revisit a node), so the stub seam -- glued on before/after the A*
    call, invisible to it -- is the only place a wire could ever
    literally double back over itself.

    :param skip_wires: See :func:`routing._wire_segments` -- forwarded
        unchanged to :func:`routing.route`.
    :param frame: A :class:`~.routing.RoutingFrame` (see :func:`build_frame`)
        that *wire* is part of. When given, the route comes from it -- one
        grid shared by the whole batch, which also tracks which of the
        batch are settled -- and *skip_wires* isn't needed.
    :param fixed_prefix: The first interior waypoints of the path, already
        placed by hand, as ``(x, z)`` in order from the start end (a terminal
        exit stub included, if the user's path starts with one). They are kept
        exactly, whatever their angle, and only the rest of the path -- from the
        last of them to the stop end -- is routed. Not used with *frame*.
    """
    ptables = project.ptables
    db_obj = wire.db_obj

    start = db_obj.start_position2d
    stop = db_obj.stop_position2d

    start_xz = (float(start.x), float(start.z))
    stop_xz = (float(stop.x), float(stop.z))

    start_stub = _terminal_exit_stub_point(wire, 'start')
    stop_stub = _terminal_exit_stub_point(wire, 'stop')

    if fixed_prefix:
        fixed_prefix = [(float(x), float(z)) for x, z in fixed_prefix]
        own_path = [start_xz] + fixed_prefix

        route_start = own_path[-1]

        # Fold-back guard only makes sense against a real cardinal run.
        start_anchor = own_path[-2] if _axis_aligned(own_path[-2], route_start) else None

        own_lanes = list(zip(own_path, own_path[1:]))
        if stop_stub is not None:
            own_lanes.append((stop_xz, stop_stub))
    else:
        route_start = start_xz if start_stub is None else start_stub

        start_anchor = None if start_stub is None else start_xz

        # The wire's own stubs count as lanes too (see RoutingFrame.route).
        own_lanes = []
        if start_stub is not None:
            own_lanes.append((start_xz, start_stub))
        if stop_stub is not None:
            own_lanes.append((stop_xz, stop_stub))

    route_stop = stop_xz if stop_stub is None else stop_stub

    if frame is not None and wire in frame:
        interior = frame.route(wire)
    else:
        interior = _wire_routing.route(
            project, route_start, route_stop, ignore_wire=wire, skip_wires=skip_wires,
            start_anchor=start_anchor,
            stop_anchor=None if stop_stub is None else stop_xz,
            extra_segments=_skipped_stub_segments(skip_wires) + own_lanes)

    if fixed_prefix:
        full_path = [start_xz] + fixed_prefix + interior
    else:
        full_path = [start_xz]
        if start_stub is not None:
            full_path.append(start_stub)
        full_path.extend(interior)

    if stop_stub is not None:
        full_path.append(stop_stub)
    full_path.append(stop_xz)

    # A waypoint the wire runs straight through is no bend at all -- and one
    # the user placed can be exactly that once the routed tail joins it (the
    # last point placed, with the route carrying on the same way) -- so it goes.
    waypoints = _wire_routing._collapse(full_path)  # NOQA

    # Reposition whatever overlaps in place rather than tearing everything
    # down and inserting fresh rows (new ids, new Point objects, any
    # WireLayout re-anchored) and only add/remove the difference in
    # count -- see set_waypoints's own docstring.
    set_waypoints(project, wire, waypoints)


@_check_types.do
def is_junction_wire(wire: "_wire_obj.Wire") -> bool:
    """Whether either of *wire*'s own ends is attached to a Terminal that
    currently has more than one wire -- a schematic-view wire-junction
    (see ``objects.terminal.Terminal._make_room_for_second_wire``).

    Used to route/settle a junction terminal's own wires FIRST in any
    same-batch multi-wire routing pass, before every other wire, so they
    claim their lanes around the junction's own (pushed-out)
    ``wire_position2d`` and everything else routes around the result --
    rather than a junction's own wires and some unrelated neighbour's wire
    settling in whatever order they happened to be given in and landing
    their own 90-degree turns on top of each other (confirmed 2026-09-22,
    Kevin, from a live capture: two such wires' bends coincided exactly).
    See ``drag_handlers.editor_schematic.generic.Generic``'s own
    ``_attached`` sort and ``objects_schematic.auto_arrange.auto_arrange``'s
    own wire loop, both of which sort on this first.
    """
    from ..objects import terminal as _terminal

    for sibling in (wire.start_sibling, wire.stop_sibling):
        if isinstance(sibling, _terminal.Terminal) and len(sibling.wires) > 1:
            return True

    return False


@_check_types.do
def crow_flies_distance(wire: "_wire_obj.Wire") -> float:
    """Straight-line world distance between *wire*'s own true start and
    stop 2D points -- used to order a same-frame multi-wire routing
    batch shortest-first (see ``drag_handlers.editor_schematic.generic
    .Generic``): the shortest, most-constrained run gets first pick of
    the available lanes while its longer siblings are still unsettled
    (and so still excluded as obstacles for it -- see
    :func:`routing._wire_segments`'s own ``skip_wires``) rather than the
    other way around.
    """
    start = wire.db_obj.start_position2d
    stop = wire.db_obj.stop_position2d
    return math.hypot(float(stop.x) - float(start.x), float(stop.z) - float(start.z))


@_check_types.do
def wires_attached_to(obj) -> list["_wire_obj.Wire"]:
    """Every wire directly attached to *obj* -- a ``Terminal``/``Splice``
    exposes ``.wires`` directly; a ``Housing`` has none of its own, so
    it's built from every seated terminal across its cavities (those
    already have correct live positions by the time this is called each
    drag frame -- ``objects_schematic/housing.py``'s ``Housing._update_position``/
    ``_update_angle`` cascade to every child first). Anything else
    (a bare wire segment/handle, dragged through its own dedicated
    segment-drag interaction, not this generic path) returns an empty
    list.
    """
    from ..objects import terminal as _terminal
    from ..objects import splice as _splice
    from ..objects import housing as _housing

    if isinstance(obj, (_terminal.Terminal, _splice.Splice)):
        return list(obj.wires)

    if isinstance(obj, _housing.Housing):
        result = []
        for cavity in obj.cavities:
            terminal = cavity.terminal
            if terminal is not None:
                result.extend(terminal.wires)
        return result

    return []


@_check_types.do
def _path_overlaps_rect(wire: "_wire_obj.Wire",
                        rect: tuple[float, float, float, float]) -> bool:
    """Cheap check: does any of *wire*'s current 2D sub-segments cross
    or run inside *rect* (``(min_x, min_z, max_x, max_z)``)? Used to
    filter which wires actually need the expensive
    :func:`reroute_wire`/A* call during :func:`sweep_for_overlaps`,
    rather than blindly rerouting every wire in the project.
    """
    min_x, min_z, max_x, max_z = rect

    for p1, p2 in wire.objschematic._segments():  # NOQA
        x1, z1 = float(p1[0]), float(p1[2])
        x2, z2 = float(p2[0]), float(p2[2])

        seg_min_x, seg_max_x = min(x1, x2), max(x1, x2)
        seg_min_z, seg_max_z = min(z1, z2), max(z1, z2)

        if seg_max_x < min_x or max_x < seg_min_x:
            continue
        if seg_max_z < min_z or max_z < seg_min_z:
            continue

        return True

    return False


@_check_types.do
def sweep_for_overlaps(project: "_project.Project", moved_obj,
                       already_rerouted: list["_wire_obj.Wire"]) -> None:
    """Run once, on drag/rotate release: for every connected wire *not*
    already live-rerouted this operation, reroute it if its current
    path now comes within ``Config.layout.housing_spacing`` of
    *moved_obj*'s new footprint -- a cheap AABB-vs-segment check first,
    the real (expensive) A* reroute only for wires actually violated.

    *moved_obj*'s bounds are grown by that same margin before the
    check -- the same technique the router itself already uses to keep
    a margin around an obstacle (see ``wire_routing.routing``'s own
    housing-obstacle-rect expansion) -- so this catches a wire that's
    now merely too CLOSE to the new footprint, not only one that
    literally crosses into it. An un-padded bounds check would silently
    miss exactly the violation this function exists to catch: confirmed
    2026-09-24 (Kevin) as a real gap, found while wiring this same
    sweep into the rotation gizmo (see rotation_handlers.
    editor_schematic.generic.Rings2D.detach) alongside the drag handler
    that already called this.
    """
    bounds = moved_obj.objschematic.get_bounds()
    if bounds is None:
        return

    margin = float(Config.layout.housing_spacing)
    min_x, min_z, max_x, max_z = bounds
    bounds = (min_x - margin, min_z - margin, max_x + margin, max_z + margin)

    already = set(already_rerouted)

    for wire in project.wires:
        if wire in already or not wire.is_connected:
            continue

        if _path_overlaps_rect(wire, bounds):
            reroute_wire(project, wire)
