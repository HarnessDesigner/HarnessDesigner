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
    reroute_wire(project, wire)
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
    has no fixed exit direction of its own) or the direction isn't
    resolvable yet (e.g. a bare terminal with no seated cavity).
    """
    from ..objects import terminal as _terminal

    sibling = wire.start_sibling if end == 'start' else wire.stop_sibling
    if not isinstance(sibling, _terminal.Terminal):
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


@_check_types.do
def reroute_wire(project: "_project.Project", wire: "_wire_obj.Wire",
                 skip_wires=frozenset()) -> None:
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
    """
    ptables = project.ptables
    db_obj = wire.db_obj

    start = db_obj.start_position2d
    stop = db_obj.stop_position2d

    start_xz = (float(start.x), float(start.z))
    stop_xz = (float(stop.x), float(stop.z))

    start_stub = _terminal_exit_stub_point(wire, 'start')
    stop_stub = _terminal_exit_stub_point(wire, 'stop')

    route_start = start_xz if start_stub is None else start_stub
    route_stop = stop_xz if stop_stub is None else stop_stub

    interior = _wire_routing.route(
        project, route_start, route_stop, ignore_wire=wire, skip_wires=skip_wires,
        start_anchor=None if start_stub is None else start_xz,
        stop_anchor=None if stop_stub is None else stop_xz)

    full_path = [start_xz]
    if start_stub is not None:
        full_path.append(start_stub)
    full_path.extend(interior)
    if stop_stub is not None:
        full_path.append(stop_stub)
    full_path.append(stop_xz)

    waypoints = _wire_routing._collapse(full_path)  # NOQA

    old_waypoints = list(db_obj.waypoints2d)
    common = min(len(old_waypoints), len(waypoints))

    from ..objects import wire_layout as _wire_layout

    layouts_table = ptables.pjt_wire_layouts_table

    # Reposition whatever overlaps -- the shared prefix of whichever
    # list is shorter -- in place rather than tearing it down and
    # inserting a fresh row (new id, new Point object, any WireLayout
    # re-anchored to it). One DB write per point moved, not a
    # delete-then-insert pair. Matches how every other live position
    # update in this codebase already works (e.g.
    # PJTHousing._update_position2d's own batch move).
    #
    # The explicit _process_callbacks() after the `with` block is
    # required, not optional -- per geometry/point.py's own documented
    # contract, callbacks (including PJTPoint2D's own DB write-through)
    # are suppressed entirely while inside `with point:`, and "the
    # caller is responsible for triggering the update itself after the
    # block" once it exits. Confirmed missing this the hard way
    # (2026-09-16): without it, self._data still updates in place (so
    # everything LOOKS right for the rest of the session -- rendering
    # reads the Point's live in-memory value directly, never through a
    # callback), but the database write-through callback never fires,
    # so the new position silently never persists -- a project
    # reload brought back a stale, much-earlier position instead. Same
    # explicit-call idiom PJTHousing._update_position2d's own batch
    # move already uses for exactly this reason.
    for old_point, (x, z) in zip(old_waypoints[:common], waypoints[:common]):
        point = old_point.point
        with point:
            point.x = x
            point.z = z
        point._process_callbacks()  # NOQA

        # Backfill a missing WireLayout for a waypoint that predates
        # this feature (created by an older reroute, before every
        # interior bend got its own handle) -- the "gained bend(s)"
        # branch below only ever creates one for a BRAND NEW point, so
        # without this an already-existing waypoint that just happens
        # to never hit that branch again would stay handle-less forever.
        #
        # old_point.db_id (the PJTPoint2D row wrapper's own id), NOT
        # point.db_id (the live Point's id, which carries a clone-
        # detection b'2d' suffix -- see PJTPoint2D.point -- and so is
        # NOT a valid point2d_id foreign key on its own).
        if layouts_table.for_point2d_id(old_point.db_id) is None:
            layout_db = layouts_table.insert(point2d_id=old_point.db_id)
            layout_obj = _wire_layout.WireLayout(wire.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

    if len(waypoints) > len(old_waypoints):
        # Gained bend(s) -- append fresh points/layouts for only the
        # new ones past what already existed and got moved above.
        for i in range(common, len(waypoints)):
            x, z = waypoints[i]
            new_point = ptables.pjt_points2d_table.insert(x, z, wire_id=db_obj.db_id, idx=i)

            # Every interior bend gets its own WireLayout handle -- same
            # as a terminal's own back/cavity routing points already do
            # for the 3D/peg-board views (see Terminal.add_wire) -- so a
            # routed bend is a real, selectable/draggable object in the
            # schematic too, not just a bare point the wire happens to
            # pass through.
            layout_db = layouts_table.insert(point2d_id=new_point.db_id)
            layout_obj = _wire_layout.WireLayout(wire.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

    elif len(waypoints) < len(old_waypoints):
        # Lost bend(s) -- delete only the excess old ones (and their
        # WireLayout, if any) past what's still needed and got moved
        # above.
        for point in old_waypoints[common:]:
            _pjt_wire.delete_layouts_at(layouts_table, 'point2d_id', point.db_id)

            # PJTPoint2D.delete() refuses outright while is_referenced()
            # is True -- and this point's own wire_id column, still
            # pointing at THIS (very much still-alive) wire, counts as a
            # reference on its own (see PJTPoint2D.is_referenced's
            # "Phase 6" check) -- so without clearing it first,
            # point.delete() would silently no-op every time, leaving
            # this excess waypoint sitting in the database forever
            # (confirmed 2026-09-16 from a live capture: waypoints kept
            # accumulating across reroutes instead of ever shrinking).
            point.wire_id = None
            point.delete()

    wire.objschematic.refresh_waypoints()


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
    """Run once, on drag release: for every connected wire *not* already
    live-rerouted this drag, reroute it if its current path now overlaps
    *moved_obj*'s new footprint -- a cheap AABB-vs-segment check first,
    the real (expensive) A* reroute only for wires actually violated.
    """
    bounds = moved_obj.objschematic.get_bounds()
    if bounds is None:
        return

    already = set(already_rerouted)

    for wire in project.wires:
        if wire in already or not wire.is_connected:
            continue

        if _path_overlaps_rect(wire, bounds):
            reroute_wire(project, wire)
