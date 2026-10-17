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

A seated Terminal resolves to its own Housing (see :func:`_node_for_point`'s
own docstring) -- pulling a wire plugged into one seated terminal pulls
the whole housing, which cascades into every other wire plugged into
every OTHER terminal on that same housing too, each all the way to
whatever it in turn finds enough slack (or runs out and keeps
cascading). A free-standing/"ring" terminal (not seated in any cavity)
has nothing to cascade into, same as a genuinely free end.

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
(:func:`finalize_drag`, run by ``objects.project.Project.end_gesture`` on
the outermost gesture close), runs the real, height-cap-derived
reconcile exactly once, letting the count finally catch up to whatever
it actually needs. Every OTHER caller
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
import uuid

import numpy as np

from .. import rope_pull as _rope_pull
from ..rope_pull import offline_store as _offline_store
from .. import config as _config
from ..geometry import point as _point
from ..geometry.angle import angle as _angle
from ..objects import bundle_layout as _bundle_layout
from ..objects import wire_layout as _wire_layout
from ..database.project_db import pjt_bundle as _pjt_bundle
from . import wire_routing_handler as _wire_routing_handler
from .. import check_types as _check_types
from .. import debug as _debug


if TYPE_CHECKING:
    from ..database.project_db.pjt_pegboard_table import PJTPegboardTable as _PJTPegboardTable
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_bundle_path as _pjt_bundle_path
    from ..database.project_db import pjt_wire_path as _pjt_wire_path
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from ..database.project_db import pjt_wire_layout as _pjt_wire_layout


Config = _config.Config.editor_pegboard.rope_pull

# How many times one pulled node may be pulled again inside a single solve
# before the move is refused -- see _evaluate_points' pull_if_needed. Several
# wires between the same two housings settle in one or two; this only ends a
# loop that genuinely cannot fit.
_MAX_REPULLS = 16

# A re-pull smaller than this (mm) is floating-point noise, not a chain that
# still needs relief -- matches solve_chain's own default tolerance.
_REPULL_TOLERANCE_MM = 1e-6


@_debug.logfunc
@_check_types.do
def is_enabled() -> bool:
    """Whether the rope-pull solver is on (``Config.editor_pegboard.rope_pull.enabled``,
    toggled from the Peg Board toolbar). Off, drag handlers fall back to the
    per-edge length clamp and the 3D side does not re-solve the peg-board."""
    return bool(Config.enabled)


@_debug.logfunc
@_check_types.do
def _chain_diameter(
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]
) -> float:
    """The diameter the zig-zag rules scale by: a bundle's own effective
    diameter (``PJTBundle.diameter``, see ``handlers.bundle_diameter``), or a
    wire's own conductor OD (``part.od_mm``)."""
    from ..database.project_db import pjt_bundle as _pjt_bundle_runtime

    if isinstance(chain_db_obj, _pjt_bundle_runtime.PJTBundle):
        return float(chain_db_obj.diameter)

    return float(chain_db_obj.part.od_mm)


@_debug.logfunc
@_check_types.do
def _structural_stub_ids(ptables: "_PJTPegboardTable", attach_point_id: bytes | None) -> list[bytes]:
    """The real (canonical, never a per-wire clone) terminal/cavity
    wire-stub point ids anchored at *attach_point_id* -- a wire's own
    real start/stop anchor (``PJTTerminal.attach_position_pegboard_id``,
    the ONLY thing ``Terminal.add_wire`` ever uses as a wire's own
    start/stop_position, never an interior waypoint), nearest-the-
    terminal first: the terminal's own ``wire_position_pegboard``, then
    (only when seated in a cavity) that cavity's own
    ``wire_position_pegboard`` -- exactly ``Terminal.add_wire``'s own
    construction order for a 'start' attach (reversed on disk for a
    'stop' attach, but reading *backward* from a wire's own stop anchor
    lands on this same nearest-terminal-first order -- see
    :func:`_stub_boundary`, this function's only caller).

    These two points are fixed offsets from the terminal's/cavity's own
    structural geometry, already carried along rigidly whenever the
    terminal/housing moves (``Terminal._own_or_cloned_point_id``'s own
    ``parent_point_id`` -> ``PJTHousing._update_position3d``/
    ``_update_position_pegboard`` cascade) -- never something the
    rope-pull solver should reposition, or delete/recreate as an
    ordinary free zigzag waypoint, which is exactly what was happening
    before this existed: confirmed live, 2026-10-13, dragging a housing
    with only two wires attached visibly corrupted both wires' own
    near-terminal points, because ``solve_chain`` was being handed the
    terminal's raw ``attach_position_pegboard`` as its anchor and told
    these two fixed points were free interior slack, same as any
    ordinary bend. Empty when *attach_point_id* isn't a terminal's
    attach point at all (a free/dangling end, a splice, a wire-service-
    loop, ...).
    """
    if attach_point_id is None:
        return []

    rows = ptables.pjt_terminals_table.select('id', attach_point_pegboard_id=attach_point_id)
    if not rows:
        return []

    terminal = ptables.pjt_terminals_table[rows[0][0]]
    ids = []

    stub_id = terminal.wire_position_pegboard_id_raw
    if stub_id is not None:
        ids.append(stub_id)

    cavity_id = terminal.cavity_id
    if cavity_id is not None:
        cavity = ptables.pjt_cavities_table[cavity_id]
        cavity_stub_id = cavity.wire_position_pegboard_id_raw
        if cavity_stub_id is not None:
            ids.append(cavity_stub_id)

    return ids


@_debug.logfunc
@_check_types.do
def _canonical_point_id(points_table: object, point_id: bytes) -> bytes:
    """*point_id*'s own canonical identity -- itself, or whatever
    ``parent_point_id`` it was cloned from (every terminal/cavity stub
    past the first wire on that terminal is a clone at the same spot,
    tagged this way so it still tracks the real point's own future
    movement -- see ``Terminal._own_or_cloned_point_id``)."""
    parent_id = points_table[point_id].parent_point_id
    return parent_id if parent_id is not None else point_id


@_debug.logfunc
@_check_types.do
def _stub_boundary(ptables: "_PJTPegboardTable", wire_db_obj: "_pjt_wire.PJTWire") -> tuple[int, int]:
    """How many of *wire_db_obj*'s own leading (start-side) and trailing
    (stop-side) peg-board interior waypoints are terminal/cavity
    structural stubs (see :func:`_structural_stub_ids`) -- ``(0, 0)``
    for either end that isn't attached to a terminal at all.

    Verifies identity (via :func:`_canonical_point_id`) against the
    expected ids rather than just trusting the expected count, so a
    chain that somehow doesn't match ``Terminal.add_wire``'s usual
    construction order degrades to excluding nothing for that end
    instead of silently excluding the wrong points. Clamped so the two
    ends' own counts can never overlap and claim the same point twice,
    for a wire short enough that its whole interior is just these
    stubs.
    """
    old_ids = list(ptables.pjt_wire_paths_table.point_ids(wire_db_obj.db_id, 'pegboard'))
    points_table = ptables.pjt_points_pegboard_table

    def count(expected_ids: list[bytes], from_tail: bool) -> int:
        found = 0
        for i, expected in enumerate(expected_ids):
            index = len(old_ids) - 1 - i if from_tail else i
            if index < 0 or index >= len(old_ids):
                break
            if _canonical_point_id(points_table, old_ids[index]) != expected:
                break
            found += 1
        return found

    leading = count(_structural_stub_ids(ptables, wire_db_obj.start_position_pegboard_id), False)
    trailing = count(_structural_stub_ids(ptables, wire_db_obj.stop_position_pegboard_id), True)

    if leading + trailing > len(old_ids):
        overlap = leading + trailing - len(old_ids)
        if trailing >= leading:
            trailing -= overlap
        else:
            leading -= overlap

    return leading, trailing


@_debug.logfunc
@_check_types.do
def stub_boundary_for_chain(
    ptables: "_PJTPegboardTable", chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]
) -> tuple[int, int]:
    """``(0, 0)`` for a bundle -- a bundle never attaches through a
    terminal the way a wire does, see :func:`_stub_boundary`.

    Public (no leading underscore): also used by
    ``handlers.wire_slack_handler.WireSlackHandler.register_pegboard``
    to decide which of a wire's own structural stub points are
    rigidly-coupled duplicates of the SAME housing move, and so don't
    each need their own binding -- see that method's own docstring.
    """
    if isinstance(chain_db_obj, _pjt_bundle.PJTBundle):
        return 0, 0

    return _stub_boundary(ptables, chain_db_obj)


