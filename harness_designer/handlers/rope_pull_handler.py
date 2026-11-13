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
from collections.abc import Callable

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
from ..database.project_db import pjt_cable as _pjt_cable
from ..database.project_db import pjt_cable_path as _pjt_cable_path
from ..database.project_db import pjt_wire_path as _pjt_wire_path_runtime
from . import wire_routing_handler as _wire_routing_handler
from . import bundle_wire_model as _bundle_wire_model
from .. import check_types as _check_types
from .. import debug as _debug
from .. import logger as _logger


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

# How many times a node may be pulled in ONE solve, all nodes together, before the move is refused. A solve that is going to succeed
# needs a few dozen at most (the most seen in a project with a cable of nine conductors and loops was 66); one that does not fit (the
# move is more than the chains allow) otherwise spends hundreds, over and over, in the binary search of every drag frame.
_MAX_PULLS_PER_SOLVE = 120

# A re-pull smaller than this (mm) is floating-point noise, not a chain that
# still needs relief -- matches solve_chain's own default tolerance.
_REPULL_TOLERANCE_MM = 1e-6

# Floor on the diameter the fold limit (_fold_limit) is measured with, so a zero or missing diameter never makes a chain that cannot fold.
_MIN_FOLD_DIAMETER_MM = 1.0


def _short(point_id: bytes | None) -> str:
    """A point or row id as a few hex characters (the part of it that tells two ids apart), for the trace."""
    if point_id is None:
        return 'None'

    return point_id.hex()[8:16]


def _xz(xz: tuple[float, float] | None) -> str:
    """A board position as ``(x, z)`` to 0.01 mm, for the trace."""
    if xz is None:
        return 'None'

    return f'({xz[0]:.2f}, {xz[1]:.2f})'


def _label(chain_db_obj: object) -> str:
    """What a chain is, for the trace: its kind and short id (a lead of a cable's conductor says so)."""
    if isinstance(chain_db_obj, _pjt_cable.PJTCable):
        return f'cable {_short(chain_db_obj.db_id)}'

    if isinstance(chain_db_obj, _pjt_bundle.PJTBundle):
        return f'bundle {_short(chain_db_obj.db_id)}'

    if chain_db_obj.cable_conductor_id is not None:
        return f'lead {_short(chain_db_obj.db_id)} of conductor {_short(chain_db_obj.cable_conductor_id)}'

    return f'wire {_short(chain_db_obj.db_id)}'


def _trace(make_parts: Callable[[], tuple]) -> None:
    """One line of the solver's trace in the log, when ``Config.trace`` is on (see config). *make_parts* builds the parts of the line:
    it is called only then, so a solve that is not traced pays for none of the formatting."""
    if Config.trace:
        _logger.info('[rope]', *make_parts())


@_check_types.do
def _is_wire_chain(chain_db_obj: object) -> bool:
    """Whether *chain_db_obj* is a wire: the one kind of chain that attaches to terminals (stubs), is routed through bundles and
    transitions, and has a layout at each of its waypoints. A bundle has layouts but no stubs; a cable (a trunk whose ends are free)
    has none of the three, and its waypoints are bare points of ``pjt_cable_paths``."""
    return not isinstance(chain_db_obj, (_pjt_bundle.PJTBundle, _pjt_cable.PJTCable))


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

    if isinstance(chain_db_obj, _pjt_cable.PJTCable):
        # the thinner side of the trunk (a ribbon is wider than it is thick)
        return float(min(chain_db_obj.part.trunk_size))

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


# Wires already reported by _stub_boundary as not starting with their terminal's/cavity's stub points (reported once each).
_unmatched_stub_wires: set[bytes] = set()


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

    @_check_types.do
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

    start_expected = _structural_stub_ids(ptables, wire_db_obj.start_position_pegboard_id)
    stop_expected = _structural_stub_ids(ptables, wire_db_obj.stop_position_pegboard_id)

    leading = count(start_expected, False)
    trailing = count(stop_expected, True)

    # The part of a wire inside a housing (its terminal's and its cavity's stub, out to the back of the cavity) is found by those
    # stub points' ids. A wire whose board route does not start with them (made before the stubs were tagged, or damaged) has that
    # part counted as free wire: it is measured from the terminal, not from the back of the cavity.
    if (leading < len(start_expected) or trailing < len(stop_expected)) and wire_db_obj.db_id not in _unmatched_stub_wires:
        _unmatched_stub_wires.add(wire_db_obj.db_id)
        _logger.warning(
            f'wire {wire_db_obj.db_id.hex()}: its board route does not start with the stub points of its terminal/cavity '
            f'(found {leading} of {len(start_expected)} at the start, {trailing} of {len(stop_expected)} at the end): the part '
            f'inside the housing is measured as free wire')

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
    if not _is_wire_chain(chain_db_obj):
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
def _wire_protected_runs(
    ptables: "_PJTPegboardTable", wire_db_obj: "_pjt_wire.PJTWire", view: str,
) -> list[tuple[int, int]]:
    """Contiguous runs of *wire_db_obj*'s own interior *view* points that
    a wire-level solve may never add, remove or reposition (user,
    2026-10-28): every point tagged ``bundle_id``/``transition_id``/
    ``transition_branch_id`` (shared with a bundle's own span, or a
    transition branch/centre -- BUNDLE_DESIGN.md 2.6/2.7, "etched in
    stone" until the wire is actually un-routed from it), plus its
    bracketing guard stub(s) -- untagged themselves, but immediately
    next to a tagged point (see ``wire_routing_handler.guard_points_at``/
    ``is_guard_point`` for the same ``bundle_id``-only check; generalized
    here to the transition tags too, since a bare transition pass-
    through -- no bundle plugged into either branch -- tags its two
    branch points and centre point but has no ``bundle_id`` anywhere).

    Returns a list of ``(first_index, last_index)`` inclusive, in order,
    indexing *wire_db_obj*'s own full interior point list for *view*
    (index 0 = its first interior waypoint) -- NOT adjusted for any
    terminal/cavity stub exclusion (:func:`_stub_boundary`), which the
    caller reconciles separately.
    """
    rows = ptables.pjt_wire_paths_table.for_wire(wire_db_obj.db_id, view)
    tagged = [
        row.bundle_id is not None or row.transition_id is not None
        or row.transition_branch_id is not None
        for row in rows]

    runs: list[tuple[int, int]] = []
    n = len(tagged)
    i = 0
    while i < n:
        if not tagged[i]:
            i += 1
            continue

        start = i
        while i < n and tagged[i]:
            i += 1
        end = i - 1

        if start > 0 and not tagged[start - 1]:
            start -= 1
        if end < n - 1 and not tagged[end + 1]:
            end += 1

        if runs and start <= runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], max(runs[-1][1], end))
        else:
            runs.append((start, end))

    return runs


@_debug.logfunc
@_check_types.do
def _distance_sum(points: list) -> float:
    """Total 3D length walking through *points* in order."""
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += _distance3d(a, b)
    return total


@_debug.logfunc
@_check_types.do
def _wire_bundle_length3d(ptables: "_PJTPegboardTable", wire_db_obj: "_pjt_wire.PJTWire") -> float:
    """Total 3D length consumed by every bundle/transition-routed
    protected run along *wire_db_obj*'s own 3D route (see
    :func:`_wire_protected_runs`) -- fixed bundle/transition geometry,
    never available as peg-board slack, exactly like a terminal stub's
    own fixed length (:func:`_wire_stub_length3d`) but found anywhere in
    the interior, not just the two ends.
    """
    runs = _wire_protected_runs(ptables, wire_db_obj, '3d')
    if not runs:
        return 0.0

    points = [wire_db_obj.start_position3d, *(wp.point for wp in wire_db_obj.waypoints3d),
              wire_db_obj.stop_position3d]

    return sum(_distance_sum(points[start + 1:end + 2]) for start, end in runs)


# A point pulled exactly taut is stored as float32 (a few 1e-6 mm of error at ~50 mm),
# so re-reading it from the database can put a taut stretch a hair past its length;
# solve_chain's own default tolerance (1e-6) would then refuse it.
_STRETCH_TOLERANCE_MM = 1e-3


