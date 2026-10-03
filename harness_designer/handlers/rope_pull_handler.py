# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board reconciliation for the ``rope_pull`` solver -- see
``BUNDLE_PLACEMENT.md`` sections 6/6b for the design, and
``rope_pull.rope_pull_py`` for the solver itself. Two entry points:

- :func:`resolve_rigid_move` -- called by a peg-board drag of anything
  that could be a wire/bundle anchor OR an interior waypoint
  (``drag_handlers.editor_pegboard.generic.Generic``). Takes EVERY real
  point the dragged object is about to move, each at its own position
  when the drag BEGAN (not the last frame), plus the one full delta the
  current mouse position implies for all of them together -- almost
  always a single point, except a Transition, which moves every one of
  its branches' own points together by the same rigid delta its own
  center moves by, and a bundle is anchored at a BRANCH's own point,
  never the transition's own center point. Binary-searches the largest
  fraction of that delta every touched chain can accept AT ONCE (see its
  own docstring for why a fresh line from the drag's own start, instead
  of a hard per-frame refuse, is what fixes the "stuck until the mouse
  wanders back over it" bug), reconciles every chain's interior
  waypoints at that fraction, and returns it so the caller can place the
  dragged object there. A point touching no chain at all (an ordinary
  housing with no wires, say) always resolves to the full ``1.0``.
- :func:`realize_length_change` (for one already-known chain) and
  :func:`realize_3d_move` (for every chain anchored at one of several
  given 3D point ids -- the 3D-side counterpart of the "a Transition
  moves several points at once" case above) -- called after a 3D drag
  changes a wire's/bundle's real length, per ``BUNDLE_PLACEMENT.md``
  section 6's decided rule that a 3D length change must be realized in
  the peg-board view.

**The cascade (user's own spec, 2026-10-01).** Every chain (bundle or
wire) a moved point touches is checked the same way: if the chain's OWN
slack can absorb the move with its far end held exactly where it is,
nothing else happens. If it can't, the far end doesn't just refuse --
whatever single rigid object owns it (another Transition, a Housing, a
Splice, a WireServiceLoop -- see :func:`_node_for_point`; a genuinely
free bundle/wire end is pulled directly, nothing further to cascade
into) is pulled by exactly enough to relieve that one chain (straight
line between the two ends, every bit of slack used, zero zigzag left),
and the exact same check then runs for every OTHER chain attached to
that newly-pulled object -- a Transition pulled through one branch can
pull a second bundle hanging off one of its OTHER branches, which can
pull a second Transition, and so on outward, all the way to whatever
Housing or Terminal eventually has enough of its own remaining slack to
absorb the rest. :func:`_evaluate_points` is both the single-chain check
AND this whole cascade -- see its own docstring for exactly how, and for
why no explicit cycle-detection code was needed to satisfy the chosen
"refuse the whole move on a cycle" policy.

**A pulled Transition rotates, it doesn't just translate** -- per
section 6's own already-decided pivot/trailing rule, confirmed by the
user still stands (2026-10-01): "the body would end up trailing the
branch when it is being pulled; that is what would happen in the real
world." The branch the pull arrives through pivots exactly onto its own
new target position, undisturbed; every other point of that Transition
(its own centre, and every other branch) rotates about that same pivot
by whatever angle points the Transition's own pre-pull centre directly
away from the pull direction -- see :func:`_rotated_and_translated` for
the exact math (verified directly against this codebase's own real
``geometry.point.Point.set_angle``/``geometry.angle.Angle``
machinery). A pulled Housing/Splice/WireServiceLoop only ever
translates -- the doc's own rotation rule is specific to a Transition's
own branch geometry.

Terminal is NOT one of the node types :func:`_node_for_point` recognises
yet -- see that function's own docstring for why (its real wire
attachment point is a separate, derived point from its own structural
position, with nothing yet known to keep the two in sync under a pull
the way a Transition's branch tips already are). A wire reaching a
terminal today pulls only that one attachment point, same as a free
end -- correct in effect (the point ends up in the right place), but
the terminal's own rendered body does not visibly move with it yet.

**Waypoint add/remove deferred to mouse-up (user's own spec,
2026-10-02).** A drag can run many frames a second, and the solver's
own ideal waypoint count for a span can change on almost any one of
them as the needed slack crosses a bump-count threshold -- inserting
or deleting a ``pjt_points_pegboard``/``pjt_bundle_layouts``/
``pjt_wire_layouts`` row every such frame would be real, continuous DB
churn for the whole length of a drag. :func:`_commit_points`'s own
``in_progress`` flag (default ``True`` for :func:`resolve_rigid_move`)
holds every touched chain's own waypoint COUNT fixed through every
ordinary frame -- :func:`_fixed_count_interior` repositions whatever
already exists to the best shape that count can reach, exact length
when it can, visibly taut/straight when it can't yet -- and the drag's
own very last call, the moment the mouse button is released
(``drag_handlers.editor_pegboard.generic.Generic.delete``), runs the
real, height-cap-derived reconcile exactly once, letting the count
finally catch up to whatever it actually needs. Every OTHER caller
(:func:`realize_length_change`, a one-shot reconcile, not a per-frame
drag) always uses the real shape, same as before this existed.

**Peg-board view only.** Nothing here runs for a 3D drag directly --
:func:`realize_length_change`/:func:`realize_3d_move` are triggered BY
one, but the work they do (and now cascade through) is entirely within
the peg-board view's own point graph. A bundle's/wire's real 3D length
has no ceiling of its own today (3D is the unconstrained source of
truth the peg-board view must always match), so there is nothing to
cascade on while dragging something in 3D itself.

**Graduated, via a line from the drag's own start -- not a per-frame
hard refuse (revised 2026-10-01).** An anchor (a `Housing`/`Transition`/
`Terminal`/`Splice`/`WireServiceLoop`) can be shared by several
wires/bundles at once (several wires entering one housing, say).
:func:`resolve_rigid_move` checks a candidate *fraction of the full
delta* against every touching chain (now, the whole cascade it may
trigger) and requires every single one to accept it, same as before --
what changed is WHICH candidates get tried. An earlier version refused
the mouse's own raw target outright and stopped there, which (confirmed
live, user, 2026-10-01) left the dragged object stuck exactly where the
last accepted frame put it while the mouse kept moving, since the next
frame's delta was computed against that now-stale position rather than
the cursor -- "the transition stops moving... until the mouse is
hovering over the top of it again." Recomputing the full delta fresh
every frame from the drag's own fixed start (never the previous frame's
possibly-clamped result) and binary-searching the farthest fraction of
THAT line every touched chain accepts removes the stuck state entirely:
the object always ends up somewhere sensible toward the mouse, every
frame independently, never needing the mouse to "catch back up" to a
frozen position.