@_debug.logfunc
@_check_types.do
def _distance3d(a: "_point.Point", b: "_point.Point") -> float:
    dx = float(b.x) - float(a.x)
    dy = float(b.y) - float(a.y)
    dz = float(b.z) - float(a.z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


@_debug.logfunc
@_check_types.do
def _wire_stub_length3d(wire_db_obj: "_pjt_wire.PJTWire", leading: int, trailing: int) -> float:
    """Real 3D length of *wire_db_obj*'s own leading/trailing structural
    stub segment(s) -- see :func:`_stub_boundary`. Walked over
    ``waypoints3d`` (not the peg-board list) since this is subtracted
    from ``length_mm``, itself a pure 3D measurement (see
    ``PJTWire.length_mm``'s own docstring)."""
    if not leading and not trailing:
        return 0.0

    points = [wire_db_obj.start_position3d, *(wp.point for wp in wire_db_obj.waypoints3d),
              wire_db_obj.stop_position3d]

    total = 0.0
    if leading:
        for a, b in zip(points[:leading], points[1:leading + 1]):
            total += _distance3d(a, b)
    if trailing:
        for a, b in zip(points[-trailing - 1:-1], points[-trailing:]):
            total += _distance3d(a, b)
    return total


@_debug.logfunc
@_check_types.do
def _anchors_and_length(
    ptables: "_PJTPegboardTable", chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]
) -> tuple[tuple[float, float], tuple[float, float], float, int, int]:
    """*chain_db_obj*'s two EFFECTIVE peg-board anchors as plain
    ``(x, z)`` tuples, the EFFECTIVE length the rope-pull solver should
    treat as available slack between them, and the leading/trailing
    terminal-stub counts (see :func:`_stub_boundary`) every caller that
    touches this chain's own interior needs to exclude from it --
    exactly what ``rope_pull.solve_chain`` needs, plus what
    :func:`_reconcile_interior`/:func:`_apply_mid_drag` need, read fresh
    every call since ``length_mm`` has no cache/signal of its own
    (confirmed: a plain computed property, see its own docstring on
    ``PJTBundle``/``PJTWire``).

    For a bundle, or a wire whose end isn't attached to a terminal,
    "effective" is simply the chain's own real start/stop anchor and
    its real ``length_mm``, same as always. For a wire attached to a
    terminal, it instead means: past that terminal's own fixed
    wire-stub point (and, if seated, past its cavity's own wire-stub
    point too) -- see :func:`_structural_stub_ids` for why those points
    are never part of the solver's own free interior. The fixed 3D
    length of whatever stub segment(s) this excludes is subtracted from
    ``length_mm``, since that portion of the wire's real length is
    consumed by fixed housing/connector geometry, never available as 2D
    zigzag slack.
    """
    start = chain_db_obj.start_position_pegboard
    stop = chain_db_obj.stop_position_pegboard
    length = chain_db_obj.length_mm

    leading, trailing = stub_boundary_for_chain(ptables, chain_db_obj)

    if leading or trailing:
        length -= _wire_stub_length3d(chain_db_obj, leading, trailing)

        if leading:
            start = chain_db_obj.waypoints_pegboard[leading - 1].point
        if trailing:
            stop = chain_db_obj.waypoints_pegboard[-trailing].point

    return (float(start.x), float(start.z)), (float(stop.x), float(stop.z)), length, leading, trailing


