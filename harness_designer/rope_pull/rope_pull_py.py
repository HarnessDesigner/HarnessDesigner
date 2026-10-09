# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Pure-Python reference implementation of the peg-board rope-pull
solver -- see ``BUNDLE_PLACEMENT.md`` section 6b for the design this
ports, and this module's own docstrings for the exact geometry chosen
where that document only describes the desired behavior in words.

**Scope.** This module is pure numeric geometry over plain ``(x, z)``
tuples -- no database, no live objects, no project state. It answers one
question: given a WIRE OR BUNDLE's peg-board chain (start anchor, some
number of interior waypoints, stop anchor) and a real total length that
chain must always sum to (the real 3D length, via ``PJTWire.length_mm``/
``PJTBundle.length_mm`` -- the source of truth either way), what should
the WHOLE chain look like after one endpoint or waypoint is dragged to a
new position? A ``PJTWire`` and a ``PJTBundle`` row expose the same
``start_position_pegboard``/``stop_position_pegboard``/
``waypoints_pegboard``/``length_mm`` shape (the same fact
``objects_pegboard.chain_edges`` already relies on for its own, simpler
clamp), so this solver works unchanged for either -- it never reads or
cares which kind of row its two anchors/length actually came from. The
caller (eventually a drag handler) is responsible for reading the
chain's current anchors and length, calling :func:`solve_chain`, and
reconciling the returned flat point list against whatever peg-board
waypoint DB rows currently exist (adding/removing/repositioning them) --
this module knows nothing about any of that.