**Reconciling the solver's stateless output against persistent DB rows.**
``solve_chain`` recomputes a chain's ENTIRE interior waypoint list from
scratch every call (see ``rope_pull_py``'s own module docstring) -- it
has no notion of "this waypoint already existed". Naively replacing
every interior point every frame would delete and recreate the exact
``BundleLayout``/``WireLayout`` DB row (and live Python object) the user
is actively dragging in the WAYPOINT case, which would corrupt the
live drag session (the armed drag handler holds a direct reference to
that one object across every frame of the same drag). :func:`_reconcile_interior`
fixes this: the dragged point's own id (when there is one -- the
WAYPOINT case) is matched to its own exact position in the solver's
output (passed through unmodified, so an exact float match is reliable)
and kept, never deleted/recreated; every OTHER interior position reuses
an existing point row positionally where possible (just repositions it,
no DB churn for a small/typical change), only inserting a fresh
``pjt_points_pegboard`` + ``pjt_bundle_layouts``/``pjt_wire_layouts`` row
(mirroring ``handlers.wire_slack``'s own ``_add_waypoint_pegboard``
construction exactly) when the new list is longer than the old one, and
only deleting an existing layout's live facade object (via its own
``.delete()``, mirroring ``objects.bundle_layout.BundleLayout.delete``/
``objects.wire_layout.WireLayout.delete``) when the new list is shorter.
"""

from typing import TYPE_CHECKING, Union as _Union

import math

from .. import rope_pull as _rope_pull
from .. import config as _config
from ..geometry import point as _point
from ..objects import bundle_layout as _bundle_layout
from ..objects import wire_layout as _wire_layout
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_bundle_path as _pjt_bundle_path
    from ..database.project_db import pjt_wire_path as _pjt_wire_path
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from ..database.project_db import pjt_wire_layout as _pjt_wire_layout


Config = _config.Config.editor_pegboard.rope_pull


@_check_types.do
def _anchors_and_length(
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]
) -> tuple[tuple[float, float], tuple[float, float], float]:
    """*chain_db_obj*'s two peg-board anchors as plain ``(x, z)`` tuples,
    plus its real (3D-derived) ``length_mm`` -- exactly what
    ``rope_pull.solve_chain`` needs, read fresh every call since
    ``length_mm`` has no cache/signal of its own (confirmed: a plain
    computed property, see its own docstring on ``PJTBundle``/``PJTWire``).
    """
    start = chain_db_obj.start_position_pegboard
    stop = chain_db_obj.stop_position_pegboard
    return (float(start.x), float(start.z)), (float(stop.x), float(stop.z)), chain_db_obj.length_mm


@_check_types.do
def _drag_end_for(
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"], point_id: bytes
) -> "_rope_pull.DragEnd | None":
    """Whether *point_id* is *chain_db_obj*'s own start or stop anchor,
    or neither.
    """
    if chain_db_obj.start_position_pegboard_id == point_id:
        return _rope_pull.DragEnd.START

    if chain_db_obj.stop_position_pegboard_id == point_id:
        return _rope_pull.DragEnd.STOP

    return None


@_check_types.do
def _reconcile_interior(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    path_table: _Union["_pjt_bundle_path.PJTBundlePathsTable", "_pjt_wire_path.PJTWirePathsTable"],
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    layout_facade_cls: _Union[type["_bundle_layout.BundleLayout"], type["_wire_layout.WireLayout"]],
    new_interior: list[tuple[float, float]],
    pin_point_id: bytes | None,
    pin_xz: tuple[float, float] | None
) -> None:
    """Rewrite *chain_db_obj*'s peg-board interior waypoints to
    *new_interior*, preserving *pin_point_id* (the point actively being
    dragged, in the WAYPOINT case -- ``None``/``None`` for an anchor
    drag, which has no pin) -- see the module docstring's own
    "Reconciling..." section for why and how.

    **Ordering matters here.** ``path_table.set_route(...)`` -- which
    establishes which bundle/wire a given point id belongs to -- runs
    BEFORE any new ``BundleLayout``/``WireLayout`` facade object is
    constructed for a brand-new point, not after. A facade's own
    ``__init__`` reads ``attached_bundles``/``attached_wires`` (backed
    by this exact path table) to derive its real diameter/color;
    constructing it first and calling ``set_route`` afterward (an
    earlier version of this function did exactly that) left every
    newly-added waypoint looking permanently unattached at the moment
    it mattered, falling through to the neutral-gray "no bundle"
    fallback color instead of the bundle's own -- confirmed live by the
    user (2026-10-01): "spheres... not the same color as the bundle."
    """
    project = mainframe.project
    points_table = project.ptables.pjt_points_pegboard_table

    old_ids = list(path_table.point_ids(chain_db_obj.db_id, 'pegboard'))

    pin_new_index = None
    if pin_point_id is not None:
        for i, xz in enumerate(new_interior):
            if xz == pin_xz:
                pin_new_index = i
                break

        if pin_point_id in old_ids:
            old_ids.remove(pin_point_id)

    remaining_new_indexes = [i for i in range(len(new_interior)) if i != pin_new_index]
    remaining_old_ids = old_ids

    final_ids: list[bytes | None] = [None] * len(new_interior)

    if pin_new_index is not None:
        final_ids[pin_new_index] = pin_point_id
        pin_point = points_table[pin_point_id].point
        pin_point.x = pin_xz[0]
        pin_point.z = pin_xz[1]

    reuse_count = min(len(remaining_new_indexes), len(remaining_old_ids))

    for i in range(reuse_count):
        new_index = remaining_new_indexes[i]
        point_id = remaining_old_ids[i]
        x, z = new_interior[new_index]
        point = points_table[point_id].point
        point.x = x
        point.z = z
        final_ids[new_index] = point_id

    # Only the raw point rows are inserted here -- the layout row and
    # facade object for each come after set_route, below.
    new_indexes = []
    for i in range(reuse_count, len(remaining_new_indexes)):
        new_index = remaining_new_indexes[i]
        x, z = new_interior[new_index]
        point_db = points_table.insert(x, 0.0, z)
        final_ids[new_index] = point_db.db_id
        new_indexes.append(new_index)

    removed_ids = remaining_old_ids[reuse_count:]

    path_table.set_route(chain_db_obj.db_id, 'pegboard', final_ids)

    for new_index in new_indexes:
        layout_db = layouts_table.insert(point_pegboard_id=final_ids[new_index])
        layout_obj = layout_facade_cls(mainframe, layout_db)
        if layout_facade_cls is _bundle_layout.BundleLayout:
            project.add_bundle_layout(layout_obj)
        else:
            project.add_wire_layout(layout_obj)

    for point_id in removed_ids:
        layout_db = layouts_table.for_point_pegboard_id(point_id)
        if layout_db is not None:
            layout_obj = layout_db.get_object()
            if layout_obj is not None:
                layout_obj.delete()

    # The waypoint markers (the layouts just inserted/moved/deleted
    # above) are independent GL objects with their own live Point, so
    # they already render in their new positions for free -- but the
    # CHAIN's own rendered strand (its mesh, cached from the waypoint
    # list) does not re-derive itself just because the DB rows changed.
    # Confirmed live by the user (2026-10-01): waypoint spheres moved/
    # appeared correctly, but "no rope pull effect" on the bundle's own
    # strand -- exactly this gap. Mirrors handlers.wire_slack's own
    # closing call for the same reason.
    chain_obj = chain_db_obj.get_object()
    if chain_obj is not None:
        chain_obj.objpegboard.refresh_waypoints()


@_check_types.do
def _chains_for_point(ptables, point_id: bytes) -> list[tuple]:
    """Every chain (bundle or wire) that *point_id* is part of, each as
    ``(chain_db_obj, path_table, layouts_table, layout_facade_cls,
    drag_end)`` -- ``drag_end`` is :attr:`rope_pull.DragEnd.WAYPOINT` if
    *point_id* is an interior waypoint (at most one chain, by
    construction -- a waypoint belongs to exactly one bundle/wire), or
    :attr:`~rope_pull.DragEnd.START`/:attr:`~rope_pull.DragEnd.STOP` for
    every chain *point_id* anchors (zero or more -- e.g. several wires
    entering the same housing, or a bundle plugged into one of a
    transition's branches).
    """
    bundle_ids = ptables.pjt_bundle_paths_table.bundle_ids_for_point('pegboard', point_id)
    if bundle_ids:
        bundle_db_obj = ptables.pjt_bundles_table[bundle_ids[0]]
        return [(
            bundle_db_obj, ptables.pjt_bundle_paths_table,
            ptables.pjt_bundle_layouts_table, _bundle_layout.BundleLayout,
            _rope_pull.DragEnd.WAYPOINT)]

    wire_ids = ptables.pjt_wire_paths_table.wire_ids_for_point('pegboard', point_id)
    if wire_ids:
        wire_db_obj = ptables.pjt_wires_table[wire_ids[0]]
        return [(
            wire_db_obj, ptables.pjt_wire_paths_table,
            ptables.pjt_wire_layouts_table, _wire_layout.WireLayout,
            _rope_pull.DragEnd.WAYPOINT)]

    chains = []

    for bundle_db_obj in ptables.pjt_bundles_table:
        drag_end = _drag_end_for(bundle_db_obj, point_id)
        if drag_end is not None:
            chains.append((
                bundle_db_obj, ptables.pjt_bundle_paths_table,
                ptables.pjt_bundle_layouts_table, _bundle_layout.BundleLayout, drag_end))

    for wire_db_obj in ptables.pjt_wires_table:
        drag_end = _drag_end_for(wire_db_obj, point_id)
        if drag_end is not None:
            chains.append((
                wire_db_obj, ptables.pjt_wire_paths_table,
                ptables.pjt_wire_layouts_table, _wire_layout.WireLayout, drag_end))

    return chains


@_check_types.do
def _pulled_far_position(
    far_xz: tuple[float, float], near_target_xz: tuple[float, float], required_length: float
) -> tuple[float, float]:
    """*far_xz* unmoved, unless the straight-line distance to
    *near_target_xz* already exceeds *required_length* -- in which case
    *far_xz* is pulled straight toward *near_target_xz* until the
    distance exactly equals *required_length* (every bit of the
    chain's own slack used, zero zigzag left).

    Pure geometry only -- carries no notion of what (if anything) OWNS
    *far_xz*, or of whether pulling it is even allowed; that's entirely
    :func:`_evaluate_points`'s own job (a lone free point moves
    directly; a point owned by a Transition/Housing/Splice/
    WireServiceLoop takes its whole owning object -- see
    :func:`_node_for_point` -- along with it, and cascades on into that
    object's other chains from there).
    """
    dx = far_xz[0] - near_target_xz[0]
    dz = far_xz[1] - near_target_xz[1]
    straight = math.hypot(dx, dz)

    if straight <= required_length or straight < 1e-9:
        return far_xz

    scale = required_length / straight
    return near_target_xz[0] + dx * scale, near_target_xz[1] + dz * scale


@_check_types.do
def _node_for_point(ptables, point_id: bytes) -> tuple[str, list[bytes]] | None:
    """The rigid structural object that owns *point_id*, as
    ``(kind, points)`` -- *points* is every peg-board point that moves
    together with it as one object (a Transition's own centre PLUS
    every one of its branches -- centre always ``points[0]`` -- a
    Splice's or WireServiceLoop's own start AND stop together, or a
    Housing's single point); *kind* is ``'transition'`` (the only kind
    that ROTATES when pulled -- see :func:`_rotated_and_translated`'s
    own caller) or ``'rigid'`` (pure translation, same delta for every
    point in *points*). ``None`` if *point_id* belongs to none of
    these (a genuinely free point, owned by nothing).

    **Terminal is deliberately not one of the types recognised here.**
    A wire's real attachment point on a terminal
    (``PJTTerminal.wire_position_pegboard_id``) is a separate, derived
    point -- offset from the terminal's own structural
    ``position_pegboard_id`` by its own angle -- and nothing is known
    to keep that offset point in sync if the terminal's own body were
    pulled, the way a Transition's branch tips already are (see
    ``objects_pegboard.transition.Transition._update_position`` ->
    ``write_tips_to_db``, confirmed to already run on exactly this kind
    of move; there is no equivalent for a terminal's own
    wire-attachment point today). Modeling that correctly is its own
    task, left for later -- a wire reaching a terminal pulls only that
    one attachment point for now, same as a genuinely free end, with
    nothing further to cascade into past it (the point ends up in the
    right place; the terminal's own rendered body just doesn't visibly
    follow it yet).
    """
    if ptables.pjt_housings_table.select('id', point_pegboard_id=point_id):
        return 'rigid', [point_id]

    branch_rows = ptables.pjt_transition_branches_table.select(
        'transition_id', point_pegboard_id=point_id)
    if branch_rows:
        transition_id = branch_rows[0][0]
    else:
        transition_rows = ptables.pjt_transitions_table.select('id', point_pegboard_id=point_id)
        transition_id = transition_rows[0][0] if transition_rows else None

    if transition_id is not None:
        transition = ptables.pjt_transitions_table[transition_id]
        points = [transition.position_pegboard_id]
        for branch in transition.branches:
            points.append(branch.position_pegboard_id)
        return 'transition', points

    for table in (ptables.pjt_splices_table, ptables.pjt_wire_service_loops_table):
        rows = table.select(
            'id', OR=True,
            start_point_pegboard_id=point_id, stop_point_pegboard_id=point_id)
        if rows:
            obj = table[rows[0][0]]
            return 'rigid', [obj.start_position_pegboard_id, obj.stop_position_pegboard_id]

    return None


@_check_types.do
def _rotated_and_translated(
    old_xz: tuple[float, float], pivot_old_xz: tuple[float, float],
    pivot_new_xz: tuple[float, float], phi: float
) -> tuple[float, float]:
    """*old_xz*, translated so *pivot_old_xz* would sit exactly on
    *pivot_new_xz*, then rotated by *phi* radians about *pivot_new_xz*
    -- ``pivot_new_xz + R(phi) @ (old_xz - pivot_old_xz)``, matching
    ``BUNDLE_PLACEMENT.md`` section 6's own pivot/trailing rule exactly
    (``T + R(phi) * (old_position - B0)``, *B0* = *pivot_old_xz*,
    *T* = *pivot_new_xz*).

    ``R(phi)`` here is ``[[cos, sin], [-sin, cos]]`` against ``(x, z)``
    -- confirmed by direct comparison against the real
    ``geometry.point.Point.set_angle``/``geometry.angle.Angle.
    from_axis_angle(numpy.array([0, 1, 0]), phi)`` machinery every
    OTHER rotation in this codebase goes through (2026-10-01): rotating
    ``(1, 0, 0)`` by ``phi`` about ``+Y`` that way gives
    ``(cos(phi), 0, -sin(phi))``, exactly this matrix's own first
    column. Kept as this own tiny closed-form instead of constructing a
    real ``Point``/``Angle`` pair here, since this runs purely on plain
    ``(x, z)`` floats throughout the whole cascade and must stay usable
    during the PURE evaluate pass -- no live object, no DB, no GL
    context required either way.
    """
    x = old_xz[0] - pivot_old_xz[0]
    z = old_xz[1] - pivot_old_xz[1]
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    return (
        pivot_new_xz[0] + x * cos_phi + z * sin_phi,
        pivot_new_xz[1] - x * sin_phi + z * cos_phi)


@_check_types.do
def _fixed_count_span(
    a: tuple[float, float], b: tuple[float, float], target_length: float, count: int
) -> list[tuple[float, float]]:
    """Same build as ``rope_pull_py._solve_span``, but with the bump
    COUNT held fixed at *count* instead of derived from the height cap
    -- see :func:`_fixed_count_interior`'s own docstring for why this
    exists. Deliberately duplicated here in pure Python rather than
    extending the compiled ``rope_pull`` solver itself: this is a
    handler-level DB-churn concern, not a core geometry one, and has no
    need to be Cython-fast (a handful of points, not a hot inner loop).
    """
    if count <= 0:
        return []

    ax, az = a
    bx, bz = b
    dx = bx - ax
    dz = bz - az
    straight = math.hypot(dx, dz)

    excess = math.sqrt(max(target_length * target_length - straight * straight, 0.0))
    height = excess / (2.0 * count)

    if straight < 1e-9:
        ux, uz = 1.0, 0.0
    else:
        ux, uz = dx / straight, dz / straight

    px, pz = uz, -ux

    waypoints = []
    for i in range(count):
        if i > 0:
            t_zero = i / count
            waypoints.append((ax + t_zero * dx, az + t_zero * dz))

        t_apex = (i + 0.5) / count
        sign = 1.0 if i % 2 == 0 else -1.0

        apex_x = ax + t_apex * dx + px * height * sign
        apex_z = az + t_apex * dz + pz * height * sign
        waypoints.append((apex_x, apex_z))

    return waypoints


@_check_types.do
def _fixed_count_interior(
    start_xz: tuple[float, float], stop_xz: tuple[float, float], required_length: float,
    drag_end: "_rope_pull.DragEnd", target_xz: tuple[float, float], point_count: int
) -> list[tuple[float, float]]:
    """Same overall shape as ``rope_pull.solve_chain``'s own interior
    output (the same skeleton/proportional-slack-split construction),
    but every span's own bump count is held FIXED so the total interior
    point count always equals *point_count* -- used only to reposition
    an existing set of waypoints smoothly, frame to frame, during an
    in-progress drag, without ever inserting or deleting a single DB
    row (see :func:`_commit_points`'s own ``in_progress`` flag, and the
    user's own explicit spec, 2026-10-02: "any addition and subtraction
    of waypoints should only be committed to the database when the
    drag operation stops"). The true, height-cap-derived shape (which
    CAN change the count) runs exactly once more, the moment the drag
    actually ends -- see ``drag_handlers.editor_pegboard.generic.
    Generic.delete``.

    Exact total length is NOT guaranteed when *point_count* can't
    support however much slack is actually needed (e.g. zero existing
    waypoints but real slack is now required) -- the chain renders
    visibly taut/straight until enough points exist again, which only
    happens at the next full (mouse-up) reconcile. A deliberate,
    transient approximation, not a bug: the alternative is inserting or
    deleting a row on every single drag frame, which is exactly what
    this exists to avoid.

    :returns: The full point list, start through stop inclusive, same
        slicing convention as ``rope_pull.ChainResult.points`` (callers
        take ``[1:-1]`` for the interior alone).
    """
    if drag_end is _rope_pull.DragEnd.WAYPOINT:
        skeleton = [start_xz, target_xz, stop_xz]
    elif drag_end is _rope_pull.DragEnd.START:
        skeleton = [target_xz, stop_xz]
    else:
        skeleton = [start_xz, target_xz]

    span_count = len(skeleton) - 1
    straights = [
        math.hypot(skeleton[i + 1][0] - skeleton[i][0], skeleton[i + 1][1] - skeleton[i][1])
        for i in range(span_count)]
    base_length = sum(straights)
    needed_slack = max(required_length - base_length, 0.0)

    if span_count == 1:
        counts = [max(0, (point_count + 1) // 2)]
    elif point_count <= 1:
        # Just the pin (or a degenerate non-positive input, which
        # shouldn't occur -- the pin itself always makes point_count
        # at least 1 for a WAYPOINT drag): no bumps on either side.
        counts = [0, 0]
    elif point_count % 2 == 0:
        # A span's own achievable output is always 2*count-1 (odd) or
        # 0 -- an EVEN point_count (excluding the pin, which itself
        # contributes the "+1" that makes a two-bumped total odd) can
        # only ever be hit by putting every bump on ONE side and
        # leaving the other at a flat 0, never split between both.
        k = point_count // 2
        counts = [k, 0] if straights[0] >= straights[1] else [0, k]
    else:
        m = (point_count + 1) // 2
        total_straight = straights[0] + straights[1]
        count0 = m // 2 if total_straight < 1e-9 else round(m * straights[0] / total_straight)
        count0 = max(1, min(m - 1, count0))
        counts = [count0, m - count0]

    # Slack can only ever go to a span that actually has a bump to
    # carry it (a count of 0 can only ever produce its own bare
    # straight length, never more) -- splitting it proportionally by
    # straight length across EVERY span regardless, the way the real
    # solver does (every span there always has room to grow), silently
    # lost whatever share landed on a zero-count span here instead,
    # undershooting required_length even though the span(s) that
    # actually HAD a bump could have carried the rest. Route it only
    # to spans with counts[i] > 0.
    capable_straight = sum(straights[i] for i in range(span_count) if counts[i] > 0)

    points = [skeleton[0]]
    for i in range(span_count):
        a, b = skeleton[i], skeleton[i + 1]
        if counts[i] <= 0 or capable_straight < 1e-9:
            share = 0.0
        else:
            share = needed_slack * (straights[i] / capable_straight)

        points.extend(_fixed_count_span(a, b, straights[i] + share, counts[i]))
        points.append(b)

    return points


@_check_types.do
def _evaluate_points(
    ptables, point_targets: list[tuple[bytes, tuple[float, float]]]
) -> tuple[list[tuple], dict[bytes, tuple[float, float]]] | None:
    """Pure solve, no DB writes -- every ``(point_id, target_xz)`` pair
    in *point_targets* moving AT ONCE, cascading through whatever else
    needs to move as a result (see the module docstring's own "The
    cascade" section for the rule in plain words).

    **How.** *fixed* is this whole resolve's one authoritative map of
    "every point whose position is already decided" -- seeded from
    *point_targets* itself, and grown every time a pull decides a new
    point's position. *pending* is the matching worklist: points whose
    own touching chains haven't been checked yet. Popping a point and
    walking :func:`_chains_for_point` for it covers both directions a
    chain can be discovered from -- the point IS one of its two real
    anchors, or (if several points of the SAME pulled node happen to
    touch the chain this call already handled from the other side)
    nothing new, caught by *seen_chains* so a chain is never evaluated
    twice. For each chain: the OTHER (far) end is read fresh from the
    DB unless it's already in *fixed* (already decided this resolve,
    whether an original target or an earlier pull -- then that value is
    authoritative and is used as-is, never re-pulled). If letting the
    far end sit right there would make the chain too short
    (:func:`_pulled_far_position` returns something different), the far
    point's own owning node (:func:`_node_for_point`; a lone point if it
    owns nothing) is pulled by that exact delta, EVERY one of its
    points is added to *fixed*/*pending* together (so the cascade keeps
    going from all of them, not just the one point this particular
    chain happened to touch), and the node's points are recorded in
    *write_points* for :func:`_commit_points` to actually write.

    **Why no explicit cycle detection is needed to satisfy the "refuse
    the whole move on a cycle" policy (user, 2026-10-01).** A point
    already in *fixed* is never pulled a second time with a different
    delta -- whichever chain reaches it FIRST decides its position for
    the rest of this resolve. A closed loop (several Transitions/
    bundles forming a ring, say) therefore either happens to still fit
    once every node along it has been independently pulled this way --
    accepted, nothing further needed, a strictly BETTER outcome than
    refusing a ring that actually had enough slack to flex -- or it
    doesn't, and whichever chain closes the loop fails the ordinary
    ``solve_chain`` feasibility check against the two now-fixed ends it
    can no longer move, which already returns ``None`` below. Both
    outcomes satisfy the chosen policy without a solver for the loop's
    simultaneous constraints ever being written.

    :returns: ``(entries, write_points)`` -- *entries* is every
        ``(chain_db_obj, path_table, layouts_table, layout_facade_cls,
        drag_end, point_id, target_xz, result)`` :func:`_commit_points`
        needs to reconcile each chain's own interior, and *write_points*
        is every ``point_id -> (x, z)`` a pull decided that isn't one of
        *point_targets* itself (the caller already owns moving those).
        ``None`` if anything, anywhere in the whole cascade, is
        infeasible even after every pull it allows.
    """
    points_table = ptables.pjt_points_pegboard_table

    fixed: dict[bytes, tuple[float, float]] = dict(point_targets)
    write_points: dict[bytes, tuple[float, float]] = {}
    pending: list[bytes] = [point_id for point_id, _ in point_targets]
    seen_chains: set[bytes] = set()
    entries = []

    def pull_if_needed(
        far_point_id: bytes, far_xz: tuple[float, float],
        near_target_xz: tuple[float, float], required_length: float
    ) -> tuple[float, float]:
        if far_point_id in fixed:
            return fixed[far_point_id]

        pulled_xz = _pulled_far_position(far_xz, near_target_xz, required_length)
        if pulled_xz == far_xz:
            return far_xz

        node = _node_for_point(ptables, far_point_id)
        kind, node_points = ('rigid', [far_point_id]) if node is None else node

        if kind == 'transition':
            # BUNDLE_PLACEMENT.md section 6's own pivot/trailing rule:
            # far_point_id IS the branch the pull arrives through (the
            # "handle"), always node_points[1:]'s member, never the
            # centre -- a bundle/wire anchors at a branch's own point,
            # never a transition's bare centre point (see this module's
            # own docstring's "anchor model"). phi is the rotation that
            # points the vector from the handle to the transition's own
            # (pre-pull) centre in the direction OPPOSITE the pull, so
            # the body trails behind the branch being pulled, same as
            # the real world.
            center_id = node_points[0]
            center_point = points_table[center_id].point
            center_old = (float(center_point.x), float(center_point.z))

            dx = pulled_xz[0] - far_xz[0]
            dz = pulled_xz[1] - far_xz[1]
            vx = center_old[0] - far_xz[0]
            vz = center_old[1] - far_xz[1]

            if math.hypot(dx, dz) < 1e-9 or math.hypot(vx, vz) < 1e-9:
                phi = 0.0
            else:
                phi = math.atan2(vz, vx) - math.atan2(-dz, -dx)

            for p in node_points:
                p_point = points_table[p].point
                p_old = (float(p_point.x), float(p_point.z))
                new_xz = _rotated_and_translated(p_old, far_xz, pulled_xz, phi)
                fixed[p] = new_xz
                write_points[p] = new_xz
                pending.append(p)
        else:
            delta = (pulled_xz[0] - far_xz[0], pulled_xz[1] - far_xz[1])

            for p in node_points:
                p_point = points_table[p].point
                new_xz = (float(p_point.x) + delta[0], float(p_point.z) + delta[1])
                fixed[p] = new_xz
                write_points[p] = new_xz
                pending.append(p)

        return pulled_xz

    while pending:
        point_id = pending.pop()
        target_xz = fixed[point_id]

        for chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end in _chains_for_point(ptables, point_id):
            if chain_db_obj.db_id in seen_chains:
                continue
            seen_chains.add(chain_db_obj.db_id)

            start_xz, stop_xz, required_length = _anchors_and_length(chain_db_obj)

            if drag_end is _rope_pull.DragEnd.START:
                stop_xz = pull_if_needed(
                    chain_db_obj.stop_position_pegboard_id, stop_xz, target_xz, required_length)
            elif drag_end is _rope_pull.DragEnd.STOP:
                start_xz = pull_if_needed(
                    chain_db_obj.start_position_pegboard_id, start_xz, target_xz, required_length)
            # DragEnd.WAYPOINT: both real anchors stay exactly as read --
            # the anchor model never lets a waypoint drag move them, and
            # a waypoint belongs to exactly one chain by construction,
            # so nothing ever cascades INTO this branch either.

            result = _rope_pull.solve_chain(
                start_xz, stop_xz, required_length, drag_end, target_xz,
                Config.height_cap_fraction, Config.min_height_mm)

            if not result.accepted:
                return None

            entries.append((
                chain_db_obj, path_table, layouts_table, layout_facade_cls,
                drag_end, point_id, target_xz, result, start_xz, stop_xz, required_length))

    return entries, write_points


@_check_types.do
def _commit_points(
    mainframe: "_ui.MainFrame", entries: list[tuple], write_points: dict[bytes, tuple[float, float]],
    in_progress: bool = False
) -> None:
    """Reconcile every entry :func:`_evaluate_points` already found
    acceptable, and write every point its cascade decided to pull --
    see that function's own docstring for both. Writes *write_points*
    first: every chain's own interior reconcile below reads anchor
    positions fresh from the DB again (``_reconcile_interior`` ->
    ``get_object()``'s live render, and any OTHER chain touching one of
    these same pulled points that a later call resolves), so the pulled
    positions must already be real by the time any of that runs.

    **in_progress (user's own spec, 2026-10-02).** When ``True``, every
    chain's own interior is rebuilt via :func:`_fixed_count_interior`
    (same total waypoint count it already has -- repositioned only) in
    place of the solver's own ``result.points`` (whose count can and
    does change frame to frame) -- so a mid-drag frame never inserts or
    deletes a single ``pjt_points_pegboard``/``pjt_bundle_layouts``/
    ``pjt_wire_layouts`` row. Still exact-length when the existing
    count can support the needed slack; only an approximation when it
    can't (see that function's own docstring). ``False`` (every caller
    OTHER than a per-frame peg-board drag, plus that drag's own very
    last frame) uses the solver's real, height-cap-derived shape as
    before, letting the count catch up to whatever it actually needs.
    """
    points_table = mainframe.project.ptables.pjt_points_pegboard_table

    for point_id, (x, z) in write_points.items():
        point = points_table[point_id].point
        point.x = x
        point.z = z

    for (
        chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end, point_id, target_xz,
        result, start_xz, stop_xz, required_length
    ) in entries:
        if in_progress:
            old_count = len(path_table.point_ids(chain_db_obj.db_id, 'pegboard'))
            full_points = _fixed_count_interior(
                start_xz, stop_xz, required_length, drag_end, target_xz, old_count)
        else:
            full_points = result.points

        interior = full_points[1:-1]
        if drag_end is _rope_pull.DragEnd.WAYPOINT:
            _reconcile_interior(
                mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls,
                interior, point_id, target_xz)
        else:
            _reconcile_interior(
                mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls,
                interior, None, None)


@_check_types.do
def resolve_rigid_move(
    mainframe: "_ui.MainFrame",
    point_starts: list[tuple[bytes, _point.Point]],
    full_delta: tuple[float, float],
    iterations: int = 32,
    in_progress: bool = True
) -> float:
    """Binary-search the largest fraction ``t`` in ``[0, 1]`` such that
    moving every point in *point_starts* by ``t * full_delta`` --
    each measured from ITS OWN position when the WHOLE drag began, in
    :attr:`point_starts`, never accumulated frame to frame -- is
    accepted by every wire/bundle chain any of them touches. Commits
    the reconciliation at that final ``t`` only; every candidate ``t``
    explored only during the search is pure read-only solving (see
    :func:`_evaluate_points`), never partially written to the DB.

    **Why resolve a drag as a line from its own start, instead of a
    per-frame increment that hard-refuses.** A hard per-frame refuse
    (the original design) left the dragged object's own position
    exactly where the LAST accepted frame put it, while the mouse kept
    moving -- the next frame's delta was computed against that stale
    position, not the cursor, so the object stayed stuck until the
    mouse happened to wander back over it. Confirmed live by the user
    (2026-10-01): "the transition stops moving due to hitting a
    bundle[']s length limit... it should... eliminate the need to
    'hard stop'... and allow[] the transition to be placed anywhere
    within the circle created by the limit." Recomputing the FULL
    delta fresh every frame from the drag's own fixed starting
    point(s) and the CURRENT mouse position, then finding the farthest
    reachable point along that line instead of refusing outright,
    removes the stuck state entirely: every frame's target is
    independent of whatever happened on the last one.

    :param point_starts: Every point this drag moves, each at its own
        position when the drag began (not the last frame) -- almost
        always one entry, except a Transition, whose branches all move
        by the same rigid delta its own center does.
    :param full_delta: The complete, unclamped ``(dx, dz)`` the current
        mouse position implies, applied identically to every point in
        *point_starts*.
    :param in_progress: Passed straight through to :func:`_commit_points`
        -- ``True`` (the default -- an ordinary mid-drag frame) holds
        every touched chain's own waypoint COUNT fixed, repositioning
        only, so dragging never inserts/deletes a DB row on every single
        frame (user's own spec, 2026-10-02). The drag's own very last
        call -- ``drag_handlers.editor_pegboard.generic.Generic.delete``,
        the moment the mouse button is released -- passes ``False`` to
        run the real, height-cap-derived reconcile exactly once, letting
        the count finally catch up to whatever it actually needs.
    :returns: The fraction of *full_delta* actually reachable, in
        ``[0, 1]`` -- ``0.0`` only when even the starting positions'
        own chains are somehow already infeasible (should not happen in
        practice; the pre-drag state already satisfies every chain's
        required length by construction). The caller is responsible
        for moving each point's own live position to
        ``start + t * full_delta`` -- this function only resolves/commits
        each affected chain's INTERIOR waypoints, exactly like the
        older single-shot check it replaces, never the anchor points
        themselves.
    """
    ptables = mainframe.project.ptables
    dx, dz = full_delta

    def candidate(t: float) -> list[tuple[bytes, tuple[float, float]]]:
        return [
            (point_id, (float(start.x) + dx * t, float(start.z) + dz * t))
            for point_id, start in point_starts]

    full_result = _evaluate_points(ptables, candidate(1.0))
    if full_result is not None:
        _commit_points(mainframe, *full_result, in_progress=in_progress)
        return 1.0

    lo, hi = 0.0, 1.0
    best_t = 0.0
    best_result = _evaluate_points(ptables, candidate(0.0))

    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        mid_result = _evaluate_points(ptables, candidate(mid))

        if mid_result is not None:
            lo = mid
            best_t = mid
            best_result = mid_result
        else:
            hi = mid

    if best_result is not None:
        _commit_points(mainframe, *best_result, in_progress=in_progress)

    return best_t


@_check_types.do
def realize_length_change(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]
) -> bool:
    """Re-solve *chain_db_obj*'s peg-board chain after its real 3D
    length changed (a ``BundleLayout``/``WireLayout`` marker was dragged
    in the 3D view) -- see the module docstring.

    Routed through the exact same :func:`_evaluate_points`/
    :func:`_commit_points` cascade a peg-board drag uses: this chain's
    own start anchor is "dragged" to its own current position (a
    no-move target -- the point ends up exactly where it already was),
    which still runs the ordinary check against every chain THAT point
    touches, this one included; the new ``length_mm`` is what makes
    THIS chain's own check come out differently than before. If this
    chain's own slack can't absorb the change with its far end held
    fixed, the far end -- and, now, whatever it cascades into: another
    Transition, a Housing, and so on -- is pulled exactly like a real
    drag would pull it. *chain_db_obj*'s own start point never actually
    moves (it's the thing nothing else in this call drags), but every
    other point touched by the cascade can, including this chain's own
    stop anchor.

    *path_table*/*layouts_table*/*layout_facade_cls* are no longer
    parameters here -- :func:`_chains_for_point` re-discovers them
    fresh for every chain the cascade touches, this one included, so
    there is nothing left for a caller to hand in.

    :returns: Whether the whole cascade this change triggers (if any)
        was feasible. ``False`` means something in it is infeasible
        even after every pull it allows -- a closed loop that doesn't
        fit (see :func:`_evaluate_points`'s own "why no explicit cycle
        detection" note) or genuinely nowhere left to pull -- and the
        peg-board side is deliberately left untouched rather than
        guessed at.
    """
    ptables = mainframe.project.ptables
    start_xz, _stop_xz, _required_length = _anchors_and_length(chain_db_obj)

    result = _evaluate_points(ptables, [(chain_db_obj.start_position_pegboard_id, start_xz)])
    if result is None:
        return False

    _commit_points(mainframe, *result)
    return True


@_check_types.do
def realize_3d_move(mainframe: "_ui.MainFrame", point3d_ids: list[bytes]) -> None:
    """Call :func:`realize_length_change` for every bundle/wire whose
    own start or stop 3D point is one of *point3d_ids* -- the 3D-side
    counterpart of :func:`resolve_rigid_move` for every anchor
    type OTHER than a ``BundleLayout``/``WireLayout`` marker (those are
    interior waypoints, found via :func:`_chains_for_point`'s
    path-table lookup instead, not a start/stop scan -- see
    ``drag_handlers.editor_3d.generic.Generic._realize_pegboard_length``,
    which calls whichever of the two actually applies).

    *point3d_ids* is plural for exactly the same reason
    :func:`resolve_rigid_move` takes several points: a Transition
    moves ALL of its branches' own points together, rigidly, and a
    bundle is anchored at a BRANCH's own point, never the transition's
    own center point -- the caller is responsible for gathering every
    one of a moved object's own real 3D point ids (one for a
    Housing/BundleLayout/WireLayout, two for a Splice/WireServiceLoop's
    start/stop, one per branch for a Transition).

    Each matched chain starts its own independent call to
    :func:`realize_length_change` -- unlike :func:`resolve_rigid_move`'s
    single shared resolve, there is no "every one must agree" step
    tying separate matched chains together here, since each one's own
    cascade (now, potentially reaching well beyond just this chain) is
    resolved and committed before the next matched chain's own call
    even starts. A chain (or its cascade) that's infeasible is simply
    left alone while every other matched chain still updates.
    """
    ptables = mainframe.project.ptables
    ids = set(point3d_ids)

    for bundle_db_obj in ptables.pjt_bundles_table:
        if bundle_db_obj.start_position3d_id in ids or bundle_db_obj.stop_position3d_id in ids:
            realize_length_change(mainframe, bundle_db_obj)

    for wire_db_obj in ptables.pjt_wires_table:
        if wire_db_obj.start_position3d_id in ids or wire_db_obj.stop_position3d_id in ids:
            realize_length_change(mainframe, wire_db_obj)