@_debug.logfunc
@_check_types.do
def _reconcile_interior(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    path_table: _Union["_pjt_bundle_path.PJTBundlePathsTable", "_pjt_wire_path.PJTWirePathsTable"],
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    layout_facade_cls: _Union[type["_bundle_layout.BundleLayout"], type["_wire_layout.WireLayout"]],
    new_interior: list[tuple[float, float]],
    pin_point_id: bytes | None,
    pin_xz: tuple[float, float] | None,
    leading: int = 0,
    trailing: int = 0
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

    *leading*/*trailing* (``_anchors_and_length``'s own terminal-stub
    exclusion counts, see :func:`_stub_boundary`) are how many of this
    chain's own real interior point ids -- read fresh below, before
    anything else happens -- are fixed terminal/cavity structural stubs
    carved out before the reuse/insert/delete dance runs and spliced
    back verbatim at the very end: never reused, repositioned, or
    deleted here, same as *new_interior* itself never includes them
    (the caller's own *start_xz*/*stop_xz* already stopped short of
    them). Without this, collapsing a wire's free interior to zero
    (a straight, taut run) could delete these two points outright,
    which doesn't just mis-place them -- a wire with no interior
    waypoints at a Terminal end renders as one single bare-conductor
    segment end to end (``objects_pegboard.wire.Wire.render``'s own
    ``_conductor_segment_ends``), losing its insulation color AND its
    stripe, confirmed live, 2026-10-13, alongside the position
    corruption this same gap caused.
    """
    project = mainframe.project
    points_table = project.ptables.pjt_points_pegboard_table

    old_ids = list(path_table.point_ids(chain_db_obj.db_id, 'pegboard'))

    if pin_point_id is not None and (leading or trailing):
        boundary_ids = set(old_ids[:leading]) | set(old_ids[len(old_ids) - trailing:])
        if pin_point_id in boundary_ids:
            leading = trailing = 0

    tail_start = len(old_ids) - trailing
    structural_lead_ids = old_ids[:leading]
    structural_tail_ids = old_ids[tail_start:]
    old_ids = old_ids[leading:tail_start]

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
    # facade object for each come after set_route, below. Each insert()/
    # delete() below runs inside the drag's own open gesture and defers
    # into the project's row cache rather than touching the database
    # per row -- see PJTTableBase.insert/delete's own comments.
    new_indexes = []
    for i in range(reuse_count, len(remaining_new_indexes)):
        new_index = remaining_new_indexes[i]
        x, z = new_interior[new_index]
        point_db = points_table.insert(x, 0.0, z)
        final_ids[new_index] = point_db.db_id
        new_indexes.append(new_index)

    removed_ids = remaining_old_ids[reuse_count:]

    path_table.set_route(
        chain_db_obj.db_id, 'pegboard', structural_lead_ids + final_ids + structural_tail_ids)

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


@_debug.logfunc
@_check_types.do
def _anchor_index(ptables: "_PJTPegboardTable") -> dict[bytes, list[tuple]]:
    """Every bundle/wire in *ptables*, indexed by the point id(s) it
    anchors (its start and/or stop) -- the reverse of the one-chain-at-
    a-time scan :func:`_chains_for_point` used to do per call. Built
    once and reused across every :func:`_chains_for_point` lookup that
    shares the same *cache* (see its own docstring) -- a resolve's whole
    binary search re-asks this question up to 34 times per mouse move
    (:func:`resolve_rigid_move`/:func:`resolve_local_move`/
    :func:`_resolve_pinned_move`) without the DB changing in between
    (``_evaluate_points`` is a pure, read-only solve), so the
    bundles+wires scan this builds from need happen only once per
    resolve instead of once per lookup.

    START-before-STOP precedence: a chain whose start and stop anchor
    the SAME point (a degenerate zero-length chain) gets exactly one
    entry there, tagged START, not two -- matching what the old
    per-chain scan (START checked, then STOP only if different) would
    have produced for that one chain.
    """
    index: dict[bytes, list[tuple]] = {}

    def add(chain_db_obj, path_table, layouts_table, layout_facade_cls) -> None:
        start_id = chain_db_obj.start_position_pegboard_id
        stop_id = chain_db_obj.stop_position_pegboard_id
        index.setdefault(start_id, []).append((
            chain_db_obj, path_table, layouts_table, layout_facade_cls, _rope_pull.DragEnd.START))
        if stop_id != start_id:
            index.setdefault(stop_id, []).append((
                chain_db_obj, path_table, layouts_table, layout_facade_cls, _rope_pull.DragEnd.STOP))

    for bundle_db_obj in ptables.pjt_bundles_table:
        add(bundle_db_obj, ptables.pjt_bundle_paths_table, ptables.pjt_bundle_layouts_table, _bundle_layout.BundleLayout)

    for wire_db_obj in ptables.pjt_wires_table:
        add(wire_db_obj, ptables.pjt_wire_paths_table, ptables.pjt_wire_layouts_table, _wire_layout.WireLayout)

    return index


@_debug.logfunc
@_check_types.do
def _chains_for_point(
    ptables: "_PJTPegboardTable", point_id: bytes, cache: dict | None = None
) -> list[tuple]:
    """Every chain (bundle or wire) that *point_id* is part of, each as
    ``(chain_db_obj, path_table, layouts_table, layout_facade_cls,
    drag_end)`` -- ``drag_end`` is :attr:`rope_pull.DragEnd.WAYPOINT` if
    *point_id* is an interior waypoint (at most one chain, by
    construction -- a waypoint belongs to exactly one bundle/wire), or
    :attr:`~rope_pull.DragEnd.START`/:attr:`~rope_pull.DragEnd.STOP` for
    every chain *point_id* anchors (zero or more -- e.g. several wires
    entering the same housing, or a bundle plugged into one of a
    transition's branches).

    *cache*: an optional dict a caller making several of these calls
    against the same (unwritten) *ptables* state can pass in to share
    the anchor-side lookup's one-time index (:func:`_anchor_index`)
    across all of them instead of rebuilding it per call -- see that
    function's own docstring. ``None`` (the default) rebuilds it fresh
    every call, exactly like the old unconditional per-call scan.
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

    if cache is None:
        index = _anchor_index(ptables)
    else:
        index = cache.get('anchor_index')
        if index is None:
            index = cache['anchor_index'] = _anchor_index(ptables)

    return list(index.get(point_id, ()))


@_debug.logfunc
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


@_debug.logfunc
@_check_types.do
def _node_for_point(ptables: "_PJTPegboardTable", point_id: bytes) -> tuple[str, list[bytes]] | None:
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

    **A seated Terminal resolves to its own Housing.** *point_id* being
    a terminal's real wire-attachment point
    (``PJTTerminal.attach_position_pegboard_id``) does not by itself
    mean a Housing owns it -- a free-standing/"ring" terminal (not
    seated in any cavity) has nothing further to cascade into, same as
    a genuinely free end -- but a SEATED terminal's own attach point
    moves rigidly with its housing already
    (``PJTHousing._update_position_pegboard``'s own cavity/terminal
    cascade, bound the moment anything first reads the housing's own
    ``position_pegboard``), the exact same mechanism a Transition's
    branch tips already use (``objects_pegboard.transition.
    Transition._update_position`` -> ``write_tips_to_db``). *points*
    for a seated terminal is therefore the housing's own point PLUS
    every OTHER seated terminal's own attach point across every one of
    that housing's own cavities -- not just the one point_id arrived
    through -- so :func:`_evaluate_points`'s own cascade actually
    visits (and can refuse the whole move over) every wire plugged
    into this housing, not only the one that triggered the pull.
    Deliberately excludes each terminal's OWN ``wire_position_pegboard``/
    its cavity's ``wire_position_pegboard`` (the structural stub points
    :func:`_structural_stub_ids` excludes from a wire's own free
    interior) -- those are interior WAYPOINTS of their own wire, not a
    second real anchor, and feeding one into this cascade as if it were
    a draggable point would wrongly treat it as a WAYPOINT drag target
    (see :func:`_chains_for_point`'s own ``DragEnd.WAYPOINT`` case).
    """
    if ptables.pjt_housings_table.select('id', point_pegboard_id=point_id):
        return 'rigid', [point_id]

    terminal_rows = ptables.pjt_terminals_table.select('id', attach_point_pegboard_id=point_id)
    if terminal_rows:
        terminal = ptables.pjt_terminals_table[terminal_rows[0][0]]
        cavity_id = terminal.cavity_id

        if cavity_id is not None:
            housing_rows = ptables.pjt_cavities_table.select('housing_id', id=cavity_id)
            housing_id = housing_rows[0][0] if housing_rows else None

            if housing_id is not None:
                housing = ptables.pjt_housings_table[housing_id]
                points = [housing.position_pegboard_id]

                for other_cavity in housing.cavities:
                    other_terminal = other_cavity.terminal
                    if other_terminal is None:
                        continue

                    attach_id = other_terminal.attach_position_pegboard_id_raw
                    if attach_id is not None:
                        points.append(attach_id)

                return 'rigid', points

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


@_debug.logfunc
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


@_debug.logfunc
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


@_debug.logfunc
@_check_types.do
def _evaluate_points(
    ptables: "_PJTPegboardTable", point_targets: list[tuple[bytes, tuple[float, float]]],
    cascade: bool = True, chain_cache: dict | None = None,
) -> tuple[list[tuple], dict[bytes, tuple[float, float]], dict[bytes, float]] | None:
    """Pure solve, no DB writes -- every ``(point_id, target_xz)`` pair
    in *point_targets* moving AT ONCE, cascading through whatever else
    needs to move as a result (see the module docstring's own "The
    cascade" section for the rule in plain words).

    *chain_cache*: forwarded to every :func:`_chains_for_point` call
    this makes (see that function's own *cache* parameter). ``None``
    (the default) builds one locally so this call's own repeated
    lookups -- one per :func:`pull_node`, one per point popped off
    *pending* -- still share a single anchor-index build instead of
    one each; a caller making several of these calls back to back
    against the same unwritten *ptables* (every binary-search resolver
    in this module) passes its own dict in to share that index across
    the whole search too.

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
    the whole move on a cycle" policy (user, 2026-10-01).** A DRAGGED
    point is authoritative and never moved. A point an earlier pull
    decided can be pulled again -- by whatever a later chain still
    needs on top (several wires between the same two housings each
    need a different amount, and which one is processed first depends
    on seed order, so "first one wins" refused the move in one drag
    direction and not the other) -- but only up to ``_MAX_REPULLS``
    times per node, and every chain already solved against its old
    position is forgotten and solved again. A closed loop (several Transitions/
    bundles forming a ring, say) therefore either happens to still fit
    once every node along it has been independently pulled this way --
    accepted, nothing further needed, a strictly BETTER outcome than
    refusing a ring that actually had enough slack to flex -- or it
    doesn't, and whichever chain closes the loop fails the ordinary
    ``solve_chain`` feasibility check against the two now-fixed ends it
    can no longer move, which already returns ``None`` below. Both
    outcomes satisfy the chosen policy without a solver for the loop's
    simultaneous constraints ever being written.

    :returns: ``(entries, write_points, write_yaws)`` -- *entries* is
        every ``(chain_db_obj, path_table, layouts_table,
        layout_facade_cls, drag_end, point_id, target_xz, result,
        start_xz, stop_xz, required_length, leading, trailing)``
        :func:`_commit_points` needs to reconcile each chain's own
        interior -- *leading*/*trailing* are :func:`_anchors_and_length`'s
        own terminal-stub exclusion counts, carried through so
        :func:`_reconcile_interior`/:func:`_apply_mid_drag` never touch
        those points either -- and *write_points*/*write_yaws* are every
        ``point_id -> (x, z)``/``center_id -> phi`` a pull decided that
        isn't one of *point_targets* itself (the caller already owns
        moving those). ``None`` if anything, anywhere in the whole
        cascade, is infeasible even after every pull it allows.
    """
    points_table = ptables.pjt_points_pegboard_table
    if chain_cache is None:
        chain_cache = {}

    fixed: dict[bytes, tuple[float, float]] = dict(point_targets)
    write_points: dict[bytes, tuple[float, float]] = {}
    write_yaws: dict[bytes, float] = {}
    pending: list[bytes] = [point_id for point_id, _ in point_targets]
    seen_chains: set[bytes] = set()
    entries = []

    # How many times each pulled node (keyed by its first point id) has been
    # pulled AGAIN after its first pull in this solve -- see pull_node. A
    # node that keeps being re-pulled never settles (a closed loop that does
    # not fit): past _MAX_REPULLS it is left where it is and the chain is
    # left to fail its own feasibility check, which refuses the move.
    repulls: dict[bytes, int] = {}

    def pull_node(
        point_id: bytes, from_xz: tuple[float, float], to_xz: tuple[float, float],
        chain_id: bytes, is_repull: bool
    ) -> bool:
        """Move the rigid node that owns *point_id* so that point's
        EFFECTIVE position goes from *from_xz* to *to_xz*, deciding every
        one of the node's points in fixed/write_points and queuing them.

        *is_repull*: the node was already pulled earlier in this solve, so
        its points move on from where this solve put them (fixed[]) instead
        of from where the DB has them.

        :returns: ``False`` when a re-pull would exceed _MAX_REPULLS -- the
            node is left untouched.
        """
        node = _node_for_point(ptables, point_id)
        kind, node_points = ('rigid', [point_id]) if node is None else node

        if is_repull:
            repull_count = repulls.get(node_points[0], 0) + 1
            repulls[node_points[0]] = repull_count
            if repull_count > _MAX_REPULLS:
                return False

        def moved_from(p: bytes) -> tuple[float, float]:
            # A first pull moves a point from where the DB has it; a
            # re-pull from where this solve already put it.
            if is_repull:
                return fixed[p]

            p_point = points_table[p].point
            return float(p_point.x), float(p_point.z)

        if kind == 'transition':
            # BUNDLE_PLACEMENT.md section 6's own pivot/trailing rule:
            # point_id IS the branch the pull arrives through (the
            # "handle"), always node_points[1:]'s member, never the
            # centre -- a bundle/wire anchors at a branch's own point,
            # never a transition's bare centre point (see this module's
            # own docstring's "anchor model"). phi is the rotation that
            # points the vector from the handle to the transition's own
            # (pre-pull) centre in the direction OPPOSITE the pull, so
            # the body trails behind the branch being pulled, same as
            # the real world. A re-pull rotates the already-pulled pose
            # again about the handle's current spot; the yaws add up.
            center_id = node_points[0]
            center_old = moved_from(center_id)

            dx = to_xz[0] - from_xz[0]
            dz = to_xz[1] - from_xz[1]
            vx = center_old[0] - from_xz[0]
            vz = center_old[1] - from_xz[1]

            if math.hypot(dx, dz) < 1e-9 or math.hypot(vx, vz) < 1e-9:
                phi = 0.0
            else:
                phi = math.atan2(vz, vx) - math.atan2(-dz, -dx)

            write_yaws[center_id] = write_yaws.get(center_id, 0.0) + phi

            for p in node_points:
                new_xz = _rotated_and_translated(moved_from(p), from_xz, to_xz, phi)
                fixed[p] = new_xz
                write_points[p] = new_xz
                pending.append(p)
        else:
            delta = (to_xz[0] - from_xz[0], to_xz[1] - from_xz[1])

            for p in node_points:
                p_xz = moved_from(p)
                new_xz = (p_xz[0] + delta[0], p_xz[1] + delta[1])
                fixed[p] = new_xz
                write_points[p] = new_xz
                pending.append(p)

        # Every OTHER chain already evaluated against this node's old
        # position is stale now -- its interior was solved against an
        # anchor that has since moved. Forget it, so it is evaluated again
        # from the pulled node's side.
        stale_ids: set[bytes] = set()
        for p in node_points:
            for touching in _chains_for_point(ptables, p, chain_cache):
                if touching[0].db_id != chain_id:
                    stale_ids.add(touching[0].db_id)

        if stale_ids:
            seen_chains.difference_update(stale_ids)
            entries[:] = [entry for entry in entries if entry[0].db_id not in stale_ids]

        return True

    def pull_if_needed(
        chain_id: bytes, far_point_id: bytes, far_xz: tuple[float, float],
        near_target_xz: tuple[float, float], required_length: float
    ) -> tuple[float, float]:
        is_repull = False

        if far_point_id in fixed:
            # fixed[] holds the far end's RAW (terminal attach point) new
            # position, but far_xz is the EFFECTIVE anchor -- already past
            # the terminal/cavity structural stubs (see _anchors_and_length)
            # -- and so is what the solver, and the stub-excluded
            # required_length, expect back. Every one of those stubs rides
            # rigidly with the same housing, so the effective anchor moves
            # by exactly the delta the raw point does; returning the raw
            # position outright put the anchor a stub length too far out
            # (the interior then aimed at the crimp point instead of the
            # cavity stub, or the move refused). A free end has no stubs,
            # so raw == effective and this reduces to fixed[far_point_id].
            far_raw = points_table[far_point_id].point
            far_xz = (
                far_xz[0] + fixed[far_point_id][0] - float(far_raw.x),
                far_xz[1] + fixed[far_point_id][1] - float(far_raw.z))

            # A dragged point's own target is authoritative -- never moved
            # here. A point an EARLIER PULL in this same solve decided is
            # not: several wires between the same two housings each pull
            # the far housing only as far as that one wire needs, so
            # whichever happens to be processed first used to fix the
            # housing where it alone was relieved, and a longer-run-out
            # sibling processed second found it "already decided" and
            # could not pull it any further -- the whole move was refused
            # and the dragged housing just stopped, in one drag direction
            # and not the other (which housing is dragged decides which
            # wire comes first). The node is pulled again by whatever this
            # chain still needs on top.
            if far_point_id not in write_points or not cascade:
                return far_xz

            is_repull = True
        elif not cascade:
            return far_xz

        pulled_xz = _pulled_far_position(far_xz, near_target_xz, required_length)
        if is_repull:
            if math.hypot(pulled_xz[0] - far_xz[0], pulled_xz[1] - far_xz[1]) <= _REPULL_TOLERANCE_MM:
                return far_xz
        elif pulled_xz == far_xz:
            return far_xz

        if not pull_node(far_point_id, far_xz, pulled_xz, chain_id, is_repull):
            return far_xz

        return pulled_xz

    while pending:
        point_id = pending.pop()
        target_xz = fixed[point_id]

        for chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end in _chains_for_point(
            ptables, point_id, chain_cache
        ):
            if chain_db_obj.db_id in seen_chains:
                continue
            seen_chains.add(chain_db_obj.db_id)

            start_xz, stop_xz, required_length, leading, trailing = _anchors_and_length(
                ptables, chain_db_obj)

            # target_xz is where point_id -- the chain's own RAW
            # start/stop anchor (a terminal's attach_position_pegboard)
            # -- is headed. When this end has its own leading/trailing
            # stub exclusion, that is NOT where the solver's own anchor
            # for this end should land: the EFFECTIVE anchor (start_xz/
            # stop_xz above, already past the stub -- the terminal's
            # own wire_position_pegboard, or the cavity's if seated,
            # see _stub_boundary) moves by the exact same rigid delta
            # (never a different one -- the whole terminal/housing only
            # ever translates), so it is this end's own OLD effective
            # position plus that same delta, not target_xz itself.
            # Using target_xz directly here measured every zig-zag span
            # from the terminal's own raw crimp point instead, double-
            # counting the stub segment's own length against a
            # required_length that had already excluded it -- confirmed
            # live, 2026-10-13: a housing's own terminal never let its
            # wire reach taut/pull its far end correctly, because the
            # solver always saw less slack than the chain actually had.
            effective_target = target_xz
            if drag_end is _rope_pull.DragEnd.START and leading:
                raw_anchor = chain_db_obj.start_position_pegboard
                effective_target = (
                    start_xz[0] + (target_xz[0] - float(raw_anchor.x)),
                    start_xz[1] + (target_xz[1] - float(raw_anchor.z)))
            elif drag_end is _rope_pull.DragEnd.STOP and trailing:
                raw_anchor = chain_db_obj.stop_position_pegboard
                effective_target = (
                    stop_xz[0] + (target_xz[0] - float(raw_anchor.x)),
                    stop_xz[1] + (target_xz[1] - float(raw_anchor.z)))

            if drag_end is _rope_pull.DragEnd.START:
                stop_xz = pull_if_needed(
                    chain_db_obj.db_id, chain_db_obj.stop_position_pegboard_id, stop_xz,
                    effective_target, required_length)
            elif drag_end is _rope_pull.DragEnd.STOP:
                start_xz = pull_if_needed(
                    chain_db_obj.db_id, chain_db_obj.start_position_pegboard_id, start_xz,
                    effective_target, required_length)
            # DragEnd.WAYPOINT: both real anchors stay exactly as read --
            # the anchor model never lets a waypoint drag move them, and
            # a waypoint belongs to exactly one chain by construction,
            # so nothing ever cascades INTO this branch either.

            # The near end can itself be a point an earlier pull in this
            # solve moved (this chain is being evaluated from the pulled
            # node's side, with its far end a dragged -- authoritative --
            # point). If it still does not fit, the node is the only thing
            # that can give: pull it again toward the far end by whatever
            # is still missing, instead of refusing the move.
            if cascade and drag_end is not _rope_pull.DragEnd.WAYPOINT and point_id in write_points:
                other_xz = stop_xz
                if drag_end is _rope_pull.DragEnd.STOP:
                    other_xz = start_xz

                relieved_xz = _pulled_far_position(effective_target, other_xz, required_length)
                shift = math.hypot(
                    relieved_xz[0] - effective_target[0], relieved_xz[1] - effective_target[1])

                if shift > _REPULL_TOLERANCE_MM:
                    if pull_node(point_id, effective_target, relieved_xz, chain_db_obj.db_id, True):
                        effective_target = relieved_xz
                        target_xz = fixed[point_id]

            result = _rope_pull.solve_chain(
                start_xz, stop_xz, required_length, drag_end, effective_target,
                _chain_diameter(chain_db_obj), Config.zigzag_length_factor, Config.threshold_factor)

            if not result.accepted:
                return None

            entries.append((
                chain_db_obj, path_table, layouts_table, layout_facade_cls,
                drag_end, point_id, target_xz, result, start_xz, stop_xz, required_length,
                leading, trailing))

    return entries, write_points, write_yaws


# How many _commit_points calls are on the stack right now -- see
# is_committing(). Module level on purpose: the slack handler it protects
# is per wire, but a commit moves points belonging to several wires at once.
_commit_depth: int = 0


@_debug.logfunc
@_check_types.do
def is_committing() -> bool:
    """Whether :func:`_commit_points` is running right now.

    Every peg-board write this module makes goes through
    :func:`_commit_points`, and it already reconciles every chain its
    cascade touched. ``Point +=`` fires bound callbacks synchronously, so
    without this the per-wire ``WireSlackHandler`` safety net re-entered
    ``realize_length_change`` -> ``_apply_mid_drag`` from inside the
    ``_place_active`` loop of an outer commit, on the very same overlay
    list and offline store, with the outer call's ``tail_start`` already
    stale -- which drops or reorders a both-ends-terminal-attached wire's
    far-end stub entries (a free end has no trailing stubs, so it
    survived). The slack handler checks this and stays out of a commit.
    """
    return _commit_depth > 0


@_debug.logfunc
@_check_types.do
def _commit_points(
    mainframe: "_ui.MainFrame", entries: list[tuple], write_points: dict[bytes, tuple[float, float]],
    write_yaws: dict[bytes, float], in_progress: bool = False
) -> None:
    """Run :func:`_commit_points_body` with :func:`is_committing` true, so
    nothing it moves can re-enter a wire's own slack handler -- see
    :func:`is_committing`. Exception-safe: the depth is always restored.
    """
    global _commit_depth

    _commit_depth += 1
    try:
        _commit_points_body(mainframe, entries, write_points, write_yaws, in_progress)
    finally:
        _commit_depth -= 1


@_debug.logfunc
@_check_types.do
def _commit_points_body(
    mainframe: "_ui.MainFrame", entries: list[tuple], write_points: dict[bytes, tuple[float, float]],
    write_yaws: dict[bytes, float], in_progress: bool = False
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
    ptables = mainframe.project.ptables
    points_table = ptables.pjt_points_pegboard_table

    # Yaw first, then points: the transition's own angle callback rebuilds
    # its branch tips from whatever position/angle it holds at that moment,
    # so the point writes below must run last to leave the cached Points
    # and the DB rows agreeing with the new pose.
    for center_id, phi in write_yaws.items():
        transition_rows = ptables.pjt_transitions_table.select('id', point_pegboard_id=center_id)
        transition = ptables.pjt_transitions_table[transition_rows[0][0]]
        angle = transition.angle_pegboard
        angle += _angle.Angle.from_axis_angle(np.array([0.0, 1.0, 0.0]), phi)

    # Apply each move as a delta with += on the cached Point: plain x/z
    # assignment never fires the bound callbacks that write the row back
    # to the DB and refresh every live view holding this Point.
    for point_id, (x, z) in write_points.items():
        # _move_point's own no-op short-circuit applies here too: a
        # cascade-pulled anchor this solve decided doesn't actually
        # need to move (its own far-end delta already rounded to
        # nothing) shouldn't fire every one of its bound callbacks --
        # WireSlackHandler among them, for a wire/bundle anchor -- for
        # a write that changes nothing.
        _move_point(points_table[point_id].point, x, z)

    for (
        chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end, point_id, target_xz,
        result, start_xz, stop_xz, required_length, leading, trailing
    ) in entries:
        interior = result.points[1:-1]
        pin_point_id = point_id if drag_end is _rope_pull.DragEnd.WAYPOINT else None
        pin_xz = target_xz if drag_end is _rope_pull.DragEnd.WAYPOINT else None

        if in_progress or _offline_store.overlay(chain_db_obj.db_id) is not None:
            _apply_mid_drag(
                mainframe, chain_db_obj, path_table, layouts_table,
                drag_end, interior, start_xz, stop_xz, pin_point_id, pin_xz, leading, trailing)

            if not in_progress:
                _commit_overlay(mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls)
        else:
            _reconcile_interior(
                mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls,
                interior, pin_point_id, pin_xz, leading, trailing)

        # A bundle's own peg-board interior just got its REAL (not
        # overlay) shape written -- the 3D-side counterpart of this is
        # drag_handlers.editor_3d.generic.py's own guard-reposition
        # hooks; this is the one shared place every peg-board path that
        # changes a bundle's interior (a genuine peg-board drag's own
        # release frame, or a 3D-triggered realize_length_change) ends
        # up, so one hook here covers all of them. Skipped while
        # in_progress=True (an ordinary mid-drag frame): that writes
        # only the in-memory overlay, never real pjt_bundle_paths rows,
        # so recomputing from bundle.waypoints_pegboard here would read
        # stale pre-drag positions -- the guard catches up once this
        # runs for real, at release or a non-dragging realize.
        if not in_progress and isinstance(chain_db_obj, _pjt_bundle.PJTBundle):
            _wire_routing_handler.reposition_guards_for_bundle_end(
                ptables, chain_db_obj, chain_db_obj.start_position_pegboard, 'pegboard')
            _wire_routing_handler.reposition_guards_for_bundle_end(
                ptables, chain_db_obj, chain_db_obj.stop_position_pegboard, 'pegboard')


class _Waypoint:
    """One entry in a drag's working waypoint list: a database-backed point
    (``point_id`` set), or an in-memory point created mid-drag with a pseudo
    layout (``point_id`` None until the drag releases and the row is written).
    """

    __slots__ = ('point_id', 'point', 'pseudo_layout')

    def __init__(
        self, point_id: bytes | None, point: "_point.Point", pseudo_layout: object | None
    ) -> None:
        self.point_id = point_id
        self.point = point
        self.pseudo_layout = pseudo_layout


@_debug.logfunc
def _make_pseudo_layout(chain_db_obj: object, position: "_point.Point") -> object:
    """A pseudo layout (never a database row) carrying *position* for a new
    in-memory waypoint, built on the same template as the wire probe layout."""
    from ..database.project_db import pjt_bundle as _pjt_bundle_runtime
    from ..database.project_db import pseudo_bundle_layout as _pseudo_bundle_layout
    from ..database.project_db import pseudo_wire_layout as _pseudo_wire_layout

    db_id = uuid.uuid4().bytes

    if isinstance(chain_db_obj, _pjt_bundle_runtime.PJTBundle):
        layout = _pseudo_bundle_layout.PseudoPJTBundleLayout(None, db_id)
        layout.configure(
            bundle_part=chain_db_obj.part,
            bundle_diameter=float(chain_db_obj.diameter),
            position_pegboard=position)
    else:
        layout = _pseudo_wire_layout.PseudoPJTWireLayout(None, db_id)
        layout.configure(wire_part=chain_db_obj.part, position_pegboard=position)

    return layout


@_debug.logfunc
def _move_point(point: "_point.Point", x: float, z: float) -> bool:
    """Move a cached peg-board ``Point`` to (x, z) by a delta (``+=``), so its
    bound callbacks fire -- plain assignment would not.

    No-ops (skips the ``+=`` entirely) when *point* is already exactly at
    (x, z) -- a real case, not a hypothetical one: a drag's own cascade
    settles a chain's interior once, but something else touching one of
    this SAME chain's own points (:class:`~handlers.wire_slack_handler.
    WireSlackHandler`'s per-point safety net, chief among them -- see its
    own module docstring) can re-run this exact reconcile again
    immediately after, recomputing the identical already-correct
    positions. Firing every bound callback (each one potentially a real
    GL rebuild) for a move that doesn't actually move anything is pure
    waste -- confirmed live, 2026-10-16: a single housing+wire drag spent
    multiple seconds re-settling the same wire several times a frame.
    Exact equality, not a tolerance -- this only ever skips a call whose
    inputs are bit-identical to the point's current value, never one that
    merely rounds close.

    :returns: Whether the point's position actually changed.
    """
    dx = x - float(point.x)
    dz = z - float(point.z)
    if dx == 0.0 and dz == 0.0:
        return False

    point += _point.Point(dx, 0.0, dz)
    return True


@_debug.logfunc
def _overlay_for(
    points_table: object,
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    path_table: _Union["_pjt_bundle_path.PJTBundlePathsTable", "_pjt_wire_path.PJTWirePathsTable"],
) -> list[_Waypoint]:
    """The chain's drag overlay, created from its database waypoints the first
    time a drag touches it."""
    chain_id = chain_db_obj.db_id
    existing = _offline_store.overlay(chain_id)
    if existing is not None:
        return existing

    entries = [
        _Waypoint(point_id, points_table[point_id].point, None)
        for point_id in path_table.point_ids(chain_id, 'pegboard')]
    _offline_store.set_overlay(chain_id, entries)
    return entries


@_debug.logfunc
@_check_types.do
def _set_layout_visible(
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    point_id: bytes, visible: bool
) -> None:
    """Show or hide the layout marker sitting on *point_id* on the peg-board
    object itself (no database write -- see ``BasePegboard.set_visible_cache``)."""
    layout_db = layouts_table.for_point_pegboard_id(point_id)
    if layout_db is None:
        return

    layout_obj = layout_db.get_object()
    if layout_obj is not None:
        layout_obj.objpegboard.set_visible_cache(visible)


@_debug.logfunc
@_check_types.do
def _apply_mid_drag(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    path_table: _Union["_pjt_bundle_path.PJTBundlePathsTable", "_pjt_wire_path.PJTWirePathsTable"],
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    drag_end: "_rope_pull.DragEnd",
    interior: list[tuple[float, float]],
    start_xz: tuple[float, float],
    stop_xz: tuple[float, float],
    pin_point_id: bytes | None,
    pin_xz: tuple[float, float] | None,
    leading: int = 0,
    trailing: int = 0
) -> None:
    """One mid-drag frame for one chain. No database row is inserted or
    deleted here.

    The solver's waypoint count decides the overlay's size. A surplus is given
    up from the anchor end (the end not being moved) into the store. A shortfall
    takes the store's most recent entries back first, and only creates new
    in-memory points when the store is empty. The overlay is then placed on the
    solver's shape (see :func:`_place_active`).

    *leading*/*trailing* exclude the chain's own terminal/cavity
    structural-stub entries (see :func:`_stub_boundary`) from all of
    that -- they're never grown, shrunk, given up to the store, or
    repositioned by :func:`_place_active`, only carved out of the
    overlay before this runs and spliced back verbatim after, same
    reasoning as :func:`_reconcile_interior`'s own identical guard.
    """
    chain_id = chain_db_obj.db_id
    points_table = mainframe.project.ptables.pjt_points_pegboard_table
    overlay = _overlay_for(points_table, chain_db_obj, path_table)
    store = _offline_store.for_chain(chain_id)
    from_tail = drag_end is not _rope_pull.DragEnd.STOP
    wanted = len(interior)

    if pin_point_id is not None and (leading or trailing):
        boundary_ids = (
            {e.point_id for e in overlay[:leading]}
            | {e.point_id for e in overlay[len(overlay) - trailing:]})
        if pin_point_id in boundary_ids:
            leading = trailing = 0

    tail_start = len(overlay) - trailing
    active = overlay[leading:tail_start]
    original_count = len(active)

    if wanted < len(active):
        for _ in range(len(active) - wanted):
            if from_tail:
                entry = active[-1]
            else:
                entry = active[0]

            if pin_point_id is not None and entry.point_id == pin_point_id:
                break

            if from_tail:
                active.pop()
            else:
                active.pop(0)

            _offline_store.push(chain_id, entry)
            if entry.point_id is not None:
                _set_layout_visible(layouts_table, entry.point_id, False)

    elif wanted > len(active):
        for _ in range(wanted - len(active)):
            if store:
                entry = _offline_store.pop_front(chain_id)
                if entry.point_id is not None:
                    _set_layout_visible(layouts_table, entry.point_id, True)
            else:
                position = _point.Point(0.0, 0.0, 0.0)
                entry = _Waypoint(None, position, _make_pseudo_layout(chain_db_obj, position))

            if from_tail:
                active.append(entry)
            else:
                active.insert(0, entry)

    # Suspend the chain's own per-point geometry rebuild for the duration of
    # the move loop below -- _place_active moves every active waypoint one
    # at a time, and each one left bound would otherwise trigger its own
    # full _recalculate_geometry()/GL-stripe-capacity rebuild (confirmed
    # live, 2026-10-16: this was the dominant per-point cost of a drag).
    # One rebuild after all of them have their final position, in the
    # refresh_waypoints() call below, replaces all of those. Always
    # resumed in the finally, via refresh_waypoints()'s own unconditional
    # rebind half, so a raised exception never leaves this chain's own
    # waypoints permanently unbound.
    chain_obj = chain_db_obj.get_object()
    if chain_obj is not None:
        chain_obj.objpegboard.unregister_geometry_updates()

    try:
        moved = _place_active(active, interior, start_xz, stop_xz, pin_point_id, pin_xz)
    finally:
        overlay[:] = overlay[:leading] + active + overlay[tail_start:]

        if chain_obj is not None:
            # A true no-op -- same count, same positions -- needs only
            # the cheap rebind (reregister_geometry_updates: back onto
            # the exact same points just unbound, no DB/offline-store
            # re-derivation, no WireSlackHandler rebind, since the set
            # it would rebind to is provably identical). This is what
            # makes a redundant reconcile (WireSlackHandler's own
            # per-point safety net firing on points a housing/transition
            # move rigidly carries along -- see its own module
            # docstring) cheap end to end: by the time it runs, this
            # chain is already exactly where the real pass just put it,
            # confirmed by _move_point's own no-op short-circuit (exact
            # equality, never a tolerance). Only a real change pays for
            # the full refresh_waypoints() -- re-derive the waypoint
            # set, rebind everything (this wire's own geometry callback
            # AND WireSlackHandler's), recalculate, repaint.
            if original_count != len(active) or moved:
                chain_obj.objpegboard.refresh_waypoints()
            else:
                chain_obj.objpegboard.reregister_geometry_updates()


@_debug.logfunc
@_check_types.do
def _place_active(
    overlay: list[_Waypoint],
    interior: list[tuple[float, float]],
    start_xz: tuple[float, float],
    stop_xz: tuple[float, float],
    pin_point_id: bytes | None,
    pin_xz: tuple[float, float] | None
) -> bool:
    """Move the overlay's points onto the solver's shape, keeping the pinned
    (dragged) point on its own target. When the counts disagree, the others are
    spread evenly on the straight line between the anchors (a transient state
    that only lasts until the drag releases).

    :returns: Whether any point actually moved -- see :func:`_move_point`'s
        own no-op short-circuit.
    """
    pinned = [entry for entry in overlay if pin_point_id is not None and entry.point_id == pin_point_id]
    others = [entry for entry in overlay if not (pin_point_id is not None and entry.point_id == pin_point_id)]

    other_xz = list(interior)
    if pin_xz is not None and pin_xz in other_xz:
        other_xz.remove(pin_xz)

    if len(others) == len(other_xz):
        targets = list(zip(others, other_xz))
    else:
        count = len(others)
        targets = []
        for i, entry in enumerate(others):
            fraction = (i + 1) / (count + 1)
            x = start_xz[0] + (stop_xz[0] - start_xz[0]) * fraction
            z = start_xz[1] + (stop_xz[1] - start_xz[1]) * fraction
            targets.append((entry, (x, z)))

    if pinned and pin_xz is not None:
        targets.append((pinned[0], pin_xz))

    moved = False
    for entry, (x, z) in targets:
        if _move_point(entry.point, x, z):
            moved = True

    return moved


@_debug.logfunc
@_check_types.do
def _commit_overlay(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    path_table: _Union["_pjt_bundle_path.PJTBundlePathsTable", "_pjt_wire_path.PJTWirePathsTable"],
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    layout_facade_cls: _Union[type["_bundle_layout.BundleLayout"], type["_wire_layout.WireLayout"]],
) -> None:
    """Drag released: write the overlay to the database in one pass.

    New in-memory points get real rows, the route is set in the overlay's
    order (database-backed points keep their rows), new layouts are created
    after the route is set (see :func:`_reconcile_interior`'s ordering note),
    and every layout that is no longer in the route is deleted. The store is
    discarded, so nothing given up mid-drag survives unless it is in the route.

    Every insert()/delete() here runs inside the drag's own open gesture
    (opened by the concrete drag handler, e.g. ``drag_handlers.
    editor_pegboard.generic.Generic``) -- see ``PJTTableBase.insert``/
    ``delete``'s own comments: both defer into the project's row cache
    rather than touching the database per row, and the gesture's own
    outermost close flushes everything accumulated in one transaction.
    """
    project = mainframe.project
    points_table = project.ptables.pjt_points_pegboard_table
    chain_id = chain_db_obj.db_id

    overlay = _offline_store.release_overlay(chain_id) or []
    _offline_store.release(chain_id)

    final_ids: list[bytes] = []
    created: list[_Waypoint] = []
    for entry in overlay:
        if entry.point_id is None:
            point_db = points_table.insert(float(entry.point.x), 0.0, float(entry.point.z))
            entry.point_id = point_db.db_id
            created.append(entry)

        final_ids.append(entry.point_id)

    old_ids = list(path_table.point_ids(chain_id, 'pegboard'))
    path_table.set_route(chain_id, 'pegboard', final_ids)

    for entry in created:
        layout_db = layouts_table.insert(point_pegboard_id=entry.point_id)
        layout_obj = layout_facade_cls(mainframe, layout_db)
        if layout_facade_cls is _bundle_layout.BundleLayout:
            project.add_bundle_layout(layout_obj)
        else:
            project.add_wire_layout(layout_obj)

    for point_id in old_ids:
        if point_id in final_ids:
            continue

        layout_db = layouts_table.for_point_pegboard_id(point_id)
        if layout_db is not None:
            layout_obj = layout_db.get_object()
            if layout_obj is not None:
                layout_obj.delete()

    chain_obj = chain_db_obj.get_object()
    if chain_obj is not None:
        chain_obj.objpegboard.refresh_waypoints()


@_debug.logfunc
@_check_types.do
def clamp_to_length_from_anchor(
    anchor_xz: tuple[float, float], target_xz: tuple[float, float], length: float
) -> tuple[float, float]:
    """*target_xz*, pulled back onto the circle of radius *length* around
    *anchor_xz* when it is farther away than that. The clamped point is the
    one on the line from the anchor through the target. Unchanged when the
    target is already within reach."""
    dx = target_xz[0] - anchor_xz[0]
    dz = target_xz[1] - anchor_xz[1]
    dist = math.hypot(dx, dz)

    if dist <= length or dist < 1e-9:
        return target_xz

    scale = length / dist
    return anchor_xz[0] + dx * scale, anchor_xz[1] + dz * scale


@_debug.logfunc
@_check_types.do
def _pinned_chain(
    ptables: "_PJTPegboardTable", point_starts: list[tuple[bytes, _point.Point]]
) -> _Union[tuple[_Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"], _point.Point,
                  tuple[float, float], float], None]:
    """The one chain a drag group is pinned to, as
    ``(chain_db_obj, anchor_start, far_xz, length)``: a start/stop anchor
    belonging to exactly one chain, whose other end is not part of this
    drag. ``None`` when no point is pinned or several are (a transition
    with two bundles, say) -- the general solve handles those.
    """
    pinned = []

    for point_id, start in point_starts:
        chains = _chains_for_point(ptables, point_id)
        if len(chains) != 1:
            continue

        chain_db_obj, _path_table, _layouts_table, _layout_facade_cls, drag_end = chains[0]
        if drag_end is _rope_pull.DragEnd.WAYPOINT:
            continue

        start_xz, stop_xz, length, _leading, _trailing = _anchors_and_length(ptables, chain_db_obj)
        far_xz = stop_xz if drag_end is _rope_pull.DragEnd.START else start_xz
        pinned.append((chain_db_obj, start, far_xz, length))

    if len(pinned) != 1:
        return None

    return pinned[0]


@_debug.logfunc
@_check_types.do
def _chain_is_tight(chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"]) -> bool:
    """The chain's own live ``is_tight`` (see objects_pegboard.bundle/wire).
    A chain with no loaded view object counts as tight, so the move takes
    the cast path, which always respects the chain's length.
    """
    chain_obj = chain_db_obj.get_object()
    if chain_obj is None:
        return True

    return bool(chain_obj.objpegboard.is_tight)


@_debug.logfunc
@_check_types.do
def _resolve_pinned_move(
    mainframe: "_ui.MainFrame",
    point_starts: list[tuple[bytes, _point.Point]],
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    anchor_start: _point.Point,
    far_xz: tuple[float, float],
    length: float,
    full_delta: tuple[float, float],
    iterations: int,
    in_progress: bool,
) -> tuple[float, float]:
    """Rope pull OFF, one chain pinned: the dragged group's own center
    (``point_starts[0]``) is placed by the cursor while the chain is slack,
    and by a cast once it is tight.

    The chain's anchor sits at a fixed offset from the center (``off``).
    Slack: the center goes straight under the cursor, provided the anchor
    still fits within the chain length. Tight: the anchor is projected onto
    the chain-length circle around the far anchor, along the line from the
    far anchor through where the anchor would be if the center were under
    the cursor, and the center is then placed ``off`` back from that point.
    The anchor therefore always lands exactly ``length`` from the far
    anchor, so the bundle is limited at its own length. The slack check is
    attempted first with the cursor's own position.
    """
    ptables = mainframe.project.ptables
    _center_id, center_start = point_starts[0]
    center_x = float(center_start.x)
    center_z = float(center_start.z)
    off_x = float(anchor_start.x) - center_x
    off_z = float(anchor_start.z) - center_z
    dx, dz = full_delta

    def center_at(s: float, cast: bool) -> tuple[float, float]:
        cursor_x = center_x + dx * s
        cursor_z = center_z + dz * s
        if not cast:
            return cursor_x, cursor_z

        anchor_desired = (cursor_x + off_x, cursor_z + off_z)
        anchor_x, anchor_z = clamp_to_length_from_anchor(far_xz, anchor_desired, length)
        return anchor_x - off_x, anchor_z - off_z

    def candidate(s: float, cast: bool) -> list[tuple[bytes, tuple[float, float]]]:
        # Every point of the group moves rigidly with the center.
        center_placed_x, center_placed_z = center_at(s, cast)
        ddx = center_placed_x - center_x
        ddz = center_placed_z - center_z
        return [
            (point_id, (float(start.x) + ddx, float(start.z) + ddz))
            for point_id, start in point_starts]

    def displacement_at(s: float, cast: bool) -> tuple[float, float]:
        center_placed_x, center_placed_z = center_at(s, cast)
        return center_placed_x - center_x, center_placed_z - center_z

    # Shared across every _evaluate_points call this resolve makes below --
    # all read-only against the same unwritten ptables state (nothing here
    # commits until the winning candidate is found), so the anchor-side
    # chain lookup's one-time index (_anchor_index, via _chains_for_point)
    # only needs building once for the whole search instead of once per
    # candidate. See _evaluate_points' own chain_cache docstring.
    chain_cache: dict = {}

    if not _chain_is_tight(chain_db_obj):
        free_result = _evaluate_points(ptables, candidate(1.0, False), cascade=False, chain_cache=chain_cache)
        if free_result is not None:
            _commit_points(mainframe, *free_result, in_progress=in_progress)
            return displacement_at(1.0, False)

    full_result = _evaluate_points(ptables, candidate(1.0, True), cascade=False, chain_cache=chain_cache)
    if full_result is not None:
        _commit_points(mainframe, *full_result, in_progress=in_progress)
        return displacement_at(1.0, True)

    lo, hi = 0.0, 1.0
    best_s = 0.0
    best_result = _evaluate_points(ptables, candidate(0.0, True), cascade=False, chain_cache=chain_cache)

    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        mid_result = _evaluate_points(ptables, candidate(mid, True), cascade=False, chain_cache=chain_cache)

        if mid_result is not None:
            lo = mid
            best_s = mid
            best_result = mid_result
        else:
            hi = mid

    if best_result is not None:
        _commit_points(mainframe, *best_result, in_progress=in_progress)

    return displacement_at(best_s, True)


@_debug.logfunc
@_check_types.do
def resolve_local_move(
    mainframe: "_ui.MainFrame",
    point_starts: list[tuple[bytes, _point.Point]],
    full_delta: tuple[float, float],
    iterations: int = 32,
    in_progress: bool = True
) -> tuple[float, float]:
    """Rope pull OFF: move the dragged point(s) without pulling anything else.

    When the drag is pinned to one chain (see :func:`_pinned_chain`), the
    center is placed by :func:`_resolve_pinned_move` so the chain's own
    length is respected. Otherwise the largest fraction of the drag line
    every touching chain accepts is taken. Either way the touching chains'
    own slack is re-solved locally (no far end is pulled).

    :returns: The ``(dx, dz)`` actually applied to the point(s), measured
        from each point's own position when the drag began.
    """
    ptables = mainframe.project.ptables

    pinned = _pinned_chain(ptables, point_starts)
    if pinned is not None:
        chain_db_obj, anchor_start, far_xz, length = pinned
        return _resolve_pinned_move(
            mainframe, point_starts, chain_db_obj, anchor_start, far_xz, length,
            full_delta, iterations, in_progress)

    dx, dz = full_delta

    def candidate(t: float) -> list[tuple[bytes, tuple[float, float]]]:
        return [
            (point_id, (float(start.x) + dx * t, float(start.z) + dz * t))
            for point_id, start in point_starts]

    # See _resolve_pinned_move's identical comment -- shared across this
    # whole search since every call below is a read-only solve against
    # the same unwritten ptables state.
    chain_cache: dict = {}

    full_result = _evaluate_points(ptables, candidate(1.0), cascade=False, chain_cache=chain_cache)
    if full_result is not None:
        _commit_points(mainframe, *full_result, in_progress=in_progress)
        return dx, dz

    lo, hi = 0.0, 1.0
    best_t = 0.0
    best_result = _evaluate_points(ptables, candidate(0.0), cascade=False, chain_cache=chain_cache)

    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        mid_result = _evaluate_points(ptables, candidate(mid), cascade=False, chain_cache=chain_cache)

        if mid_result is not None:
            lo = mid
            best_t = mid
            best_result = mid_result
        else:
            hi = mid

    if best_result is not None:
        _commit_points(mainframe, *best_result, in_progress=in_progress)

    return dx * best_t, dz * best_t


@_debug.logfunc
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

    # See _resolve_pinned_move's identical comment -- shared across this
    # whole search since every call below is a read-only solve against
    # the same unwritten ptables state.
    chain_cache: dict = {}

    full_result = _evaluate_points(ptables, candidate(1.0), chain_cache=chain_cache)
    if full_result is not None:
        _commit_points(mainframe, *full_result, in_progress=in_progress)
        return 1.0

    lo, hi = 0.0, 1.0
    best_t = 0.0
    best_result = _evaluate_points(ptables, candidate(0.0), chain_cache=chain_cache)

    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        mid_result = _evaluate_points(ptables, candidate(mid), chain_cache=chain_cache)

        if mid_result is not None:
            lo = mid
            best_t = mid
            best_result = mid_result
        else:
            hi = mid

    if best_result is not None:
        _commit_points(mainframe, *best_result, in_progress=in_progress)

    return best_t


@_debug.logfunc
@_check_types.do
def realize_length_change(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    in_progress: bool = False
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

    :param in_progress: Passed straight through to :func:`_commit_points`
        -- ``True`` while a gesture/drag is still open holds every
        touched chain's own waypoint COUNT fixed (repositioning only,
        via the in-memory overlay), so a caller that re-runs this every
        frame (e.g. a point-bound callback firing on every move) never
        creates/destroys a real ``WireLayout``/``BundleLayout`` object
        on every single frame. ``False`` (the default -- every call
        site that only ever runs once per real change, plus whatever
        runs the drag's own very last frame) lets the waypoint count
        finally catch up to whatever it actually needs.

    :returns: Whether the whole cascade this change triggers (if any)
        was feasible. ``False`` means something in it is infeasible
        even after every pull it allows -- a closed loop that doesn't
        fit (see :func:`_evaluate_points`'s own "why no explicit cycle
        detection" note) or genuinely nowhere left to pull -- and the
        peg-board side is deliberately left untouched rather than
        guessed at.
    """
    ptables = mainframe.project.ptables
    raw_start = chain_db_obj.start_position_pegboard
    raw_start_xz = (float(raw_start.x), float(raw_start.z))

    # The RAW anchor's own current position, not _anchors_and_length's
    # EFFECTIVE one -- _evaluate_points' own main loop now derives the
    # effective target from a raw-position delta (see its own comment),
    # so a genuine no-move target has to be expressed in the same raw
    # terms, or that delta math reads a nonzero "move" (the stub
    # segment's own fixed offset) out of what should be a pure no-op.
    result = _evaluate_points(
        ptables, [(chain_db_obj.start_position_pegboard_id, raw_start_xz)], cascade=is_enabled())
    if result is None:
        return False

    _commit_points(mainframe, *result, in_progress=in_progress)
    return True


@_debug.logfunc
@_check_types.do
def realize_3d_move(
        mainframe: "_ui.MainFrame", point3d_ids: list[bytes], in_progress: bool = False) -> None:
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

    :param in_progress: Passed straight through to every
        :func:`realize_length_change` call -- see that function's own
        comment.
    """
    ptables = mainframe.project.ptables
    ids = set(point3d_ids)

    for bundle_db_obj in ptables.pjt_bundles_table:
        if bundle_db_obj.start_position3d_id in ids or bundle_db_obj.stop_position3d_id in ids:
            realize_length_change(mainframe, bundle_db_obj, in_progress=in_progress)

    for wire_db_obj in ptables.pjt_wires_table:
        if wire_db_obj.start_position3d_id in ids or wire_db_obj.stop_position3d_id in ids:
            realize_length_change(mainframe, wire_db_obj, in_progress=in_progress)


@_debug.logfunc
@_check_types.do
def finalize_drag(mainframe: "_ui.MainFrame") -> bool:
    """The release-time commit of a drag: reconcile every chain still
    holding an overlay one final time with ``in_progress=False`` -- see the
    module docstring's "Waypoint add/remove deferred to mouse-up" section.
    Called by ``objects.project.Project.end_gesture`` on the outermost
    gesture close, so it covers every drag/rotate handler (peg-board, 3D
    through the slack handler's own in-gesture reconciles, schematic).

    Every frame before this one ran with ``in_progress=True``, which only
    repositions each chain's in-memory overlay (:mod:`rope_pull.
    offline_store`) and never touches its real route. Without this call the
    overlay is never written: the database path keeps every waypoint the
    drag gave up, each frozen at whatever position it last had and still in
    the old order, interleaved with the live ones -- the wire reads back
    (after a reload, or the moment anything else releases the overlay) as a
    back-and-forth tangle. Confirmed from a live project snapshot,
    2026-10-15: one wire's saved interior ran x = 29.8, 28.5, 14.8, 15.3
    between two housings while its live overlay held a single bend.

    Each overlay chain is committed on its own, with both of its anchors
    "dragged" to exactly where they already are, so nothing moves -- this
    only lets :func:`_commit_overlay` write the overlay and the waypoint
    count settle on whatever the final position needs. Found from the
    overlay store itself rather than from the dragged points: the cascade
    (a far housing pulled along, and whatever else hangs off it) overlays
    chains no dragged point touches. One chain that cannot be solved never
    blocks the others.

    :returns: Whether every overlay chain could be committed. A chain that
        could not is left exactly as the last drag frame left it.
    """
    ptables = mainframe.project.ptables
    points_table = ptables.pjt_points_pegboard_table

    chains = (*ptables.pjt_wires_table, *ptables.pjt_bundles_table)
    live_ids = {chain_db_obj.db_id for chain_db_obj in chains}
    feasible = True

    for chain_db_obj in chains:
        # Re-checked per chain, not taken from a snapshot: committing one
        # chain also commits any other overlay chain that shares an anchor
        # with it (a terminal several wires plug into).
        if _offline_store.overlay(chain_db_obj.db_id) is None:
            continue

        seeds: list[tuple[bytes, tuple[float, float]]] = []
        for point_id in (chain_db_obj.start_position_pegboard_id, chain_db_obj.stop_position_pegboard_id):
            if point_id is None:
                continue

            point = points_table[point_id].point
            seeds.append((point_id, (float(point.x), float(point.z))))

        result = _evaluate_points(ptables, seeds, cascade=is_enabled())
        if result is None:
            feasible = False
            continue

        _commit_points(mainframe, *result, in_progress=False)

    # An overlay whose chain no longer exists (deleted mid-drag) has nothing
    # to write -- just drop the dead state.
    for chain_id in _offline_store.overlay_chain_ids():
        if chain_id not in live_ids:
            _offline_store.release_overlay(chain_id)
            _offline_store.release(chain_id)

    return feasible