**The anchor rule (``BUNDLE_PLACEMENT.md`` section 6, "the anchor
model").** A chain always has exactly two real anchors. Dragging one of
them moves it to the target and leaves the OTHER anchor fixed. Dragging
an interior waypoint leaves BOTH anchors fixed and pins that waypoint at
the target instead.

**Whole-chain redistribution (the user's explicit choice over a
"local-zone-only" alternative, 2026-09-30).** Every interior waypoint,
anywhere in the chain -- not just the ones immediately touching whatever
was dragged -- is free to move. Concretely, this solver is STATELESS:
it is handed only the two anchor positions (or the anchor and the drag
target, for an anchor drag), the drag target, and the required total
length, and it recomputes the ENTIRE set of interior waypoints from
scratch every call. It does not take the chain's previous waypoints as
input at all -- their count and position have no bearing on the new
shape, only on how the caller chooses to reconcile new positions against
old DB rows (an add/remove/reposition diff, entirely the caller's
concern). This is the direct consequence of choosing "whole chain" over
"local zone": if nothing about the old waypoint layout is allowed to
anchor the new one beyond the chain's two real endpoints, there is
nothing left to feed the solver except the endpoints themselves.

**The reference skeleton.** Dragging anchor A (B fixed) or anchor B (A
fixed) gives a 2-point reference skeleton ``[fixed_end, dragged_target]``.
Dragging an interior waypoint gives a 3-point skeleton
``[start, target, stop]`` (both real anchors stay put; the dragged
waypoint becomes a third fixed/pinned point splitting the chain into two
independent spans). Either way, the reference skeleton's own straight-
line length (``base_length``) can never exceed the chain's
*required_length* -- a straight line is the shortest possible path
between two points, so if even the bare skeleton is already too long the
move is impossible and is REFUSED outright (nothing moves, matching
``BUNDLE_PLACEMENT.md``'s explicit "a move is REFUSED if there is not
enough slack available").

**Distributing slack across the skeleton's segments.** Any slack beyond
the bare skeleton (``required_length - base_length``) is split across the
skeleton's segments (one segment for an anchor drag, two for a waypoint
drag) in proportion to each segment's own straight length -- the longer
segment gets proportionally more of the extra length to absorb. This is
a design choice, not something ``BUNDLE_PLACEMENT.md`` pins down exactly;
proportional-by-length matches the proportional-split convention the
older, simpler ``objects_pegboard.chain_edges`` budget model already
used, and keeps the two spans' shares in a sensible ratio to their own
size.

**One span's own zigzag (user spec, 2026-10-05).** Given a span's two fixed
endpoints, its straight length ``s``, the total path length ``t`` it must
reach, and the bundle diameter ``D``, :func:`_solve_span` works out the
zig-zag count in two steps:

- ``max_count = max(1, floor(s / (zigzag_length_factor * D)))`` -- the most
  zig-zags the span may hold (default factor 3: one per three diameters of
  straight length), clamped to at least 1.
- ``threshold = threshold_factor * D`` -- the height every existing zig-zag
  must reach before another one is created.

The count is ``clamp(floor(excess / (2 * threshold)), 1, max_count)`` with
``excess = sqrt(t**2 - s**2)``. A zig-zag is therefore only added once the
existing ones could all stand at least *threshold* tall. Once the count is
at ``max_count``, the amplitude keeps growing and shrinking with the slack.
When the slack drops back below a threshold the count falls by exactly one
and the slack comes out of one zig-zag at a time -- the floor makes each
change a discrete step, never a reshuffle of the whole chain.

**Closed-form bow height.** For ``count`` equal bows across the span, each
with half-base ``s / (2 * count)`` and apex height ``h``, the total zig-zag
length is ``count * 2 * sqrt((s / (2 * count)) ** 2 + h ** 2)``. Setting that
to ``t`` gives ``h = excess / (2 * count)`` exactly, independent of ``s``.
``count == 1`` reduces to :func:`geometry.line.Line.bow_midpoint`'s own
single-bow construction.
"""

import enum
import math
from typing import NamedTuple


_EPS = 1e-9

# Floor on the bundle/wire diameter fed into the zig-zag rules, so a zero or
# missing diameter can never divide by zero.
_MIN_DIAMETER_MM = 1.0


class DragEnd(enum.Enum):
    """Which point of a wire or bundle's peg-board chain a drag
    operation moves.

    ``START``/``STOP`` drag one of the chain's two real anchors (the
    other stays fixed); ``WAYPOINT`` drags an interior point (both
    anchors stay fixed).
    """
    START = 'start'
    STOP = 'stop'
    WAYPOINT = 'waypoint'


class ChainResult(NamedTuple):
    """The result of one :func:`solve_chain` call.

    :ivar accepted: ``False`` means the drag was physically impossible
        (even the bare start-to-stop skeleton already needs more than
        *required_length*) -- the caller must leave the chain exactly as
        it was before this call; :attr:`points` carries no meaning and is
        always empty in this case.
    :ivar points: The full new peg-board chain, start anchor through
        stop anchor inclusive, in order. Only meaningful when
        :attr:`accepted` is ``True``.
    """
    accepted: bool
    points: list[tuple[float, float]]


def solve_chain(
    start: tuple[float, float],
    stop: tuple[float, float],
    required_length: float,
    drag_end: DragEnd,
    target: tuple[float, float],
    diameter_mm: float,
    zigzag_length_factor: float,
    threshold_factor: float,
    tolerance: float = 1e-6,
) -> ChainResult:
    """Recompute a wire or bundle's whole peg-board chain after one
    point of it is dragged to *target*.

    :param start: The chain's current start anchor position -- ignored
        (superseded by *target*) if *drag_end* is :attr:`DragEnd.START`.
    :param stop: The chain's current stop anchor position -- ignored
        (superseded by *target*) if *drag_end* is :attr:`DragEnd.STOP`.
    :param required_length: The chain's real total length (its 3D
        ``length_mm``) that the returned chain's own polyline length must
        match exactly.
    :param drag_end: Which point is being dragged -- see :class:`DragEnd`.
    :param target: Where that point is being dragged to.
    :param diameter_mm: The bundle's (or wire's) diameter -- drives both
        the zig-zag count cap and the zig-zag threshold height.
    :param zigzag_length_factor: Diameters of straight start-to-stop length
        per allowed zig-zag (see :func:`_solve_span`).
    :param threshold_factor: Height, in diameters, every zig-zag must reach
        before another is created (see :func:`_solve_span`).
    :param tolerance: How close total length may come to *required_length*
        before a span counts as "straight" (no bow needed) and how much
        slack is treated as the geometry allows before refusing a move.
    :returns: See :class:`ChainResult`.
    """
    if drag_end is DragEnd.START:
        skeleton = [target, stop]
    elif drag_end is DragEnd.STOP:
        skeleton = [start, target]
    else:
        skeleton = [start, target, stop]

    base_length = _polyline_length(skeleton)

    if base_length > required_length + tolerance:
        return ChainResult(False, [])

    needed_slack = required_length - base_length

    diameter = max(diameter_mm, _MIN_DIAMETER_MM)

    points: list[tuple[float, float]] = [skeleton[0]]
    span_count = len(skeleton) - 1

    for i in range(span_count):
        a = skeleton[i]
        b = skeleton[i + 1]
        straight = math.hypot(b[0] - a[0], b[1] - a[1])

        if base_length < _EPS:
            share = needed_slack / span_count
        else:
            share = needed_slack * (straight / base_length)

        points.extend(_solve_span(
            a, b, straight + share, diameter, zigzag_length_factor, threshold_factor, tolerance))
        points.append(b)

    return ChainResult(True, points)


def _polyline_length(points: list[tuple[float, float]]) -> float:
    """Sum of consecutive distances along *points*."""
    total = 0.0

    for i in range(len(points) - 1):
        ax, az = points[i]
        bx, bz = points[i + 1]
        total += math.hypot(bx - ax, bz - az)

    return total


def _solve_span(
    a: tuple[float, float],
    b: tuple[float, float],
    target_length: float,
    diameter: float,
    zigzag_length_factor: float,
    threshold_factor: float,
    tolerance: float,
) -> list[tuple[float, float]]:
    """The interior zigzag waypoints (excluding *a*/*b* themselves)
    needed so the polyline ``a -> waypoints -> b`` totals exactly
    *target_length* -- see the module docstring's zig-zag section for the
    count and threshold rules.

    :returns: An empty list if *target_length* is already within
        *tolerance* of ``a``-to-``b``'s own straight distance.
    """
    ax, az = a
    bx, bz = b
    dx = bx - ax
    dz = bz - az
    straight = math.hypot(dx, dz)

    if target_length <= straight + tolerance:
        return []

    # Count cap: one zig-zag per zigzag_length_factor diameters of this
    # span's own straight length, never fewer than one.
    spacing = max(zigzag_length_factor * diameter, _EPS)
    max_count = max(1, math.floor(straight / spacing))

    # Threshold: the height every zig-zag must reach before another is
    # created. Floor of excess / (2 * threshold) means each existing bow
    # stands at least that tall, so amplitude only grows past the
    # threshold once the count is pinned at max_count.
    threshold = max(threshold_factor * diameter, _EPS)

    excess = math.sqrt(max(target_length * target_length - straight * straight, 0.0))
    count = min(max(1, math.floor(excess / (2.0 * threshold))), max_count)
    height = excess / (2.0 * count)

    if straight < _EPS:
        ux, uz = 1.0, 0.0
    else:
        ux, uz = dx / straight, dz / straight

    # perpendicular to (ux, uz) in the peg-board (x, z) plane, matching
    # geometry.line.Line.bow_midpoint's own cross(world_up, direction)
    # convention (world_up = (0, 1, 0) collapses that cross product to
    # exactly (dz, -dx) here).
    px, pz = uz, -ux

    # One waypoint per bump apex. The height-0 boundary between two
    # neighbouring bumps lies exactly on the straight line joining their
    # apexes, so it is not a bend and is not emitted -- emitting it doubled
    # the waypoint count for no change in shape.
    waypoints = []
    for i in range(count):
        t_apex = (i + 0.5) / count

        if i % 2 == 0:
            sign = 1.0
        else:
            sign = -1.0

        apex_x = ax + t_apex * dx + px * height * sign
        apex_z = az + t_apex * dz + pz * height * sign
        waypoints.append((apex_x, apex_z))

    return waypoints