@_debug.logfunc
@_check_types.do
def _wire_gap_lengths3d(
    ptables: "_PJTPegboardTable", wire_db_obj: "_pjt_wire.PJTWire",
    protected_runs: list[tuple[int, int]], leading: int, trailing: int,
) -> list[float] | None:
    """The real 3D length of each of *wire_db_obj*'s free stretches
    (``len(protected_runs) + 1`` of them: start -> first run, between
    runs, last run -> stop), terminal/cavity stubs excluded. ``None`` if
    the 3D route doesn't have the same number of protected runs.
    """
    runs3d_full = _wire_protected_runs(ptables, wire_db_obj, '3d')
    if len(runs3d_full) != len(protected_runs):
        return None

    points3d_full = [wire_db_obj.start_position3d, *(wp.point for wp in wire_db_obj.waypoints3d),
                     wire_db_obj.stop_position3d]
    points3d = points3d_full[leading:len(points3d_full) - trailing]

    lengths: list[float] = []
    prev_end3d = -1
    for start3d, end3d in runs3d_full:
        start3d -= leading
        end3d -= leading
        lengths.append(_distance_sum(points3d[prev_end3d + 1:start3d + 2]))
        prev_end3d = end3d
    lengths.append(_distance_sum(points3d[prev_end3d + 1:]))
    return lengths


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

    For a wire routed through a bundle/transition (see
    :func:`_wire_protected_runs`), the fixed 3D length of every such
    protected run is ALSO subtracted, same reasoning -- that portion is
    consumed by fixed bundle/transition geometry the wire's own solve
    never touches (:func:`_reconcile_wire_through_bundle` handles it
    instead, see that function's own docstring). Unlike a terminal
    stub, this never shifts *start*/*stop* themselves -- a protected run
    sits somewhere in the MIDDLE of the interior (BUNDLE_PLACEMENT.md
    section 12's own eligibility rule forbids grabbing a section
    touching the wire's own start/stop), so the chain's own true
    anchors are unaffected; only the available slack length shrinks.
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

    if _is_wire_chain(chain_db_obj):
        length -= _wire_bundle_length3d(ptables, chain_db_obj)

    return (float(start.x), float(start.z)), (float(stop.x), float(stop.z)), length, leading, trailing


@_debug.logfunc
@_check_types.do
def _reconcile_segment(
    points_table: object, old_ids: list[bytes], new_interior: list[tuple[float, float]],
    pin_point_id: bytes | None, pin_xz: tuple[float, float] | None,
) -> tuple[list[bytes], list[int], list[bytes]]:
    """Resolve ONE free segment's own old point ids against its own new
    target positions -- the core reuse-by-position/insert/delete dance
    :func:`_reconcile_interior` used to do inline for a chain's WHOLE
    (single-segment) interior; factored out so
    :func:`_reconcile_wire_through_bundle` can run it once per free
    segment instead (see that function's own docstring for why a wire
    with a bundle/transition-routed run needs more than one). *pin_xz*
    is matched against *new_interior* by exact value (never fuzzy
    float comparison) -- the solver echoes a dragged point's own target
    back unmodified, so this is reliable; see the module docstring's
    own "Reconciling..." section.

    :returns: ``(final_ids, new_indexes, removed_ids)`` -- *final_ids*
        is parallel to *new_interior*; *new_indexes* are indexes into
        it that got a freshly-inserted point (needing a new layout);
        *removed_ids* are old ids no longer used (needing their layout
        deleted).
    """
    old_ids = list(old_ids)

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
    # facade object for each come after set_route, in the caller. Each
    # insert()/delete() below runs inside the drag's own open gesture
    # and defers into the project's row cache rather than touching the
    # database per row -- see PJTTableBase.insert/delete's own comments.
    new_indexes = []
    for i in range(reuse_count, len(remaining_new_indexes)):
        new_index = remaining_new_indexes[i]
        x, z = new_interior[new_index]
        point_db = points_table.insert(x, 0.0, z)
        final_ids[new_index] = point_db.db_id
        new_indexes.append(new_index)

    removed_ids = remaining_old_ids[reuse_count:]
    return final_ids, new_indexes, removed_ids


@_debug.logfunc
@_check_types.do
def _reconcile_wire_through_bundle(
    mainframe: "_ui.MainFrame", wire_db_obj: "_pjt_wire.PJTWire",
    path_table: "_pjt_wire_path.PJTWirePathsTable",
    layouts_table: "_pjt_wire_layout.PJTWireLayoutsTable",
    layout_facade_cls: type["_wire_layout.WireLayout"],
    protected_runs: list[tuple[int, int]],
    pin_point_id: bytes | None, pin_xz: tuple[float, float] | None,
    leading: int = 0, trailing: int = 0, gap_lengths: list[float] | None = None,
) -> None:
    """:func:`_reconcile_interior`'s own counterpart for a wire whose
    peg-board interior has one or more bundle/transition-routed
    protected runs (:func:`_wire_protected_runs`) -- splits the
    interior into ``len(protected_runs) + 1`` independent free segments
    around them and solves/applies each one separately
    (:func:`_reconcile_segment`), splicing the protected runs back in
    completely untouched.

    User's own rule, 2026-10-28: a wire-level solve may only add/remove
    waypoints in the free run after a bundle's own exit stub (or before
    its entry stub) -- anything bundle/transition-tagged, or a guard
    immediately next to it, is "etched in stone," touchable only by the
    BUNDLE's own solve (a separate call, always run first -- see
    :func:`realize_bundle_and_wires`).

    *leading*/*trailing* are :func:`_anchors_and_length`'s own terminal-
    stub exclusion counts (see :func:`_stub_boundary`), carried through
    exactly like :func:`_reconcile_interior` does -- a wire CAN be
    attached to a terminal at one or both ends AND routed through a
    bundle somewhere in the middle at the same time; the two
    protections are independent and both apply. *protected_runs* is
    expressed against the FULL interior list (see
    :func:`_wire_protected_runs`'s own docstring) and is shifted here
    to be relative to the stub-excluded slice, same as the plain
    reuse/insert/delete path already does for its own *new_interior*.
    """
    ptables = mainframe.project.ptables
    points_table = ptables.pjt_points_pegboard_table

    old_ids_full = list(path_table.point_ids(wire_db_obj.db_id, 'pegboard'))
    runs3d_full = _wire_protected_runs(ptables, wire_db_obj, '3d')

    if len(runs3d_full) != len(protected_runs):
        _logger.error(
            f'rope_pull_handler: wire {wire_db_obj.db_id!r} has '
            f'{len(protected_runs)} peg-board protected run(s) but {len(runs3d_full)} '
            f'in 3D -- refusing to reconcile rather than guess which points correspond')
        return

    if pin_point_id is not None and (leading or trailing):
        boundary_ids = set(old_ids_full[:leading]) | set(old_ids_full[len(old_ids_full) - trailing:])
        if pin_point_id in boundary_ids:
            leading = trailing = 0

    tail_start = len(old_ids_full) - trailing
    structural_lead_ids = old_ids_full[:leading]
    structural_tail_ids = old_ids_full[tail_start:]
    old_ids = old_ids_full[leading:tail_start]
    protected_runs = [(s - leading, e - leading) for s, e in protected_runs]

    diameter = _chain_diameter(wire_db_obj)

    gap_count = len(protected_runs) + 1
    gap_old_ids: list[list[bytes]] = []
    gap_length3d = gap_lengths if gap_lengths is not None else _wire_gap_lengths3d(
        ptables, wire_db_obj, [(s + leading, e + leading) for s, e in protected_runs], leading, trailing)

    prev_end = -1
    for start_idx, end_idx in protected_runs:
        gap_old_ids.append(old_ids[prev_end + 1:start_idx])
        prev_end = end_idx
    gap_old_ids.append(old_ids[prev_end + 1:])

    if leading:
        start_point = wire_db_obj.waypoints_pegboard[leading - 1].point
    else:
        start_point = wire_db_obj.start_position_pegboard
    if trailing:
        stop_point = wire_db_obj.waypoints_pegboard[-trailing].point
    else:
        stop_point = wire_db_obj.stop_position_pegboard
    gap_start_xz = (float(start_point.x), float(start_point.z))
    final_stop_xz = (float(stop_point.x), float(stop_point.z))

    final_segments: list[list[bytes]] = []
    new_layout_point_ids: list[bytes] = []
    removed_point_ids: list[bytes] = []

    for i in range(gap_count):
        if i < len(protected_runs):
            run_start_idx, _run_end_idx = protected_runs[i]
            entry_point = points_table[old_ids[run_start_idx]].point
            gap_stop_xz = (float(entry_point.x), float(entry_point.z))
        else:
            gap_stop_xz = final_stop_xz

        gap_ids = gap_old_ids[i]
        gap_pin_id = pin_point_id if pin_point_id is not None and pin_point_id in gap_ids else None
        gap_pin_xz = pin_xz if gap_pin_id is not None else None

        if gap_pin_id is not None:
            drag_end, effective_target = _rope_pull.DragEnd.WAYPOINT, gap_pin_xz
        else:
            drag_end, effective_target = _rope_pull.DragEnd.START, gap_start_xz

        result = _rope_pull.solve_chain(
            gap_start_xz, gap_stop_xz, gap_length3d[i], drag_end, effective_target,
            diameter, Config.zigzag_length_factor, Config.threshold_factor, _STRETCH_TOLERANCE_MM)

        if not result.accepted:
            _logger.error(
                f'rope_pull_handler: wire {wire_db_obj.db_id!r} free segment {i} '
                f'of {gap_count} is infeasible -- leaving its whole peg-board route untouched')
            return

        final_ids, new_indexes, removed_ids = _reconcile_segment(
            points_table, gap_ids, result.points[1:-1], gap_pin_id, gap_pin_xz)

        final_segments.append(final_ids)
        new_layout_point_ids.extend(final_ids[idx] for idx in new_indexes)
        removed_point_ids.extend(removed_ids)

        if i < len(protected_runs):
            run_start_idx, run_end_idx = protected_runs[i]
            exit_point = points_table[old_ids[run_end_idx]].point
            gap_start_xz = (float(exit_point.x), float(exit_point.z))

    final_route: list[bytes] = list(structural_lead_ids)
    for i, segment in enumerate(final_segments):
        final_route.extend(segment)
        if i < len(protected_runs):
            run_start_idx, run_end_idx = protected_runs[i]
            final_route.extend(old_ids[run_start_idx:run_end_idx + 1])
    final_route.extend(structural_tail_ids)

    # set_route deletes and re-adds every row, losing the bundle/transition
    # tags -- put them back, or the next reconcile sees an ordinary wire and
    # collapses the whole routed run.
    old_tags = {
        row.point_id: (row.bundle_id, row.concentric_id, row.transition_id, row.transition_branch_id)
        for row in path_table.for_wire(wire_db_obj.db_id, 'pegboard')}

    path_table.set_route(wire_db_obj.db_id, 'pegboard', final_route)

    if gap_lengths is not None:
        _wire_gap_split[wire_db_obj.db_id] = list(gap_lengths)

    for row in path_table.for_wire(wire_db_obj.db_id, 'pegboard'):
        tags = old_tags.get(row.point_id)
        if tags is not None:
            row.bundle_id, row.concentric_id, row.transition_id, row.transition_branch_id = tags

    for point_id in new_layout_point_ids:
        layout_db = layouts_table.insert(point_pegboard_id=point_id)
        layout_obj = layout_facade_cls(mainframe, layout_db)
        mainframe.project.add_wire_layout(layout_obj)

    for point_id in removed_point_ids:
        layout_db = layouts_table.for_point_pegboard_id(point_id)
        if layout_db is not None:
            layout_obj = layout_db.get_object()
            if layout_obj is not None:
                layout_obj.delete()

    wire_obj = wire_db_obj.get_object()
    if wire_obj is not None:
        wire_obj.objpegboard.refresh_waypoints()


@_debug.logfunc
@_check_types.do
def _drop_waypoint(points_table: object, layouts_table: object | None, point_id: bytes) -> None:
    """Remove one waypoint that has left its chain's route: the layout on it (whose delete takes the point with it) for a wire or a
    bundle, the bare point itself for a cable (it has no layouts). The point must already be out of the route (``set_route``)."""
    if layouts_table is None:
        points_table[point_id].delete()
        return

    layout_db = layouts_table.for_point_pegboard_id(point_id)
    if layout_db is not None:
        layout_obj = layout_db.get_object()
        if layout_obj is not None:
            layout_obj.delete()


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
    trailing: int = 0,
    gap_lengths: list[float] | None = None
) -> None:
    """Rewrite *chain_db_obj*'s peg-board interior waypoints to
    *new_interior*, preserving *pin_point_id* (the point actively being
    dragged, in the WAYPOINT case -- ``None``/``None`` for an anchor
    drag, which has no pin) -- see the module docstring's own
    "Reconciling..." section for why and how.

    A wire with one or more bundle/transition-routed protected runs
    along its interior (see :func:`_wire_protected_runs`) is NOT
    handled here at all -- :func:`_reconcile_wire_through_bundle` takes
    over for it instead (user, 2026-10-28: those points are "etched in
    stone," touchable only by the bundle's own solve, never a wire's),
    since the reuse-by-position algorithm below has no concept of a
    fixed run sitting in the MIDDLE of the interior -- only
    *leading*/*trailing* at the two ends.

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
    ptables = mainframe.project.ptables

    if _is_wire_chain(chain_db_obj):
        protected_runs = _wire_protected_runs(ptables, chain_db_obj, 'pegboard')
        if protected_runs:
            _reconcile_wire_through_bundle(
                mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls,
                protected_runs, pin_point_id, pin_xz, leading, trailing, gap_lengths)
            return

    project = mainframe.project
    points_table = ptables.pjt_points_pegboard_table

    old_ids = list(path_table.point_ids(chain_db_obj.db_id, 'pegboard'))

    if pin_point_id is not None and (leading or trailing):
        boundary_ids = set(old_ids[:leading]) | set(old_ids[len(old_ids) - trailing:])
        if pin_point_id in boundary_ids:
            leading = trailing = 0

    tail_start = len(old_ids) - trailing
    structural_lead_ids = old_ids[:leading]
    structural_tail_ids = old_ids[tail_start:]
    old_ids = old_ids[leading:tail_start]

    final_ids, new_indexes, removed_ids = _reconcile_segment(
        points_table, old_ids, new_interior, pin_point_id, pin_xz)

    path_table.set_route(
        chain_db_obj.db_id, 'pegboard', structural_lead_ids + final_ids + structural_tail_ids)

    # a cable has no layouts: its waypoints are bare points
    if layouts_table is not None:
        for new_index in new_indexes:
            layout_db = layouts_table.insert(point_pegboard_id=final_ids[new_index])
            layout_obj = layout_facade_cls(mainframe, layout_db)
            if layout_facade_cls is _bundle_layout.BundleLayout:
                project.add_bundle_layout(layout_obj)
            else:
                project.add_wire_layout(layout_obj)

    for point_id in removed_ids:
        _drop_waypoint(points_table, layouts_table, point_id)

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

    @_check_types.do
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

    # a cable is a chain like a wire, over its own route table and with no layouts
    for cable_db_obj in ptables.pjt_cables_table:
        add(cable_db_obj, ptables.pjt_cable_paths_table, None, None)

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

    cable_ids = ptables.pjt_cable_paths_table.wire_ids_for_point('pegboard', point_id)
    if cable_ids:
        return [(
            ptables.pjt_cables_table[cable_ids[0]], ptables.pjt_cable_paths_table, None, None,
            _rope_pull.DragEnd.WAYPOINT)]

    wire_ids = ptables.pjt_wire_paths_table.wire_ids_for_point('pegboard', point_id)
    if wire_ids:
        # A bundle END sits in the route of every wire through the bundle, but it is the
        # bundle that anchors there: solve it first, its wires follow (see _evaluate_points).
        if cache is None:
            index = _anchor_index(ptables)
        else:
            index = cache.get('anchor_index')
            if index is None:
                index = cache['anchor_index'] = _anchor_index(ptables)

        bundles = [entry for entry in index.get(point_id, ()) if isinstance(entry[0], _pjt_bundle.PJTBundle)]
        if bundles:
            return bundles

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
def chains_bound_to_point(point: "_point.Point") -> list:
    """Every chain's own peg-board facade (``Wire.objpegboard``/
    ``Bundle.objpegboard``) with ``suspend_updates()``/
    ``resume_updates()`` bound to *point* right now (see
    ``objects_pegboard.wire.Wire.suspend_updates``'s own docstring) --
    found by inspecting *point*'s own already-bound callbacks (the
    exact weakref list ``CallbackMixin._process_callbacks`` itself
    fires from), not by looking up which chain owns this point's id
    through the peg-board path tables (:func:`_chains_for_point`'s own
    job, for a different purpose).

    That distinction matters: a structural stub point
    (``terminal.wire_position_pegboard``/``cavity.wire_position_pegboard``)
    can be a per-wire CLONE whose own id a path-table lookup never
    resolves back to the wire actually bound to it (see
    :func:`_structural_stub_ids`'s own docstring -- "every terminal/
    cavity stub past the first wire on that terminal is a clone at
    the same spot"). Confirmed live, 2026-10-17: a path-table lookup
    by point id silently found nothing for several of
    ``PJTHousing._update_position_pegboard``'s own moved points,
    leaving their wires' geometry rebuild unsuspended. Inspecting the
    point's own bindings directly has no such gap -- whatever object
    actually bound itself to THIS exact ``Point`` instance is exactly
    what needs suspending, no id resolution involved at all.

    Skips a dead weakref (its owner already collected) and any bound
    callback whose owner isn't chain-like (``WireSlackHandler``'s own
    ``_on_pegboard_changed``, bound to some of the same points, has no
    ``suspend_updates`` of its own and is correctly skipped here).
    """
    result = []
    for ref in list(point.__callbacks__):
        cb = ref()
        if cb is None:
            continue

        owner = getattr(cb, '__self__', None)
        if owner is not None and hasattr(owner, 'suspend_updates'):
            result.append(owner)

    return result


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
def _fold_limit(chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"], required_length: float) -> float:
    """The closest the two ends of a chain can come before it folds over on itself: one zig-zag's worth of spacing
    (``zigzag_length_factor`` diameters, the same spacing the solver gives a zig-zag its room with), never more than the chain's own
    length. Slack is taken up as bends until the ends are this close; closer than that the chain would fold, so the far end is
    pushed (:func:`_pushed_far_position`)."""
    return min(Config.zigzag_length_factor * max(_chain_diameter(chain_db_obj), _MIN_FOLD_DIAMETER_MM), max(required_length, 0.0))


@_debug.logfunc
@_check_types.do
def _pushed_far_position(
    far_xz: tuple[float, float], near_target_xz: tuple[float, float], min_span: float, old_span: float,
    hint_xz: tuple[float, float]
) -> tuple[float, float]:
    """*far_xz* unmoved, unless the near end was moved CLOSER to it and the straight distance between them is now less than
    *min_span* (the chain would fold over on itself): then *far_xz* is pushed straight away from *near_target_xz* until the distance
    is exactly *min_span*.

    :param old_span: The distance before the near end moved: a chain that is already closer than *min_span* is left alone unless it
        is being compressed further (a reconcile that moves nothing never pushes anything).
    :param hint_xz: The far end minus the near end as it was, for the direction when the two now coincide.
    """
    dx = far_xz[0] - near_target_xz[0]
    dz = far_xz[1] - near_target_xz[1]
    straight = math.hypot(dx, dz)

    if straight >= min_span - 1e-6 or straight >= old_span - 1e-6:
        return far_xz

    if straight < 1e-9:
        dx, dz = hint_xz
        straight = math.hypot(dx, dz)

        if straight < 1e-9:
            dx, dz, straight = 1.0, 0.0, 1.0

    scale = min_span / straight
    return near_target_xz[0] + dx * scale, near_target_xz[1] + dz * scale


@_debug.logfunc
@_check_types.do
def _housing_id_of(ptables: "_PJTPegboardTable", attach_point_id: bytes) -> bytes | None:
    """The housing a terminal whose attach point is *attach_point_id* is seated in, or ``None`` (not a terminal's attach point, or a
    terminal that is not in a cavity)."""
    rows = ptables.pjt_terminals_table.select('id', attach_point_pegboard_id=attach_point_id)
    if not rows:
        return None

    cavity_id = ptables.pjt_terminals_table[rows[0][0]].cavity_id
    if cavity_id is None:
        return None

    housing_rows = ptables.pjt_cavities_table.select('housing_id', id=cavity_id)
    if not housing_rows:
        return None

    return housing_rows[0][0]


@_debug.logfunc
@_check_types.do
def _lead_pieces(ptables: "_PJTPegboardTable", conductor_id: bytes, split_id: bytes) -> tuple[list, list, bytes]:
    """Follow a conductor's lead outward from the cable's split point at *split_id*, over the wire service loops in it.

    :returns: ``(pieces, loops, end_id)``: the wires of the lead in order from the split point, the loops between them, and the board
        point the lead ends on (a terminal's attach point, or a free end).
    """
    wires_table = ptables.pjt_wires_table
    loops_table = ptables.pjt_wire_service_loops_table
    rows = wires_table.select('id', 'start_point_pegboard_id', 'stop_point_pegboard_id', cable_conductor_id=conductor_id)

    pieces: list = []
    loops: list = []
    used: set = set()
    current = split_id

    while True:
        found = None

        for wire_id, start_id, stop_id in rows:
            if wire_id in used:
                continue

            if start_id == current:
                found = (wire_id, stop_id)
            elif stop_id == current:
                found = (wire_id, start_id)

            if found is not None:
                break

        if found is None:
            return pieces, loops, current

        used.add(found[0])
        pieces.append(wires_table[found[0]])
        current = found[1]

        loop_rows = loops_table.select('id', OR=True, start_point_pegboard_id=current, stop_point_pegboard_id=current)
        if not loop_rows:
            return pieces, loops, current

        loop = loops_table[loop_rows[0][0]]
        loops.append(loop)

        if loop.start_position_pegboard_id == current:
            current = loop.stop_position_pegboard_id
        else:
            current = loop.start_position_pegboard_id


@_debug.logfunc
@_check_types.do
def _pinned_info(ptables: "_PJTPegboardTable", cable_db_obj: "_pjt_cable.PJTCable", cache: dict) -> dict:
    """What the leads of a cable that are PINNED (their free end is in a terminal seated in a housing) may be on the board.

    The board does not share the 3D view's positions: where the conductors of a cable come together (the split point) can be anywhere
    relative to the housing they plug into, so a lead's length there cannot be its length in 3D. Instead, for each end of the cable and
    each housing its leads plug into, the LONGEST of those leads (its wires plus the coil of every wire service loop in it, which is
    not drawn on the board) is the most any of them may be: a shorter lead has no slack, it is straight; none may be longer. The
    wires of one lead share that length in proportion to their own.

    :returns: ``{'caps': {wire id: most that wire may be (mm)}, 'loop_points': {board point ids of the loops in pinned leads},
        'leads': [the pinned leads that have loops: {'pieces', 'caps' (of each piece), 'loops', 'split_id', 'end_id'}]}``, built once per
        solve (kept in *cache*).
    """
    key = ('pinned', cable_db_obj.db_id)
    info = cache.get(key)
    if info is not None:
        return info

    caps: dict = {}
    loop_points: set = set()
    with_loops: list = []

    for start in (True, False):
        groups: dict = {}

        for conductor in cable_db_obj.conductors:
            split_id = conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id
            if split_id is None:
                continue

            pieces, loops, end_id = _lead_pieces(ptables, conductor.db_id, split_id)
            if not pieces:
                continue

            housing_id = _housing_id_of(ptables, end_id)
            if housing_id is None:
                continue

            lengths = [_anchors_and_length(ptables, piece)[2] for piece in pieces]
            total = sum(lengths) + sum(float(loop.length_mm) for loop in loops)
            groups.setdefault(housing_id, []).append((pieces, lengths, loops, total, split_id, end_id))

        for leads in groups.values():
            longest = max(lead[3] for lead in leads)

            for pieces, lengths, loops, _total, split_id, end_id in leads:
                scale = longest / max(sum(lengths), 1e-9)

                for piece, length in zip(pieces, lengths):
                    caps[piece.db_id] = length * scale

                for loop in loops:
                    loop_points.add(loop.start_position_pegboard_id)
                    loop_points.add(loop.stop_position_pegboard_id)

                if loops:
                    # (the lead is a straight line from the housing to the split point, the loops at their share of it: see
                    # _evaluate_points' place_pinned_loops)
                    with_loops.append({
                        'pieces': pieces, 'caps': [length * scale for length in lengths], 'loops': loops,
                        'split_id': split_id, 'end_id': end_id})

    info = cache[key] = {'caps': caps, 'loop_points': loop_points, 'leads': with_loops}
    return info


@_debug.logfunc
@_check_types.do
def _pinned_cap(ptables: "_PJTPegboardTable", wire_db_obj: "_pjt_wire.PJTWire", cache: dict) -> float | None:
    """The most *wire_db_obj* may be on the board when it is a wire of a PINNED lead (see :func:`_pinned_info`), else ``None``."""
    conductor_id = wire_db_obj.cable_conductor_id
    if conductor_id is None:
        return None

    cable_id = ptables.pjt_cable_conductors_table[conductor_id].cable_id
    return _pinned_info(ptables, ptables.pjt_cables_table[cable_id], cache)['caps'].get(wire_db_obj.db_id)


@_debug.logfunc
@_check_types.do
def straighten_pinned_leads(mainframe: "_ui.MainFrame") -> int:
    """Take the bends out of every wire of a PINNED lead (see :func:`_pinned_info`) that has any: a pinned wire has no slack, and a
    project saved before that rule (or after a drag that went wrong) has bends in them that nothing would re-solve until the housing
    or the cable is next dragged. Each such wire is re-solved as a drag of nothing: it is straight afterwards, and a wire that is
    already over its cap is left as long as it is (``tolerate_stretch``), never pulled in here.

    :returns: How many wires were straightened.
    """
    ptables = mainframe.project.ptables
    cache: dict = {}
    count = 0

    for cable_db_obj in ptables.pjt_cables_table:
        for wire_id in _pinned_info(ptables, cable_db_obj, cache)['caps']:
            wire_db_obj = ptables.pjt_wires_table[wire_id]
            leading, trailing = _stub_boundary(ptables, wire_db_obj)

            if len(ptables.pjt_wire_paths_table.point_ids(wire_id, 'pegboard')) <= leading + trailing:
                continue

            realize_length_change(mainframe, wire_db_obj, tolerate_stretch=True)
            count += 1

    _trace(lambda: ('straightened', count, 'pinned wires',))

    return count


@_debug.logfunc
@_check_types.do
def _pinned_loop_points(ptables: "_PJTPegboardTable", cache: dict) -> set:
    """The board points of every wire service loop that is in a pinned lead: those loops are a single point on the board."""
    points: set = set()

    for cable_db_obj in ptables.pjt_cables_table:
        points |= _pinned_info(ptables, cable_db_obj, cache)['loop_points']

    return points


@_debug.logfunc
@_check_types.do
def _is_owned_end(ptables: "_PJTPegboardTable", point_id: bytes) -> bool:
    """Whether *point_id* is a point of a terminal (its attach point), a splice or a wire service loop, rather than a bare wire end."""
    if ptables.pjt_terminals_table.select('id', attach_point_pegboard_id=point_id):
        return True

    for table in (ptables.pjt_splices_table, ptables.pjt_wire_service_loops_table):
        if table.select('id', OR=True, start_point_pegboard_id=point_id, stop_point_pegboard_id=point_id):
            return True

    return False


@_debug.logfunc
@_check_types.do
def _cable_node(ptables: "_PJTPegboardTable", point_id: bytes) -> tuple[str, list[bytes]] | None:
    """The part of a placed cable that moves as one piece with *point_id*, as :func:`_node_for_point` answers it, or ``None`` when no
    cable owns the point, or the point is one of the cable's two ends.

    A conductor's split point or free end (where a lead comes out of the trunk, or the lead's end when nothing is attached to it) is
    the END of the cable it comes out of, translated together with the cable's own end point and the other conductors' split points
    and free ends: something pulling on a lead drags that end of the cable. The rest of the cable is not part of it: the cable is a
    rope between its two ends (a chain, solved like a wire), so its own slack is used up before its far end is pulled, and
    the far end's conductors only move when the cable is taut (and, in the other direction, are pushed when it has folded).

    The cable's own end point answers the same group when the end is split. An end that is not split is a lone point (``None``): its
    conductors' points are children of the end's and follow by themselves.
    """
    for cable in ptables.pjt_cables_table:
        owned: dict[bool, list[bytes]] = {True: [], False: []}

        for conductor in cable.conductors:
            for start in (True, False):
                split_id = (
                    conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id)
                if split_id is None:
                    continue

                owned[start].append(split_id)
                end_id = conductor.start_position_pegboard_id if start else conductor.stop_position_pegboard_id

                # The lead's free end goes with the cable only when nothing is on it: a terminal's attach point, a splice's or a loop's
                # point belongs to that object (and its housing), and moving it here would tear it off. That lead is simply pulled
                # on, as any wire is, when the cable moves away from it.
                if end_id is not None and not _is_owned_end(ptables, end_id):
                    owned[start].append(end_id)

        # A solder sleeve on a split end lies on the split plane and goes with the end: its three board points, which are also the
        # end of its pigtail (the lead's end on the sleeve is the sleeve's branch point), so the pigtail is solved as a wire of the end.
        for start in (True, False):
            sleeve_id = cable.start_shield_splice_id if start else cable.stop_shield_splice_id

            if sleeve_id is None or not owned[start]:
                continue

            sleeve = ptables.pjt_splices_table[sleeve_id]
            owned[start].extend(
                point for point in (sleeve.start_position_pegboard_id, sleeve.stop_position_pegboard_id,
                                    sleeve.branch_position_pegboard_id) if point is not None)

        ends = {True: cable.start_position_pegboard_id, False: cable.stop_position_pegboard_id}

        for start in (True, False):
            if owned[start] and (point_id == ends[start] or point_id in owned[start]):
                return 'rigid', [ends[start], *owned[start]]

    return None


@_debug.logfunc
@_check_types.do
def _node_for_point(ptables: "_PJTPegboardTable", point_id: bytes) -> tuple[str, list[bytes]] | None:
    """The rigid structural object that owns *point_id*, as
    ``(kind, points)`` -- *points* is every peg-board point that moves
    together with it as one object (a Transition's own centre PLUS
    every one of its branches -- centre always ``points[0]`` -- a
    Splice's or WireServiceLoop's own start AND stop together, or a
    Housing's single point); *kind* is ``'transition'`` (ROTATES when
    pulled -- see :func:`_rotated_and_translated`'s own caller),
    ``'loop'`` (a wire service loop: the point the pull arrives through
    is pulled, the other one is laid inline, straight on from the wire
    that pulls, at the loop's own span) or ``'rigid'`` (pure translation,
    same delta for every point in *points*). ``None`` if *point_id*
    belongs to none of these (a genuinely free point, owned by nothing).

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

    cable_node = _cable_node(ptables, point_id)
    if cable_node is not None:
        return cable_node

    for table in (ptables.pjt_splices_table, ptables.pjt_wire_service_loops_table):
        rows = table.select(
            'id', OR=True,
            start_point_pegboard_id=point_id, stop_point_pegboard_id=point_id)
        if rows:
            obj = table[rows[0][0]]

            if table is ptables.pjt_wire_service_loops_table:
                return 'loop', [obj.start_position_pegboard_id, obj.stop_position_pegboard_id]

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
    cascade: bool = True, chain_cache: dict | None = None, seed_chains: list[tuple] | None = None,
    held_ids: set[bytes] | None = None, tolerate_stretch: bool = False,
) -> tuple[list[tuple], dict[bytes, tuple[float, float]], dict[bytes, float]] | None:
    """Pure solve, no DB writes -- every ``(point_id, target_xz)`` pair
    in *point_targets* moving AT ONCE, cascading through whatever else
    needs to move as a result (see the module docstring's own "The
    cascade" section for the rule in plain words).

    *seed_chains*: ``(chain_db_obj, path_table, layouts_table,
    layout_facade_cls, drag_end)`` tuples (as :func:`_chains_for_point`
    returns) evaluated with NO point held fixed -- used for a wire just
    routed through a bundle, where either of the wire's own ends may
    have to be pulled (see the bundle-wire branch in the loop below).
    *held_ids*: point ids that must not be pulled back by that branch (the
    wire end the user is dragging) -- the bundle is pulled instead.
    *tolerate_stretch*: a chain whose ends are ALREADY further apart than its length (saved that way, or left so by an earlier edit) is
    taken as taut at the span it has: only stretching it further pulls, and the move is not refused because of what was wrong before it.
    For a drag (``resolve_rigid_move``) and the safety net of a point's move; not for a change of the chain's own length, which is
    exactly the stretch that has to be pulled out (``realize_length_change`` from a 3D length edit).

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

    _trace(lambda: ('solve', [(_short(point_id), _xz(xz)) for point_id, xz in point_targets], f'held={[_short(i) for i in (held_ids or [])]}',))

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
    pull_count = [0]

    @_check_types.do
    def pull_node(
        point_id: bytes, from_xz: tuple[float, float], to_xz: tuple[float, float],
        chain_id: bytes, is_repull: bool, inline_from: tuple[float, float] | None = None
    ) -> bool:
        """Move the rigid node that owns *point_id* so that point's
        EFFECTIVE position goes from *from_xz* to *to_xz*, deciding every
        one of the node's points in fixed/write_points and queuing them.

        *is_repull*: the node was already pulled earlier in this solve, so
        its points move on from where this solve put them (fixed[]) instead
        of from where the DB has them.

        *inline_from*: where the chain that pulls (or pushes) the node has its near end. A wire service loop uses it to stay in line
        with that wire: its other point is laid at the loop's own span straight on from the near end through *to_xz*.

        :returns: ``False`` when a re-pull would exceed _MAX_REPULLS -- the
            node is left untouched.
        """
        pull_count[0] += 1
        if pull_count[0] > _MAX_PULLS_PER_SOLVE:
            _trace(lambda: ('  pull budget used up: the move is refused',))
            return False

        node = _node_for_point(ptables, point_id)
        kind, node_points = ('rigid', [point_id]) if node is None else node

        _trace(lambda: ('  pull node', kind, [_short(p) for p in node_points], 'through', _short(point_id), _xz(from_xz), '->', _xz(to_xz),
               f'repull={is_repull}', f'inline_from={_xz(inline_from)}',))

        if is_repull:
            repull_count = repulls.get(node_points[0], 0) + 1
            repulls[node_points[0]] = repull_count
            if repull_count > _MAX_REPULLS:
                return False

        @_check_types.do
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
        elif kind == 'loop' and inline_from is not None and len(node_points) == 2:
            other_id = node_points[1] if node_points[0] == point_id else node_points[0]
            other_old = moved_from(other_id)
            span = math.hypot(other_old[0] - from_xz[0], other_old[1] - from_xz[1])

            # a loop in a pinned lead is not drawn on the board: a single point, its two points on one spot
            if point_id in _pinned_loop_points(ptables, chain_cache):
                span = 0.0

            ux, uz = to_xz[0] - inline_from[0], to_xz[1] - inline_from[1]
            length = math.hypot(ux, uz)

            if length < 1e-9:
                ux, uz = other_old[0] - from_xz[0], other_old[1] - from_xz[1]
                length = math.hypot(ux, uz)

            if length < 1e-9:
                ux, uz, length = 1.0, 0.0, 1.0

            placed = ((point_id, to_xz), (other_id, (to_xz[0] + ux / length * span, to_xz[1] + uz / length * span)))

            for p, new_xz in placed:
                if p in fixed and p not in write_points:
                    continue

                fixed[p] = new_xz
                write_points[p] = new_xz
                pending.append(p)
        else:
            delta = (to_xz[0] - from_xz[0], to_xz[1] - from_xz[1])

            for p in node_points:
                # A point the user is placing (a dragged target) is decided already and must not be moved again by the pull: a lead's
                # free end is one of the points of the cable it pulls, and moving it too left the lead as long as it was dragged.
                if p in fixed and p not in write_points:
                    continue

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

    @_check_types.do
    def pull_if_needed(
        chain_id: bytes, far_point_id: bytes, far_xz: tuple[float, float],
        near_target_xz: tuple[float, float], required_length: float,
        min_span: float = 0.0, near_old_xz: tuple[float, float] | None = None,
    ) -> tuple[float, float]:
        """The far end of a chain whose near end is going to *near_target_xz*: pulled straight toward it when the chain is too short
        to reach, pushed straight away from it when the near end was moved so close that the chain would fold over on itself
        (*min_span*), left alone otherwise (the chain's own bends take the slack up, or give it back)."""
        is_repull = False
        entry_far_xz = far_xz

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

        # A node that an earlier chain pulled and this one pulls again is held by several chains at once (the leads of a cable's end
        # all run to one housing, each taut in its own direction): the straight pull toward the near end satisfies one chain and
        # breaks the next, again and again, and never settles. The move that keeps every one of them as it was is to carry the node by
        # what its near end moved (the near ends are points of one rigid group that moved together): a chain that was fine stays fine.
        if is_repull and pulled_xz != far_xz and near_old_xz is not None:
            carried_xz = (entry_far_xz[0] + near_target_xz[0] - near_old_xz[0], entry_far_xz[1] + near_target_xz[1] - near_old_xz[1])

            if math.hypot(carried_xz[0] - near_target_xz[0], carried_xz[1] - near_target_xz[1]) <= required_length + _REPULL_TOLERANCE_MM:
                pulled_xz = carried_xz

        if pulled_xz == far_xz and near_old_xz is not None:
            pulled_xz = _pushed_far_position(
                far_xz, near_target_xz, min_span,
                math.hypot(entry_far_xz[0] - near_old_xz[0], entry_far_xz[1] - near_old_xz[1]),
                (entry_far_xz[0] - near_old_xz[0], entry_far_xz[1] - near_old_xz[1]))

        _trace(lambda: ('  far end', _short(far_point_id), 'of', _short(chain_id), 'near', _xz(near_target_xz), 'far', _xz(far_xz),
               'span', round(math.hypot(far_xz[0] - near_target_xz[0], far_xz[1] - near_target_xz[1]), 2),
               'length', round(required_length, 2), 'fold', round(min_span, 2), '->', _xz(pulled_xz),))

        if is_repull:
            if math.hypot(pulled_xz[0] - far_xz[0], pulled_xz[1] - far_xz[1]) <= _REPULL_TOLERANCE_MM:
                return far_xz
        elif pulled_xz == far_xz:
            return far_xz

        if not pull_node(far_point_id, far_xz, pulled_xz, chain_id, is_repull, near_target_xz):
            _trace(lambda: ('  re-pull limit reached for', _short(far_point_id), ': left where it is',))
            return far_xz

        return pulled_xz

    def eval_bundle_wire(
        chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end, point_id, target_xz,
    ) -> str:
        """Solve one wire through ONE bundle with :mod:`bundle_wire_model`
        and turn its :class:`MovePlan` into pulls on the real points.

        :returns: ``'skip'`` (not a single-bundle wire -- caller falls back to
            the plain chain solve), ``'infeasible'`` or ``'done'``.
        """
        protected_runs = _wire_protected_runs(ptables, chain_db_obj, 'pegboard')
        if len(protected_runs) != 1:
            return 'skip'

        start_xz, stop_xz, required_length, leading, trailing = _anchors_and_length(ptables, chain_db_obj)
        gap_lengths = _wire_gap_lengths3d(ptables, chain_db_obj, protected_runs, leading, trailing)
        if gap_lengths is None:
            return 'skip'

        old_ids_full = list(path_table.point_ids(chain_db_obj.db_id, 'pegboard'))
        route_rows = path_table.for_wire(chain_db_obj.db_id, 'pegboard')
        run_start, run_end = protected_runs[0]

        def tagged(i: int) -> bool:
            row = route_rows[i]
            return (row.bundle_id is not None or row.transition_id is not None
                    or row.transition_branch_id is not None)

        bundle_ids = {route_rows[i].bundle_id for i in range(run_start, run_end + 1)
                      if route_rows[i].bundle_id is not None}
        if len(bundle_ids) != 1:
            return 'skip'

        bundle_db = ptables.pjt_bundles_table[next(iter(bundle_ids))]
        first_tagged = next(i for i in range(run_start, run_end + 1) if tagged(i))
        last_tagged = next(i for i in range(run_end, run_start - 1, -1) if tagged(i))

        bundle_end_ids = [bundle_db.start_position_pegboard_id, bundle_db.stop_position_pegboard_id]
        end_a_id, end_b_id = old_ids_full[first_tagged], old_ids_full[last_tagged]
        if end_a_id not in bundle_end_ids or end_b_id not in bundle_end_ids or end_a_id == end_b_id:
            return 'skip'

        a_end = bundle_end_ids.index(end_a_id)
        guard_ids = {
            0: old_ids_full[run_start] if run_start < first_tagged else None,
            1: old_ids_full[run_end] if run_end > last_tagged else None}

        def db_xz(pid: bytes) -> tuple[float, float]:
            p_ = points_table[pid].point
            return float(p_.x), float(p_.z)

        def point_xz(pid: bytes) -> tuple[float, float]:
            return fixed[pid] if pid in fixed else db_xz(pid)

        def authoritative(pid: bytes) -> bool:
            return pid in fixed and pid not in write_points

        def moved_xz(pid: bytes, base_xz: tuple[float, float]) -> tuple[float, float]:
            # A wire end's effective anchor after its raw point moved.
            if pid not in fixed:
                return base_xz
            rx, rz = db_xz(pid)
            return base_xz[0] + fixed[pid][0] - rx, base_xz[1] + fixed[pid][1] - rz

        # The stubs as they are NOW (length and direction), per bundle end.
        directions: list[tuple[float, float]] = []
        stub_lengths: list[float] = []
        for side, bundle_index in ((0, a_end), (1, 1 - a_end)):
            guard_id = guard_ids[side]
            end_id = bundle_end_ids[bundle_index]
            if guard_id is None:
                directions.append((0.0, 0.0))
                stub_lengths.append(0.0)
                continue

            gx, gz = db_xz(guard_id)
            ex, ez = db_xz(end_id)
            length = math.hypot(gx - ex, gz - ez)
            stub_lengths.append(length)
            directions.append(((gx - ex) / length, (gz - ez) / length) if length > 1e-9 else (0.0, 0.0))

        by_end_dir = [directions[0], directions[1]] if a_end == 0 else [directions[1], directions[0]]
        by_end_len = [stub_lengths[0], stub_lengths[1]] if a_end == 0 else [stub_lengths[1], stub_lengths[0]]

        start_id = chain_db_obj.start_position_pegboard_id
        stop_id = chain_db_obj.stop_position_pegboard_id
        a_xz = moved_xz(start_id, start_xz)
        b_xz = moved_xz(stop_id, stop_xz)
        ends0 = [point_xz(bundle_end_ids[0]), point_xz(bundle_end_ids[1])]

        free_total = sum(gap_lengths)
        stored = _wire_gap_split.get(chain_db_obj.db_id)
        if stored is not None and len(stored) == 2 and abs(sum(stored) - free_total) <= 0.01:
            split = (stored[0], stored[1])
        else:
            split = (gap_lengths[0], gap_lengths[1])

        bundle_model = _bundle_wire_model.BundleModel(
            ends0, float(bundle_db.length_mm),
            (not authoritative(bundle_end_ids[0]), not authoritative(bundle_end_ids[1])),
            (by_end_dir[0], by_end_dir[1]), (by_end_len[0], by_end_len[1]))
        wire_model = _bundle_wire_model.WireModel(
            a_xz, b_xz, not authoritative(start_id), not authoritative(stop_id), free_total, split, a_end)

        held = None
        if start_id in held_ids:
            held = 'a'
        elif stop_id in held_ids:
            held = 'b'
        elif authoritative(start_id):
            held = 'a'
        elif authoritative(stop_id):
            held = 'b'

        plan = _bundle_wire_model.Assembly(wire_model, bundle_model).plan(held)
        if not plan.feasible:
            _logger.error(
                f'rope_pull_handler: wire {chain_db_obj.db_id!r} cannot be fitted through its bundle: {plan.reason}')
            return 'infeasible'

        def move(pid: bytes, frm: tuple[float, float], to: tuple[float, float]) -> bool:
            if math.hypot(to[0] - frm[0], to[1] - frm[1]) <= 1e-6:
                return True
            return pull_node(pid, frm, to, chain_db_obj.db_id, pid in write_points)

        if not (move(start_id, a_xz, plan.a) and move(stop_id, b_xz, plan.b)
                and move(bundle_end_ids[0], ends0[0], plan.ends[0])
                and move(bundle_end_ids[1], ends0[1], plan.ends[1])):
            return 'infeasible'

        # The stubs ride rigidly with their bundle ends: write where they now belong,
        # so a dragged (not pulled) bundle end carries its stub too.
        for side in (0, 1):
            guard_id = guard_ids[side]
            if guard_id is None:
                continue
            target = plan.guards[side]
            if math.hypot(target[0] - db_xz(guard_id)[0], target[1] - db_xz(guard_id)[1]) > 1e-6:
                write_points[guard_id] = (float(target[0]), float(target[1]))

        # The bundle's own end points are only reachable through the WIRE (they sit in its
        # route, not in the bundle's waypoint list), so nothing else would ever re-solve the
        # bundle's interior after they moved: do it here, so it keeps its 3D length.
        if bundle_db.db_id not in seen_chains and (
                bundle_end_ids[0] in write_points or bundle_end_ids[1] in write_points
                or _offline_store.overlay(bundle_db.db_id) is not None):
            seen_chains.add(bundle_db.db_id)

            b_start = point_xz(bundle_end_ids[0])
            b_stop = point_xz(bundle_end_ids[1])
            _, _, b_required, b_leading, b_trailing = _anchors_and_length(ptables, bundle_db)
            b_result = _rope_pull.solve_chain(
                b_start, b_stop, b_required, _rope_pull.DragEnd.START, b_start,
                _chain_diameter(bundle_db), Config.zigzag_length_factor, Config.threshold_factor)

            if not b_result.accepted:
                return 'infeasible'

            entries.append((
                bundle_db, ptables.pjt_bundle_paths_table, ptables.pjt_bundle_layouts_table,
                _bundle_layout.BundleLayout, _rope_pull.DragEnd.START, None, None, b_result,
                b_start, b_stop, b_required, b_leading, b_trailing))

        whole_result = _rope_pull.solve_chain(
            plan.a, plan.b, required_length, drag_end, plan.a,
            _chain_diameter(chain_db_obj), Config.zigzag_length_factor, Config.threshold_factor)

        entries.append((
            chain_db_obj, path_table, layouts_table, layout_facade_cls,
            drag_end, point_id, target_xz, whole_result, plan.a, plan.b,
            [plan.split[0], plan.split[1]], leading, trailing))
        return 'done'

    seed_queue = list(seed_chains or [])

    held_ids = held_ids or set()

    def place_pinned_loops() -> bool:
        """Lay the wire service loops of every pinned lead this solve touched on the straight line from the housing to the split point.

        A pinned lead has no slack: it is one straight line, a loop in it at its share of that line (the pieces' caps, counted from the
        split point). A loop only moves when a piece beside it has to pull it, so a housing or a cable moved sideways left the loop
        where it was and the lead bent there. Each loop's two points go to their place; the pieces beside them are solved again.

        :returns: whether any loop point was moved.
        """
        moved = False

        for cable_db_obj in ptables.pjt_cables_table:
            for lead in _pinned_info(ptables, cable_db_obj, chain_cache)['leads']:
                pieces = lead['pieces']

                if not any(piece.db_id in seen_chains for piece in pieces):
                    continue

                last = pieces[-1]
                start_xz, stop_xz = _anchors_and_length(ptables, last)[:2]
                end_id, split_id = lead['end_id'], lead['split_id']
                tip = start_xz if last.start_position_pegboard_id == end_id else stop_xz

                # the effective end moves by the delta of the terminal's own point
                if end_id in fixed:
                    raw = points_table[end_id].point
                    tip = (tip[0] + fixed[end_id][0] - float(raw.x), tip[1] + fixed[end_id][1] - float(raw.z))

                if split_id in fixed:
                    split = fixed[split_id]
                else:
                    split_point = points_table[split_id].point
                    split = (float(split_point.x), float(split_point.z))

                total = sum(lead['caps'])
                if total < 1e-9:
                    continue

                done = 0.0

                for k, loop in enumerate(lead['loops']):
                    done += lead['caps'][k]
                    fraction = done / total
                    wanted = (split[0] + (tip[0] - split[0]) * fraction, split[1] + (tip[1] - split[1]) * fraction)
                    loop_moved = False

                    for loop_point_id in (loop.start_position_pegboard_id, loop.stop_position_pegboard_id):
                        if loop_point_id in fixed:
                            now = fixed[loop_point_id]
                        else:
                            loop_point = points_table[loop_point_id].point
                            now = (float(loop_point.x), float(loop_point.z))

                        if math.hypot(now[0] - wanted[0], now[1] - wanted[1]) <= 1e-3:
                            continue

                        fixed[loop_point_id] = wanted
                        write_points[loop_point_id] = wanted
                        pending.append(loop_point_id)
                        loop_moved = True

                    if loop_moved:
                        moved = True
                        stale_ids = {pieces[k].db_id, pieces[k + 1].db_id}
                        seen_chains.difference_update(stale_ids)
                        entries[:] = [entry for entry in entries if entry[0].db_id not in stale_ids]

        return moved

    place_rounds = 0

    while True:
        while pending or seed_queue:
            if pending:
                point_id = pending.pop()
                target_xz = fixed[point_id]
                chains = _chains_for_point(ptables, point_id, chain_cache)
            else:
                point_id = target_xz = None
                chains = [seed_queue.pop()]

            for chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end in chains:
                if chain_db_obj.db_id in seen_chains:
                    continue
                seen_chains.add(chain_db_obj.db_id)

                start_xz, stop_xz, required_length, leading, trailing = _anchors_and_length(
                    ptables, chain_db_obj)

                # A wire of a lead PINNED to a housing has no slack: it is straight, and the most it may be is the longest lead's length of
                # its cable end and housing (_pinned_info). Its length in 3D has no say: the board's positions are not the 3D view's.
                pinned_cap = None

                if drag_end is not _rope_pull.DragEnd.WAYPOINT and _is_wire_chain(chain_db_obj):
                    pinned_cap = _pinned_cap(ptables, chain_db_obj, chain_cache)

                    if pinned_cap is not None:
                        required_length = pinned_cap

                if tolerate_stretch:
                    required_length = max(required_length, math.hypot(stop_xz[0] - start_xz[0], stop_xz[1] - start_xz[1]))

                # A wire routed through ONE bundle is solved as a bundle/wire
                # assembly (bundle_wire_model), not as one start -> stop span.
                if drag_end is not _rope_pull.DragEnd.WAYPOINT and _is_wire_chain(chain_db_obj):
                    outcome = eval_bundle_wire(
                        chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end, point_id, target_xz)
                    if outcome == 'infeasible':
                        _trace(lambda: ('  REFUSED:', _label(chain_db_obj), 'through its bundle is infeasible',))
                        return None
                    if outcome == 'done':
                        continue

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

                min_span = _fold_limit(chain_db_obj, required_length)

                if pinned_cap is not None:
                    min_span = 0.0

                if drag_end is _rope_pull.DragEnd.START:
                    stop_xz = pull_if_needed(
                        chain_db_obj.db_id, chain_db_obj.stop_position_pegboard_id, stop_xz,
                        effective_target, required_length, min_span, start_xz)
                elif drag_end is _rope_pull.DragEnd.STOP:
                    start_xz = pull_if_needed(
                        chain_db_obj.db_id, chain_db_obj.start_position_pegboard_id, start_xz,
                        effective_target, required_length, min_span, stop_xz)
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
                        if pull_node(point_id, effective_target, relieved_xz, chain_db_obj.db_id, True, other_xz):
                            effective_target = relieved_xz
                            target_xz = fixed[point_id]

                # a pinned wire is as long as the straight line between its ends (never over its cap: then nothing can be solved)
                if pinned_cap is not None:
                    if drag_end is _rope_pull.DragEnd.START:
                        far_xz = stop_xz
                    else:
                        far_xz = start_xz

                    required_length = min(required_length, math.hypot(far_xz[0] - effective_target[0], far_xz[1] - effective_target[1]))

                result = _rope_pull.solve_chain(
                    start_xz, stop_xz, required_length, drag_end, effective_target,
                    _chain_diameter(chain_db_obj), Config.zigzag_length_factor, Config.threshold_factor)

                _trace(lambda: (' ', _label(chain_db_obj), drag_end.name, 'start', _xz(start_xz), 'stop', _xz(stop_xz), 'near', _xz(effective_target),
                       'length', round(required_length, 2), 'accepted', result.accepted, 'bends', max(len(result.points) - 2, 0),))

                if not result.accepted:
                    _trace(lambda: ('  REFUSED:', _label(chain_db_obj), 'cannot reach even straight: the move is infeasible',))
                    return None

                entries.append((
                    chain_db_obj, path_table, layouts_table, layout_facade_cls,
                    drag_end, point_id, target_xz, result, start_xz, stop_xz, required_length,
                    leading, trailing))

                # Wires routed through this bundle follow it: their ends are pulled
                # behind it, slack absorbed, exactly as when the wire itself is dragged.
                if isinstance(chain_db_obj, _pjt_bundle.PJTBundle):
                    for wire_db_obj in chain_db_obj.wires:
                        if wire_db_obj.db_id in seen_chains:
                            continue
                        seen_chains.add(wire_db_obj.db_id)

                        outcome = eval_bundle_wire(
                            wire_db_obj, ptables.pjt_wire_paths_table, ptables.pjt_wire_layouts_table,
                            _wire_layout.WireLayout, _rope_pull.DragEnd.START, None, None)
                        if outcome == 'infeasible':
                            _trace(lambda: ('  REFUSED: a wire through the bundle is infeasible',))
                            return None


        # the loops of the pinned leads are put on their straight lines, and what that moves is solved from there
        place_rounds += 1
        if place_rounds > 3 or not place_pinned_loops():
            break

    _trace(lambda: ('  done:', len(entries), 'chains,', len(write_points), 'points moved', {_short(p): _xz(xz) for p, xz in write_points.items()},))

    return entries, write_points, write_yaws


# Per wire: how its free length (outside the bundle stubs) is currently split
# between its stretches, so a drag slides slack through the bundle from where
# it was left. Memory only; falls back to the 3D split when absent or stale.
_wire_gap_split: dict[bytes, list[float]] = {}

# Bundles whose wires are being re-fitted by _commit_points_body right now,
# so a pull that reaches the same bundle again can't loop.
_bundle_followups: set[bytes] = set()

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

    _trace(lambda: ('commit', len(entries), 'chains', f'in_progress={in_progress}', [(_label(entry[0]), len(entry[7].points) - 2) for entry in entries],))

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

    # Every chain's own pegboard facade this whole commit could touch, so
    # each one's own geometry rebuild (Wire/Bundle._recalculate_geometry)
    # can be suspended for the WHOLE commit below instead of once per
    # point moved -- see Wire.suspend_updates's own docstring. Covers
    # every chain _evaluate_points already found (entries) AND every
    # chain actually bound to a write_points anchor (chains_bound_to_
    # point -- not a path-table lookup by id, see its own docstring for
    # why: a cascade-pulled node can belong to a chain that doesn't
    # otherwise appear in entries).
    suspended: dict[int, object] = {}

    for entry in entries:
        chain_obj = entry[0].get_object()
        if chain_obj is not None:
            suspended[id(chain_obj.objpegboard)] = chain_obj.objpegboard

    for point_id in write_points:
        for objpegboard in chains_bound_to_point(points_table[point_id].point):
            suspended[id(objpegboard)] = objpegboard

    for objpegboard in suspended.values():
        objpegboard.suspend_updates()

    try:
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
            # A guard stub rides rigidly with the bundle end it is attached
            # to, every frame (the exact tangent-based placement runs on the
            # bundle's own commit) -- so a wire reconcile never sees a stale
            # stub, mid-drag included.
            old_point = points_table[point_id].point
            move_dx, move_dz = x - float(old_point.x), z - float(old_point.z)
            if move_dx != 0.0 or move_dz != 0.0:
                for guard_id in _wire_routing_handler.guard_points_at(ptables, 'pegboard', point_id):
                    if guard_id not in write_points:
                        _move_point(
                            points_table[guard_id].point,
                            float(points_table[guard_id].point.x) + move_dx,
                            float(points_table[guard_id].point.z) + move_dz)

            # _move_point's own no-op short-circuit applies here too: a
            # cascade-pulled anchor this solve decided doesn't actually
            # need to move (its own far-end delta already rounded to
            # nothing) shouldn't fire every one of its bound callbacks --
            # WireSlackHandler among them, for a wire/bundle anchor -- for
            # a write that changes nothing.
            _move_point(points_table[point_id].point, x, z)

        # Bundles first (user, 2026-10-29): a wire's reconcile reads its
        # guard stubs, which only a finished bundle commit has repositioned.
        ordered_entries = sorted(entries, key=lambda e: not isinstance(e[0], _pjt_bundle.PJTBundle))
        committed_wire_ids = {e[0].db_id for e in entries if not isinstance(e[0], _pjt_bundle.PJTBundle)}
        followup_bundles: list = []

        for (
            chain_db_obj, path_table, layouts_table, layout_facade_cls, drag_end, point_id, target_xz,
            result, start_xz, stop_xz, required_length, leading, trailing
        ) in ordered_entries:
            interior = result.points[1:-1]
            pin_point_id = point_id if drag_end is _rope_pull.DragEnd.WAYPOINT else None
            pin_xz = target_xz if drag_end is _rope_pull.DragEnd.WAYPOINT else None

            # A wire routed through a bundle/transition never goes through the
            # overlay: _apply_mid_drag/_place_active spread EVERY point of the
            # route (the bundle's shared points included) over one start->stop
            # shape, which shrinks the bundle and pulls the wire off it, and
            # _commit_overlay's set_route drops the tags. The stretch-aware
            # _reconcile_interior is the only thing that respects the run.
            is_bundle_wire = (
                drag_end is not _rope_pull.DragEnd.WAYPOINT
                and _is_wire_chain(chain_db_obj)
                and bool(_wire_protected_runs(ptables, chain_db_obj, 'pegboard')))

            if is_bundle_wire:
                if _offline_store.overlay(chain_db_obj.db_id) is not None:
                    _offline_store.release_overlay(chain_db_obj.db_id)
                    _offline_store.release(chain_db_obj.db_id)

                _reconcile_interior(
                    mainframe, chain_db_obj, path_table, layouts_table, layout_facade_cls,
                    interior, None, None, leading, trailing,
                    required_length if isinstance(required_length, list) else None)
            elif in_progress or _offline_store.overlay(chain_db_obj.db_id) is not None:
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

                # The bundle's waypoint count may have changed: every wire
                # through it follows (before any wire entry below runs).
                for wire_db_obj in chain_db_obj.wires:
                    _resync_wire_bundle_span(mainframe, wire_db_obj, chain_db_obj)

                followup_bundles.append(chain_db_obj)
    finally:
        for objpegboard in suspended.values():
            objpegboard.resume_updates()

    # Wires through a bundle that just moved/reshaped but were not part of
    # this commit's own cascade still have to be fitted to it.
    for bundle_db_obj in followup_bundles:
        if bundle_db_obj.db_id in _bundle_followups:
            continue

        _bundle_followups.add(bundle_db_obj.db_id)
        try:
            for wire_db_obj in bundle_db_obj.wires:
                if wire_db_obj.db_id not in committed_wire_ids:
                    realize_length_change(mainframe, wire_db_obj, in_progress=False)
        finally:
            _bundle_followups.discard(bundle_db_obj.db_id)


class _Waypoint:
    """One entry in a drag's working waypoint list: a database-backed point
    (``point_id`` set), or an in-memory point created mid-drag with a pseudo
    layout (``point_id`` None until the drag releases and the row is written).
    """

    __slots__ = ('point_id', 'point', 'pseudo_layout')

    @_check_types.do
    def __init__(
        self, point_id: bytes | None, point: "_point.Point", pseudo_layout: object | None
    ):
        self.point_id = point_id
        self.point = point
        self.pseudo_layout = pseudo_layout


@_debug.logfunc
@_check_types.do
def _make_pseudo_layout(chain_db_obj: object, position: "_point.Point") -> object:
    """A pseudo layout (never a database row) carrying *position* for a new
    in-memory waypoint, built on the same template as the wire probe layout."""
    from ..database.project_db import pjt_bundle as _pjt_bundle_runtime
    from ..database.project_db import pseudo_bundle_layout as _pseudo_bundle_layout
    from ..database.project_db import pseudo_wire_layout as _pseudo_wire_layout

    # a cable's waypoint is a bare point: there is no layout to stand in for
    if isinstance(chain_db_obj, _pjt_cable.PJTCable):
        return None

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
@_check_types.do
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
@_check_types.do
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
def _on_stored_route_changed(table: object, chain_id: bytes, view: str | None) -> None:
    """Drop *chain_id*'s drag state because its STORED board route was changed by something other than this module's own commit.

    A drag keeps the chain's board route in memory (the overlay: the points in service, in order, plus the store of points given up)
    and writes it back over the stored route when the drag releases (:func:`_commit_overlay`). Anything that edits the stored route
    in between -- a terminal attached to the wire (``Terminal.add_wire`` puts the terminal's and the cavity's wire-side points in
    front of the route), a waypoint added, the route re-laid -- leaves that copy stale, and writing it back erases the edit: the
    terminal's stub points left the route and the slack was bowed in from the terminal's crimp point instead of from the cavity's
    wire-side point. The route in the database is the truth, so the copy is dropped and the next drag frame builds a new one from
    it. Points the drag had given up are still in the stored route (only hidden), so their markers are shown again.

    This module's own commits release the overlay and the store before they write (:func:`_commit_overlay`), so they find nothing
    to drop here.
    """
    if view is not None and view != 'pegboard':
        return

    if not _offline_store.has_state(chain_id):
        return

    if isinstance(table, _pjt_cable_path.PJTCablePathsTable):
        layouts_table = None
    else:
        layouts_table = table.db.pjt_wire_layouts_table

    given_up = _offline_store.release(chain_id)
    _offline_store.release_overlay(chain_id)

    for entry in given_up:
        if entry.point_id is not None:
            _set_layout_visible(layouts_table, entry.point_id, True)


_pjt_wire_path_runtime.add_route_listener(_on_stored_route_changed)


@_debug.logfunc
@_check_types.do
def _set_layout_visible(
    layouts_table: _Union["_pjt_bundle_layout.PJTBundleLayoutsTable", "_pjt_wire_layout.PJTWireLayoutsTable"],
    point_id: bytes, visible: bool
) -> None:
    """Show or hide the layout marker sitting on *point_id* on the peg-board
    object itself (no database write -- see ``BasePegboard.set_visible_cache``)."""
    if layouts_table is None:
        return

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

    # Suspend the chain's own geometry rebuild for the duration of the move
    # loop below -- _place_active moves every active waypoint one at a
    # time, and each one left unsuspended would otherwise trigger its own
    # full _recalculate_geometry()/GL-stripe-capacity rebuild (confirmed
    # live, 2026-10-16: this was the dominant per-point cost of a drag).
    # suspend_updates/resume_updates (Wire/Bundle) turn that into at most
    # one rebuild for the whole batch -- see suspend_updates's own
    # docstring. Always resumed in the finally, so a raised exception
    # never leaves this chain's own recalculation suspended forever.
    chain_obj = chain_db_obj.get_object()
    if chain_obj is not None:
        chain_obj.objpegboard.suspend_updates()

    try:
        _place_active(active, interior, start_xz, stop_xz, pin_point_id, pin_xz)
    finally:
        overlay[:] = overlay[:leading] + active + overlay[tail_start:]

        if chain_obj is not None:
            if original_count != len(active):
                # The waypoint SET itself changed -- resume_updates
                # (recalculate=False) just closes this suspend level
                # without acting on it; refresh_waypoints() below
                # re-derives the set, rebinds everything (this chain's
                # own geometry callback AND WireSlackHandler's, for a
                # wire), recalculates, and repaints regardless, so
                # resuming with its own recalculation first would only
                # be immediately redone there.
                chain_obj.objpegboard.resume_updates(recalculate=False)
                chain_obj.objpegboard.refresh_waypoints()
            else:
                # Same count: resume_updates() alone recalculates
                # exactly once if anything in this batch actually
                # moved, or does nothing at all if the whole call was a
                # true no-op (nothing was ever marked pending, since
                # _move_point's own no-op short-circuit means a point
                # that didn't move never fired _update_position in the
                # first place). This is what makes a redundant
                # reconcile (WireSlackHandler's own per-point safety
                # net firing on points a housing/transition move
                # rigidly carries along -- see its own module
                # docstring) cheap end to end: by the time it runs,
                # this chain is already exactly where the real pass
                # just put it.
                chain_obj.objpegboard.resume_updates()


@_debug.logfunc
@_check_types.do
def _place_active(
    overlay: list[_Waypoint],
    interior: list[tuple[float, float]],
    start_xz: tuple[float, float],
    stop_xz: tuple[float, float],
    pin_point_id: bytes | None,
    pin_xz: tuple[float, float] | None
) -> None:
    """Move the overlay's points onto the solver's shape, keeping the pinned
    (dragged) point on its own target. When the counts disagree, the others are
    spread evenly on the straight line between the anchors (a transient state
    that only lasts until the drag releases).

    Whether any point actually moved doesn't need tracking here --
    :func:`_move_point`'s own no-op short-circuit means a point that
    didn't move never fires a callback at all, and the chain-level
    ``Wire``/``Bundle.suspend_updates``/``resume_updates`` bracketing
    this call (see :func:`_apply_mid_drag`) already turns "did anything
    in this whole batch actually move" into "was anything left
    pending," with no help needed from this function.
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

    for entry, (x, z) in targets:
        _move_point(entry.point, x, z)


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

    if layouts_table is not None:
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

        _drop_waypoint(points_table, layouts_table, point_id)

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

    @_check_types.do
    def center_at(s: float, cast: bool) -> tuple[float, float]:
        cursor_x = center_x + dx * s
        cursor_z = center_z + dz * s
        if not cast:
            return cursor_x, cursor_z

        anchor_desired = (cursor_x + off_x, cursor_z + off_z)
        anchor_x, anchor_z = clamp_to_length_from_anchor(far_xz, anchor_desired, length)
        return anchor_x - off_x, anchor_z - off_z

    @_check_types.do
    def candidate(s: float, cast: bool) -> list[tuple[bytes, tuple[float, float]]]:
        # Every point of the group moves rigidly with the center.
        center_placed_x, center_placed_z = center_at(s, cast)
        ddx = center_placed_x - center_x
        ddz = center_placed_z - center_z
        return [
            (point_id, (float(start.x) + ddx, float(start.z) + ddz))
            for point_id, start in point_starts]

    @_check_types.do
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

    @_check_types.do
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
    iterations: int = 16,
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

    @_check_types.do
    def candidate(t: float) -> list[tuple[bytes, tuple[float, float]]]:
        return [
            (point_id, (float(start.x) + dx * t, float(start.z) + dz * t))
            for point_id, start in point_starts]

    # See _resolve_pinned_move's identical comment -- shared across this
    # whole search since every call below is a read-only solve against
    # the same unwritten ptables state.
    chain_cache: dict = {}

    full_result = _evaluate_points(ptables, candidate(1.0), chain_cache=chain_cache, tolerate_stretch=True)
    if full_result is not None:
        _commit_points(mainframe, *full_result, in_progress=in_progress)
        return 1.0

    lo, hi = 0.0, 1.0
    best_t = 0.0
    best_result = _evaluate_points(ptables, candidate(0.0), chain_cache=chain_cache, tolerate_stretch=True)

    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        mid_result = _evaluate_points(ptables, candidate(mid), chain_cache=chain_cache, tolerate_stretch=True)

        if mid_result is not None:
            lo = mid
            best_t = mid
            best_result = mid_result
        else:
            hi = mid

    _trace(lambda: ('drag resolved: fraction', round(best_t, 4), 'of', _xz(full_delta), f'feasible={best_result is not None}',))

    if best_result is not None:
        _commit_points(mainframe, *best_result, in_progress=in_progress)

    return best_t


@_debug.logfunc
@_check_types.do
def realize_length_change(
    mainframe: "_ui.MainFrame",
    chain_db_obj: _Union["_pjt_bundle.PJTBundle", "_pjt_wire.PJTWire"],
    in_progress: bool = False,
    held_point_id: bytes | None = None,
    tolerate_stretch: bool = False
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

    :param tolerate_stretch: See :func:`_evaluate_points`. The slack handler's safety net after a point moved passes ``True``; a
        change of a wire's own 3D length (the reason this function exists) does not.

    :returns: Whether the whole cascade this change triggers (if any)
        was feasible. ``False`` means something in it is infeasible
        even after every pull it allows -- a closed loop that doesn't
        fit (see :func:`_evaluate_points`'s own "why no explicit cycle
        detection" note) or genuinely nowhere left to pull -- and the
        peg-board side is deliberately left untouched rather than
        guessed at.
    """
    ptables = mainframe.project.ptables
    if _is_wire_chain(chain_db_obj) and _wire_protected_runs(
            ptables, chain_db_obj, 'pegboard'):
        # Routed through a bundle/transition: nothing is held fixed, so
        # either end of the wire may be pulled to reach it (see the
        # bundle-wire branch in _evaluate_points).
        result = _evaluate_points(
            ptables, [], cascade=is_enabled(), held_ids={held_point_id} if held_point_id else None,
            tolerate_stretch=tolerate_stretch, seed_chains=[(
                chain_db_obj, ptables.pjt_wire_paths_table, ptables.pjt_wire_layouts_table,
                _wire_layout.WireLayout, _rope_pull.DragEnd.START)])
        if result is None:
            return False

        _commit_points(mainframe, *result, in_progress=in_progress)
        return True

    # The end the user is dragging (the slack handler passes the point that moved) stays where it is and the chain pulls whatever is
    # on its other end; otherwise it is the start that stays and the stop that gives.
    held_end = chain_db_obj.stop_position_pegboard
    held_end_id = chain_db_obj.stop_position_pegboard_id

    if held_point_id is None or held_point_id != held_end_id or held_end_id == chain_db_obj.start_position_pegboard_id:
        held_end = chain_db_obj.start_position_pegboard
        held_end_id = chain_db_obj.start_position_pegboard_id

    raw_start_xz = (float(held_end.x), float(held_end.z))

    _trace(lambda: ('realize', _label(chain_db_obj), 'held end', _short(held_end_id), f'(moved point: {_short(held_point_id)})', _xz(raw_start_xz),))

    # The RAW anchor's own current position, not _anchors_and_length's
    # EFFECTIVE one -- _evaluate_points' own main loop now derives the
    # effective target from a raw-position delta (see its own comment),
    # so a genuine no-move target has to be expressed in the same raw
    # terms, or that delta math reads a nonzero "move" (the stub
    # segment's own fixed offset) out of what should be a pure no-op.
    result = _evaluate_points(
        ptables, [(held_end_id, raw_start_xz)], cascade=is_enabled(), tolerate_stretch=tolerate_stretch)
    if result is None:
        return False

    _commit_points(mainframe, *result, in_progress=in_progress)
    return True


@_debug.logfunc
@_check_types.do
def _resync_wire_bundle_span(
    mainframe: "_ui.MainFrame", wire_db_obj: "_pjt_wire.PJTWire", bundle_db_obj: "_pjt_bundle.PJTBundle",
) -> None:
    """After *bundle_db_obj*'s own solve may have changed its interior
    peg-board waypoint COUNT, re-sync *wire_db_obj*'s own protected run
    for this SPECIFIC bundle (BUNDLE_DESIGN.md 2.7 point-sharing) to
    match it -- MANDATORY, per the user's own rule, 2026-10-28: "if the
    waypoint count changes in the bundle those changes need to be
    reflected in every single wire in the bundle." Repositioning the
    SAME points is already automatic (the literal same shared row, see
    ``RouteWalk._advance``'s own construction in ``wire_routing_
    handler.py``) -- this is only needed when the COUNT itself
    changes, so a run that already matches the bundle's current
    waypoint list exactly is left alone, no DB writes at all.

    The run's own two END points (the bundle's start/stop) never
    change identity -- they are anchors, protected from every solve,
    the bundle's own included -- so only the INTERIOR entries between
    them are ever replaced here. Uses the same whole-route read/
    rebuild/``set_route``/reapply-tags dance
    ``wire_routing_handler._commit_route`` already uses for the
    initial routing, rather than a hand-rolled partial insert/delete --
    ``PJTWirePathsTable.add``'s own docstring is explicit that ``idx``
    should never be written by hand anywhere else, and deleting from
    the middle of a route has the same problem in reverse.
    """
    ptables = mainframe.project.ptables
    path_table = ptables.pjt_wire_paths_table

    rows = path_table.for_wire(wire_db_obj.db_id, 'pegboard')
    bundle_id = bundle_db_obj.db_id
    run_indices = [i for i, row in enumerate(rows) if row.bundle_id == bundle_id]
    if not run_indices:
        return

    run_start, run_end = run_indices[0], run_indices[-1]
    if run_indices != list(range(run_start, run_end + 1)):
        _logger.error(
            f'rope_pull_handler: wire {wire_db_obj.db_id!r} own bundle_id run for bundle '
            f'{bundle_id!r} is not contiguous -- refusing to resync')
        return

    first_point_id = rows[run_start].point_id
    if first_point_id == bundle_db_obj.start_position_pegboard_id:
        from_start = True
    elif first_point_id == bundle_db_obj.stop_position_pegboard_id:
        from_start = False
    else:
        _logger.error(
            f'rope_pull_handler: wire {wire_db_obj.db_id!r} own run for bundle {bundle_id!r} '
            f'does not start at either of the bundle\'s own ends -- refusing to resync')
        return

    waypoint_ids = [wp.db_id for wp in bundle_db_obj.waypoints_pegboard]
    if not from_start:
        waypoint_ids = list(reversed(waypoint_ids))

    old_interior_ids = [rows[i].point_id for i in range(run_start + 1, run_end)]
    if old_interior_ids == waypoint_ids:
        return

    old_tags = {
        row.point_id: {
            'bundle_id': row.bundle_id, 'concentric_id': row.concentric_id,
            'transition_id': row.transition_id, 'transition_branch_id': row.transition_branch_id,
        }
        for row in rows}

    old_ids = [row.point_id for row in rows]
    new_ids = old_ids[:run_start + 1] + waypoint_ids + old_ids[run_end:]

    path_table.set_route(wire_db_obj.db_id, 'pegboard', new_ids)

    for row in path_table.for_wire(wire_db_obj.db_id, 'pegboard'):
        tags = old_tags.get(row.point_id)
        if tags is None:
            # A genuinely new bundle waypoint, not previously on this
            # wire's own route at all -- an ordinary interior point of
            # the bundle's own span, never itself a transition branch
            # (only the bundle's END points ever carry those tags).
            tags = {'bundle_id': bundle_id, 'concentric_id': None,
                     'transition_id': None, 'transition_branch_id': None}

        row.bundle_id = tags.get('bundle_id')
        row.concentric_id = tags.get('concentric_id')
        row.transition_id = tags.get('transition_id')
        row.transition_branch_id = tags.get('transition_branch_id')

    wire_obj = wire_db_obj.get_object()
    if wire_obj is not None:
        wire_obj.objpegboard.refresh_waypoints()


@_debug.logfunc
@_check_types.do
def realize_bundle_and_wires(
    mainframe: "_ui.MainFrame", bundle_db_obj: "_pjt_bundle.PJTBundle", in_progress: bool = False
) -> None:
    """Reconcile *bundle_db_obj*'s own peg-board shape first, then every
    wire routed through it (user's own rule, 2026-10-28): a bundle's
    own waypoints can only ever be added/removed by the BUNDLE's own
    solve, never a wire's (:func:`_reconcile_wire_through_bundle` never
    touches them) -- a bundle obeys the exact same "peg-board length
    conforms to 3D" rule a wire does, so it is just another
    :func:`realize_length_change` call -- so the bundle must be settled
    before any wire sharing its points can be reconciled against a
    final shape. Once the bundle's own shape is written, every wire
    through it sees REPOSITIONED points for free (the literal same
    point rows, shared via ``RouteWalk``'s own construction -- see
    ``wire_routing_handler.py``) -- but a waypoint COUNT change is not
    automatic, so :func:`_resync_wire_bundle_span` runs for every wire
    first (mandatory, user's own rule, 2026-10-28), before that wire's
    own length reconciliation runs against the now-current shape.

    A wire is always longer than the bundle segment it passes through,
    so there is no equivalent ordering concern between several wires
    sharing one bundle (dropped per user instruction, 2026-10-28) --
    each wire's own call is independent once the bundle itself is done.
    """
    realize_length_change(mainframe, bundle_db_obj, in_progress=in_progress)

    for wire_db_obj in bundle_db_obj.wires:
        _resync_wire_bundle_span(mainframe, wire_db_obj, bundle_db_obj)
        realize_length_change(mainframe, wire_db_obj, in_progress=in_progress)


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

    for cable_db_obj in ptables.pjt_cables_table:
        if cable_db_obj.start_position3d_id in ids or cable_db_obj.stop_position3d_id in ids:
            realize_length_change(mainframe, cable_db_obj, in_progress=in_progress)


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

    chains = (*ptables.pjt_wires_table, *ptables.pjt_bundles_table, *ptables.pjt_cables_table)
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

        result = _evaluate_points(ptables, seeds, cascade=is_enabled(), tolerate_stretch=True)
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
