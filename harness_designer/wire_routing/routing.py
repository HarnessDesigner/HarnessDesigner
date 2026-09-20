# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Orthogonal (horizontal/vertical-only) auto-routing for the 2D
schematic editor's wires.

Single entry point: :func:`route`, given a project and a wire's two
world (x, z) endpoints, returns the minimal list of interior bend
points for a path that:

- never crosses a housing, a splice, or a note (hard obstacles), and
- never runs along the same lane as another already-connected wire's
  segment (crossing it at a right angle is fine).

Routing happens on a *compressed* grid rather than a uniform one: the
grid lines always include the two endpoints exactly (so nothing needs
snapping/stub-connecting) plus every nearby obstacle's edges, with
uniform lanes filled in between for room to jog around obstacles. The
lane pitch, and the centre-to-centre gap kept between parallel wires, is
one cavity's height (:func:`_lane_spacing`) -- the pitch terminals
already stack at -- with the lattice anchored at the start so a bundle
leaving a housing stays evenly spaced. A* (4-directional, state =
node + arrival direction, with a bend-cost penalty so straighter runs
are preferred) finds the path; consecutive non-turning nodes are then collapsed away, so a wire
that doesn't need to bend at all comes back with an empty waypoint
list.
"""

import bisect
import heapq
from typing import NamedTuple, TYPE_CHECKING

import math

import numpy as np

from .. import config as _config
from .. import bounds as _bounds
from ..geometry import cavity_layout as _cavity_layout

if TYPE_CHECKING:
    from ..objects import project as _project


try:
    from . import astar as _astar_ext
except ImportError:
    # The compiled search hasn't been built in this environment -- the pure
    # Python one (same rules, same results, much slower) takes over.
    _astar_ext = None


Config = _config.Config.editor_schematic

# Grid coordinates are rounded to 6 decimals, so scaling by 10 ** 6 makes them
# exact integers for the compiled search.
_SCALE = 1_000_000

# Extra cost added at every turn -- keeps A* from taking a longer but
# straighter path over a shorter one with more bends only when the
# difference is small; a large detour still wins on raw distance.
_BEND_COST_FACTOR = 4.0

_EPS = 1e-6

# Tolerance on the "is this lane at least one spacing away" comparison. Every
# coordinate here comes from float32 storage (noise of a few 1e-6 at the
# magnitudes involved), and terminals sit at EXACTLY one lane spacing apart, so
# a neighbour that is precisely one pitch away can measure a hair under it.
# 1e-3 mm is far above that noise and far below anything visible.
_LANE_EPS = 1e-3


def _lane_spacing() -> float:
    """Centre-to-centre distance kept between parallel wires, and the pitch
    of the routing lanes: one cavity's height.

    Terminals stack at exactly that pitch inside a housing, so using it
    for the lanes too keeps a bundle of wires evenly spaced from the
    terminals all the way along their run, instead of fanning out wider
    once past the stubs. It's font-driven (see ``cavity_layout.
    compute_stack_geometry``) and the font metrics only exist once the
    app has built its glyph atlas, so it can't be a constant -- until
    then (or if it's ever not positive) fall back to
    ``Config.layout.wire_spacing`` so the router never sees a zero pitch.
    """
    spacing = _cavity_layout.compute_stack_geometry(1).cavity_height

    if spacing > 0.0:
        return spacing

    return Config.layout.wire_spacing


def _obstacle_rects(project: "_project.Project", lo_x: float, lo_z: float,
                    hi_x: float, hi_z: float, ignore_wire=None
                    ) -> list[tuple[float, float, float, float]]:
    """Every housing's/splice's/note's world AABB
    (``(min_x, min_z, max_x, max_z)``), each padded out by half
    ``Config.layout.wire_spacing``, that overlaps the window
    ``(lo_x, lo_z)``-``(hi_x, hi_z)`` -- the hard obstacles a routed path
    may never cross.

    Read straight out of the schematic view's AABB array pool
    (``bounds_manager.editor_schematic.aabb``) rather than by walking
    ``project.housings``/``splices``/``notes`` and asking each object for
    its bounds: every such object's ``BaseSchematic`` registers its slot
    under ``bounds.TAG_OBSTACLE``, and that slot is the very memory the
    object's own position updates write into, so the rows are always
    current with nothing to rebuild. Selecting, padding and window-
    filtering are all single numpy operations over the whole array.

    A row with no real extent (an object that has no geometry yet, e.g. a
    note with no position -- its row still holds the sentinel) is skipped
    *before* padding, otherwise the padding alone would turn it into a
    phantom obstacle.

    The padding matters because ``route()``/``_astar`` only ever test a
    single centreline point/edge against these rects -- a wire is a real
    ``Config.object_sizes.wire.diameter``-wide cylinder, not an
    infinitely thin line, so a centreline running exactly along an
    obstacle's own edge would still visually overlap it. Padding the
    obstacle out first makes "centreline clear of the padded rect"
    equivalent to "the wire's own edge clear of the real rect", using
    the SAME buffer distance ``_edge_too_close_to_wire`` already
    enforces between two parallel wires -- one consistent "stay this far
    off anything" rule instead of a separate, smaller one just for
    obstacles.

    Only HALF ``wire_spacing``, not the full amount: that config value
    is a wire-to-wire centreline gap (so each wire's own side only needs
    to give up half of it), and a terminal's mandatory straight exit
    stub (see ``reroute._terminal_exit_stub_point``,
    ``Config.layout.terminal_stub_length`` -- 2mm by default) starts
    right at the housing's own edge -- padding a full 3mm out from the
    housing would put that stub's own end inside the padded (blocked)
    zone, fighting the two rules against each other. 1.5mm leaves the
    2mm stub clear.

    :param ignore_wire: Excludes any splice *ignore_wire* is directly
        attached to (``start_sibling``/``stop_sibling``) from the
        obstacle list. Unlike a housing (whose real attach point -- a
        terminal's own stub -- always sits outside the housing's body),
        a wire's own fixed end sits exactly AT its splice's centre, deep
        inside that splice's own AABB -- ``segment_blocked`` tests a
        dragged segment's *own* bounding points directly (unlike
        ``_astar``, which only ever tests a path's interior/neighboring
        nodes against these rects, never the wire's own start/goal), so
        without this exclusion, every segment next to a splice-attached
        wire would read as permanently blocked by its own splice.
    """
    margin = _lane_spacing() / 2.0

    exclude = []
    if ignore_wire is not None:
        for splice in project.splices:
            if splice in (ignore_wire.start_sibling, ignore_wire.stop_sibling):
                exclude.append(splice.objschematic._aabb_index)  # NOQA

    pool = project.mainframe.bounds_manager.editor_schematic.aabb
    rows = pool.rows_tagged(_bounds.TAG_OBSTACLE, exclude).astype(np.float64)

    # rows[:, 0] is each box's min corner, rows[:, 1] its max corner,
    # both (x, y, z) -- this view is top-down, so only x/z matter.
    min_x = rows[:, 0, 0]
    min_z = rows[:, 0, 2]
    max_x = rows[:, 1, 0]
    max_z = rows[:, 1, 2]

    keep = (max_x > min_x) & (max_z > min_z)

    min_x = min_x - margin
    min_z = min_z - margin
    max_x = max_x + margin
    max_z = max_z + margin

    keep &= ~((max_x < lo_x) | (hi_x < min_x) | (max_z < lo_z) | (hi_z < min_z))

    rects = np.stack((min_x[keep], min_z[keep], max_x[keep], max_z[keep]), axis=1)
    return [tuple(rect) for rect in rects.tolist()]


def _wire_segments(project: "_project.Project", lo_x: float, lo_z: float,
                   hi_x: float, hi_z: float, ignore_wire=None, skip_wires=frozenset()
                   ) -> np.ndarray:
    """Every connected wire's own (x, z) segment endpoints -- an ``(S, 2, 2)``
    array, ``[s, 0]`` a segment's start and ``[s, 1]`` its end -- that come
    within ``Config.layout.wire_spacing`` of the window
    ``(lo_x, lo_z)``-``(hi_x, hi_z)``, excluding *ignore_wire* (the wire
    currently being routed, if it already exists as a row, so it never
    blocks its own re-route) and every wire in *skip_wires*.

    Read from the schematic view's segment pool
    (``bounds_manager.editor_schematic.segments``, see
    :class:`~harness_designer.bounds.segment_pool.SegmentPool`) -- every
    wire keeps its path registered there, so nothing is re-queried from
    the database or rebuilt per call. Only the window's segments are
    returned: every edge :func:`_edge_too_close_to_wire` tests lies inside
    that window, so a segment further than ``wire_spacing`` from it can
    never be a match.

    An unconnected (still-being-drawn) wire is left out too -- it isn't
    really "there" yet (see ``objects.wire.Wire.is_connected``).

    :param skip_wires: Other wires to leave out of the obstacle list --
        used while routing several wires attached to the same object
        being moved together (a housing drag, see
        ``reroute.reroute_wire``'s own ``skip_wires``) for whichever of
        those siblings haven't been settled into a final path yet this
        pass: an unsettled sibling's *current* segments are stale (about
        to be recomputed anyway), so treating them as a hard obstacle
        only makes the router dodge a path that's already about to
        change -- and, worse, can make two siblings each dodge the
        other's stale position back and forth every frame instead of
        ever settling. Never affects any wire outside the batch, which
        keeps its normal current path as a real obstacle throughout.
    """
    exclude = []
    for wire in project.wires:
        if wire is ignore_wire or wire in skip_wires or not wire.is_connected:
            exclude.append(wire.objschematic)

    spacing = _lane_spacing()
    pool = project.mainframe.bounds_manager.editor_schematic.segments

    segments = pool.segments(
        exclude, (lo_x - spacing, lo_z - spacing, hi_x + spacing, hi_z + spacing))

    return segments.astype(np.float64)


def _build_axis(a: float, b: float, extra_lines: list[float], lo: float, hi: float,
                pitch: float) -> np.ndarray:
    """The grid lines along one axis, as sorted, unique integers scaled by
    ``_SCALE`` (rounded to 6 decimals, which is what makes them exact):
    *a* and *b* themselves, every value in *extra_lines* that falls within
    ``[lo, hi]``, plus lanes at every *pitch* step from *a* across that
    same range.

    The lanes are anchored at *a* -- the start, where terminals stack at
    this same pitch -- rather than at the edge of the window, so a
    wire's lanes line up with its own terminal's coordinate and with its
    neighbours'. *b* only contributes its own exact coordinate: a second
    lattice anchored there would roughly quadruple the grid for little
    visible gain (the far end's own lines are already exact).
    """
    first = math.ceil((lo - a) / pitch)
    last = math.floor((hi - a) / pitch)

    parts = [np.array((a, b)), a + np.arange(first, last + 1) * pitch]

    if extra_lines:
        lines = np.array(extra_lines)
        parts.append(lines[(lines >= lo) & (lines <= hi)])

    return np.unique(np.rint(np.concatenate(parts) * _SCALE).astype(np.int64))


def _node_blocked(x: float, z: float, rects: list[tuple[float, float, float, float]]) -> bool:
    """Whether grid point *(x, z)* falls strictly inside any obstacle
    rect -- a boundary line (used to hug alongside an obstacle) is fine.
    """
    for min_x, min_z, max_x, max_z in rects:
        if min_x + _EPS < x < max_x - _EPS and min_z + _EPS < z < max_z - _EPS:
            return True

    return False


def _edge_crosses_obstacle(x1: float, z1: float, x2: float, z2: float,
                           rects: list[tuple[float, float, float, float]]) -> bool:
    """Whether the axis-aligned edge from *(x1, z1)* to *(x2, z2)* cuts
    through any obstacle's interior.

    A true axis-*overlap* test (does the edge's span on its own axis
    overlap the rect's span at all), not containment -- an edge whose
    endpoints straddle a rect (one outside, one inside, or the edge
    passing all the way through) must still register as blocked. For an
    A*-grid edge between adjacent compressed-grid nodes this coincides
    with containment anyway (``_build_axis`` always adds every nearby
    obstacle's own edges as explicit grid lines, so such an edge can
    never straddle a rect's boundary in the first place), but
    :func:`segment_blocked` also calls this with arbitrary, non-grid-
    aligned points (live interior-segment dragging, see
    ``drag_handlers.editor_schematic.wire``) where that invariant
    doesn't hold -- containment alone let a segment slice straight
    through a housing's interior undetected there as long as it also
    extended past the housing on either side.
    """
    for min_x, min_z, max_x, max_z in rects:
        if z1 == z2:
            if (min_z + _EPS < z1 < max_z - _EPS
                    and max(x1, x2) > min_x + _EPS and min(x1, x2) < max_x - _EPS):
                return True
        else:
            if (min_x + _EPS < x1 < max_x - _EPS
                    and max(z1, z2) > min_z + _EPS and min(z1, z2) < max_z - _EPS):
                return True

    return False


def _edge_too_close_to_wire(x1: float, z1: float, x2: float, z2: float,
                            segments: list[tuple[tuple[float, float], tuple[float, float]]],
                            spacing: float) -> bool:
    """Whether the edge from *(x1, z1)* to *(x2, z2)* runs parallel to,
    and within *spacing* (``Config.layout.wire_spacing``, passed in rather
    than looked up here -- this runs per A* neighbour, and a ``Config``
    attribute read costs far more than the geometry test itself) of, an
    existing connected
    wire's own segment, over any overlapping stretch (touching at a
    single point doesn't count). A perpendicular crossing is never a
    match here (wires may freely cross at a right angle -- only running
    the same lane too closely is disallowed), since one of the two
    pairs' coordinates won't be within spacing of the other.
    """
    horizontal = abs(z1 - z2) < _EPS

    if horizontal:
        this_lo, this_hi = min(x1, x2), max(x1, x2)
        fixed = z1
    else:
        this_lo, this_hi = min(z1, z2), max(z1, z2)
        fixed = x1

    for (sx1, sz1), (sx2, sz2) in segments:
        seg_horizontal = abs(sz1 - sz2) < _EPS
        if seg_horizontal != horizontal:
            continue

        if horizontal:
            if abs(sz1 - fixed) >= spacing - _LANE_EPS:
                continue
            s_lo, s_hi = min(sx1, sx2), max(sx1, sx2)
        else:
            if abs(sx1 - fixed) >= spacing - _LANE_EPS:
                continue
            s_lo, s_hi = min(sz1, sz2), max(sz1, sz2)

        if max(this_lo, s_lo) < min(this_hi, s_hi) - _EPS:
            return True

    return False


def segment_blocked(project: "_project.Project", p1: tuple[float, float], p2: tuple[float, float],
                    ignore_wire=None) -> bool:
    """Whether a single orthogonal edge from *p1* to *p2* (both ``(x, z)``
    world points, already known to be axis-aligned) is blocked -- crosses
    a housing/splice/note, or runs closer than
    ``Config.layout.wire_spacing`` to another connected wire's own
    parallel lane over any overlapping stretch.

    The single-edge equivalent of what :func:`_astar` checks per grid
    step, exposed for a live interactive drag (see
    ``drag_handlers.editor_schematic.wire``) to test one candidate move
    against, without paying for a full A* search when the direct move is
    still legal.
    """
    x1, z1 = p1
    x2, z2 = p2

    lo_x, hi_x = min(x1, x2), max(x1, x2)
    lo_z, hi_z = min(z1, z2), max(z1, z2)

    rects = _obstacle_rects(project, lo_x, lo_z, hi_x, hi_z, ignore_wire=ignore_wire)
    segments = _wire_segments(project, lo_x, lo_z, hi_x, hi_z, ignore_wire=ignore_wire).tolist()

    if _node_blocked(x1, z1, rects) or _node_blocked(x2, z2, rects):
        return True

    if _edge_crosses_obstacle(x1, z1, x2, z2, rects):
        return True

    if _edge_too_close_to_wire(x1, z1, x2, z2, segments, _lane_spacing()):
        return True

    return False


def _direction_sign(dx: float, dz: float) -> tuple[float, float]:
    """Axis-aligned unit sign vector for *(dx, dz)* -- exactly one of the
    two components is nonzero (``dx``/``dz`` here always come from an
    orthogonal edge or an orthogonal stub), so this is just each
    component's own sign, not a true normalization.
    """
    return (0.0 if abs(dx) < _EPS else (1.0 if dx > 0.0 else -1.0),
            0.0 if abs(dz) < _EPS else (1.0 if dz > 0.0 else -1.0))


_NO_LANES = (np.empty((0, 3)), np.empty((0, 3)))


def _prepare_lanes(segments: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split the ``(S, 2, 2)`` *segments* into horizontal and vertical
    runs -- ``(H, 3)`` and ``(V, 3)`` arrays of ``lane coordinate, lo, hi``
    (``z`` for a horizontal run, ``x`` for a vertical one, ``lo``/``hi``
    its extent along the run).

    Done once per search, so nothing downstream has to re-derive a
    segment's orientation. A zero-length horizontal run can never overlap
    anything, so it's dropped here.
    """
    if segments.shape[0] == 0:
        return _NO_LANES

    x1 = segments[:, 0, 0]
    z1 = segments[:, 0, 1]
    x2 = segments[:, 1, 0]
    z2 = segments[:, 1, 1]

    horizontal = np.abs(z1 - z2) < _EPS

    h_lo = np.minimum(x1, x2)[horizontal]
    h_hi = np.maximum(x1, x2)[horizontal]
    keep = (h_hi - h_lo) > _EPS

    h_lanes = np.stack((z1[horizontal][keep], h_lo[keep], h_hi[keep]), axis=1)

    vertical = ~horizontal
    v_lanes = np.stack((x1[vertical], np.minimum(z1, z2)[vertical], np.maximum(z1, z2)[vertical]), axis=1)

    return h_lanes, v_lanes


def _build_tables(xs: list[float], zs: list[float], rects: list[tuple[float, float, float, float]],
                  lanes: tuple[np.ndarray, np.ndarray],
                  limit: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """For every node of the ``xs``/``zs`` grid, whether the step to its
    left / right / down / up neighbour is allowed -- ``(ok_left, ok_right,
    ok_down, ok_up)``, each a flat boolean array indexed ``i * len(zs) + j``
    (a step off the edge of the grid is simply ``False``).

    A step is allowed when its destination isn't inside an obstacle rect
    (:func:`_node_blocked`), the edge doesn't cut through one
    (:func:`_edge_crosses_obstacle`) and it doesn't run within *limit* of,
    and over a real stretch of, another wire's run (:func:`_lanes_hit`'s
    rule) -- the same three tests, with the same comparisons, that used
    to be a Python call per neighbour of every node the search touched;
    here each is one vectorized numpy operation per obstacle / per run,
    and the search's inner loop is just a list lookup.
    """
    nx = len(xs)
    nz = len(zs)

    x = np.array(xs, dtype=np.float64)
    z = np.array(zs, dtype=np.float64)
    x_lo = x[:-1]
    x_hi = x[1:]
    z_lo = z[:-1]
    z_hi = z[1:]

    node_bad = np.zeros((nx, nz), dtype=bool)
    h_bad = np.zeros((nx - 1, nz), dtype=bool)     # edge (i, j) -> (i + 1, j)
    v_bad = np.zeros((nx, nz - 1), dtype=bool)     # edge (i, j) -> (i, j + 1)

    for min_x, min_z, max_x, max_z in rects:
        x_in = (x > min_x + _EPS) & (x < max_x - _EPS)
        z_in = (z > min_z + _EPS) & (z < max_z - _EPS)

        node_bad |= x_in[:, None] & z_in[None, :]
        h_bad |= ((x_hi > min_x + _EPS) & (x_lo < max_x - _EPS))[:, None] & z_in[None, :]
        v_bad |= x_in[:, None] & ((z_hi > min_z + _EPS) & (z_lo < max_z - _EPS))[None, :]

    h_lanes, v_lanes = lanes

    for pos, lo, hi in h_lanes.tolist():
        j0 = bisect.bisect_right(zs, pos - limit)
        j1 = bisect.bisect_left(zs, pos + limit)
        i0 = max(bisect.bisect_right(xs, lo + _EPS) - 1, 0)
        i1 = min(bisect.bisect_left(xs, hi - _EPS), nx - 1)

        if j0 < j1 and i0 < i1:
            h_bad[i0:i1, j0:j1] = True

    for pos, lo, hi in v_lanes.tolist():
        i0 = bisect.bisect_right(xs, pos - limit)
        i1 = bisect.bisect_left(xs, pos + limit)
        j0 = max(bisect.bisect_right(zs, lo + _EPS) - 1, 0)
        j1 = min(bisect.bisect_left(zs, hi - _EPS), nz - 1)

        if i0 < i1 and j0 < j1:
            v_bad[i0:i1, j0:j1] = True

    ok_left = np.zeros((nx, nz), dtype=bool)
    ok_right = np.zeros((nx, nz), dtype=bool)
    ok_down = np.zeros((nx, nz), dtype=bool)
    ok_up = np.zeros((nx, nz), dtype=bool)

    ok_right[:-1, :] = ~h_bad & ~node_bad[1:, :]
    ok_left[1:, :] = ~h_bad & ~node_bad[:-1, :]
    ok_up[:, :-1] = ~v_bad & ~node_bad[:, 1:]
    ok_down[:, 1:] = ~v_bad & ~node_bad[:, :-1]

    return ok_left.ravel(), ok_right.ravel(), ok_down.ravel(), ok_up.ravel()


def _astar_py(xs: list[float], zs: list[float], start_ij: tuple[int, int], goal_ij: tuple[int, int],
              rects: list[tuple[float, float, float, float]],
              lanes: tuple[np.ndarray, np.ndarray],
              forbid_start_dir: tuple[float, float] | None = None,
              forbid_goal_dir: tuple[float, float] | None = None
              ) -> list[tuple[int, int]] | None:
    """The pure Python search -- used only when the compiled one
    (:mod:`.astar`) isn't available, and as the reference the compiled
    one is checked against. See :func:`_astar`.

    4-directional A* over the compressed ``xs``/``zs`` grid, from
    *start_ij* to *goal_ij*, blocked by *rects* (housings/splices/notes)
    and *lanes* (other wires' own runs, see :func:`_prepare_lanes`).
    Returns the node path (inclusive of both ends), or ``None`` if
    unreachable.

    :param forbid_start_dir: If given, the one direction (as an axis-
        aligned sign vector, see :func:`_direction_sign`) the path's very
        first step out of *start_ij* may not take -- used to forbid a
        route from immediately reversing back over a terminal's own
        mandatory exit stub (a real, already-placed physical segment
        ``reroute.reroute_wire`` glues on *before* calling this, which
        this search has no other way of knowing about -- see
        ``reroute._terminal_exit_stub_point``).
    :param forbid_goal_dir: The mirror image at the other end: the one
        direction the path's very last step INTO *goal_ij* may not take,
        forbidding the same fold-back over the stop-side exit stub.

    Beyond that stub-seam case, a path also carries its own runs so far
    along as search state and holds every candidate edge to the same lane
    rule against them -- forbidding it from heading off, doubling back,
    and turning to run too close and parallel to a stretch of itself.

    The search state is ``(node, direction of arrival)``, not just the
    node: every bend costs extra, so what it costs to continue from a
    node depends on which way the path got there, and keying the best
    cost on the node alone lets a slightly cheaper arrival in the wrong
    direction shadow the one that would have gone straight on.

    This is the hot loop of the whole router, so it is written for the
    interpreter rather than for elegance: state and costs live in flat
    lists indexed by integers; the heuristic and step lengths come from
    tables built once; and everything about a step that does NOT depend
    on the path taken to reach it (see :func:`_build_tables`) is decided
    for the whole grid up front, so the loop does one list lookup where
    it used to make three function calls.
    """
    nx = len(xs)
    nz = len(zs)

    si, sj = start_ij
    gi, gj = goal_ij
    gx = xs[gi]
    gz = zs[gj]

    limit = _lane_spacing() - _LANE_EPS
    bend_cost = _BEND_COST_FACTOR * Config.layout.routing_grid

    ok_left, ok_right, ok_down, ok_up = [t.tolist() for t in _build_tables(xs, zs, rects, lanes, limit)]

    # Neighbour order is part of the search's tie-breaking -- keep it fixed.
    # (allowed?, di, dj, direction, node offset), direction 0 = horizontal, 1 = vertical.
    moves = ((ok_left, -1, 0, 0, -nz), (ok_right, 1, 0, 0, nz),
             (ok_down, 0, -1, 1, -1), (ok_up, 0, 1, 1, 1))

    # Heuristic (Manhattan distance to the goal) and per-step lengths.
    hx = [abs(x - gx) for x in xs]
    hz = [abs(z - gz) for z in zs]
    gap_x = [xs[k + 1] - xs[k] for k in range(nx - 1)]
    gap_z = [zs[k + 1] - zs[k] for k in range(nz - 1)]

    inf = float('inf')
    heappush = heapq.heappush
    heappop = heapq.heappop
    direction_sign = _direction_sign

    # State id = node * 3 + direction of arrival (0 h, 1 v, 2 = the start).
    best = [inf] * (nx * nz * 3)
    came = [-1] * (nx * nz * 3)
    best[(si * nz + sj) * 3 + 2] = 0.0

    # (priority, cost, i, j, arrival direction, own horizontal runs, own vertical runs)
    # where a run is (lane coordinate, lo, hi), straight steps merged.
    open_heap = [(hx[si] + hz[sj], 0.0, si, sj, 2, (), ())]

    while open_heap:
        _, cost, i, j, d, own_h, own_v = heappop(open_heap)

        node = i * nz + j
        sid = node * 3 + d

        if cost > best[sid] + _EPS:
            # Stale heap entry -- a cheaper path to this state was already
            # relaxed after this one was pushed.
            continue

        if i == gi and j == gj:
            path = [(i, j)]
            while came[sid] != -1:
                sid = came[sid]
                back = sid // 3
                path.append((back // nz, back % nz))
            path.reverse()
            return path

        x1 = xs[i]
        z1 = zs[j]

        for ok_list, di, dj, nd, offset in moves:
            if not ok_list[node]:
                continue

            ni = i + di
            nj = j + dj
            x2 = xs[ni]
            z2 = zs[nj]

            # The path's own earlier runs, same lane rule.
            if nd == 0:
                if x1 < x2:
                    lo, hi = x1, x2
                else:
                    lo, hi = x2, x1

                lane = z1
                own = own_h
            else:
                if z1 < z2:
                    lo, hi = z1, z2
                else:
                    lo, hi = z2, z1

                lane = x1
                own = own_v

            if own:
                lo_e = lo + _EPS
                hi_e = hi - _EPS
                lane_lo = lane - limit
                lane_hi = lane + limit

                too_close = False
                for s_lane, s_lo, s_hi in own:
                    if lane_lo < s_lane < lane_hi and s_hi > lo_e and s_lo < hi_e:
                        too_close = True
                        break

                if too_close:
                    continue

            if d == 2:
                if forbid_start_dir is not None and direction_sign(x2 - x1, z2 - z1) == forbid_start_dir:
                    continue
            if ni == gi and nj == gj:
                if forbid_goal_dir is not None and direction_sign(x2 - x1, z2 - z1) == forbid_goal_dir:
                    continue

            if nd == 0:
                new_cost = cost + gap_x[i if di > 0 else ni]
            else:
                new_cost = cost + gap_z[j if dj > 0 else nj]

            if d != 2 and nd != d:
                new_cost += bend_cost

            nsid = (node + offset) * 3 + nd
            if new_cost < best[nsid] - _EPS:
                best[nsid] = new_cost
                came[nsid] = sid

                # A step that carries on the way the path was already
                # heading just lengthens its last run.
                if nd == 0:
                    new_v = own_v
                    if d == 0:
                        s_lane, s_lo, s_hi = own_h[-1]
                        new_h = own_h[:-1] + ((s_lane, min(s_lo, lo), max(s_hi, hi)),)
                    else:
                        new_h = own_h + ((lane, lo, hi),)
                else:
                    new_h = own_h
                    if d == 1:
                        s_lane, s_lo, s_hi = own_v[-1]
                        new_v = own_v[:-1] + ((s_lane, min(s_lo, lo), max(s_hi, hi)),)
                    else:
                        new_v = own_v + ((lane, lo, hi),)

                heappush(open_heap, (new_cost + hx[ni] + hz[nj], new_cost, ni, nj, nd, new_h, new_v))

    return None


def _direction_code(sign: tuple[float, float] | None) -> int:
    """The compiled search's code for a forbidden direction vector (see
    :func:`_direction_sign`): 0 left, 1 right, 2 down, 3 up, -1 for none."""
    if sign is None:
        return -1

    dx, dz = sign

    if dz == 0.0:
        if dx < 0.0:
            return 0
        if dx > 0.0:
            return 1
    elif dx == 0.0:
        if dz < 0.0:
            return 2
        return 3

    return -1


def _astar(xs: np.ndarray, zs: np.ndarray, start_ij: tuple[int, int], goal_ij: tuple[int, int],
           rects: list[tuple[float, float, float, float]],
           lanes: tuple[np.ndarray, np.ndarray],
           forbid_start_dir: tuple[float, float] | None = None,
           forbid_goal_dir: tuple[float, float] | None = None
           ) -> list[tuple[int, int]] | None:
    """4-directional A* over the compressed grid, from *start_ij* to
    *goal_ij* -- returns the node path (inclusive of both ends), or
    ``None`` if unreachable. See :func:`_astar_py` for the full description
    of the rules; this is the same search, run by the compiled code in
    ``astar.pyx``.

    :param xs: Grid columns, ascending, scaled by ``_SCALE`` to exact integers.
    :param zs: Grid rows, likewise.
    :param rects: Obstacle rects, in mm.
    :param lanes: Other wires' horizontal and vertical runs
        (:func:`_prepare_lanes`), in mm.

    The compiled side does all of it in integer math: which steps of the
    grid are allowed at all (``build_tables`` -- housings and other wires'
    lanes) and the search itself (everything that depends on the path
    taken: its own runs, bends, the stub directions).
    """
    if _astar_ext is None:
        return _astar_py((xs / _SCALE).tolist(), (zs / _SCALE).tolist(), start_ij, goal_ij, rects,
                         lanes, forbid_start_dir, forbid_goal_dir)

    nz = len(zs)
    limit = int(round((_lane_spacing() - _LANE_EPS) * _SCALE))
    h_lanes, v_lanes = lanes

    ok_left, ok_right, ok_down, ok_up = _astar_ext.build_tables(
        xs, zs,
        np.rint(np.array(rects, dtype=np.float64).reshape(-1, 4) * _SCALE).astype(np.int64),
        np.rint(h_lanes * _SCALE).astype(np.int64),
        np.rint(v_lanes * _SCALE).astype(np.int64),
        limit)

    path = _astar_ext.astar(
        xs, zs, start_ij[0], start_ij[1], goal_ij[0], goal_ij[1],
        ok_left, ok_right, ok_down, ok_up,
        limit, int(round(_BEND_COST_FACTOR * Config.layout.routing_grid * _SCALE)),
        _direction_code(forbid_start_dir), _direction_code(forbid_goal_dir))

    if path is None:
        return None

    return [(node // nz, node % nz) for node in path.tolist()]


def _collapse(path_xz: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Drop every node that doesn't actually turn, and drop the first/
    last (the caller's own start/stop, not interior waypoints).
    """
    if len(path_xz) <= 2:
        return []

    interior = []
    for idx in range(1, len(path_xz) - 1):
        x0, z0 = path_xz[idx - 1]
        x1, z1 = path_xz[idx]
        x2, z2 = path_xz[idx + 1]

        prev_horizontal = abs(z0 - z1) < _EPS
        next_horizontal = abs(z1 - z2) < _EPS
        if prev_horizontal != next_horizontal:
            interior.append((x1, z1))

    return interior


_MAX_WINDOW_RETRIES = 6


def _search_window(project: "_project.Project", start: tuple[float, float],
                   stop: tuple[float, float], margin: float, ignore_wire=None
                   ) -> tuple[float, float, float, float, list[tuple[float, float, float, float]]]:
    """The routing window ``(lo_x, lo_z, hi_x, hi_z)`` plus every
    obstacle rect that touches it.

    Starts as the start/stop bounding box grown by *margin*, then keeps
    growing to take in the FULL extent (plus *margin*) of every obstacle
    it overlaps, until nothing new is touched. Without that, a housing
    bigger than *margin* sitting between the two ends fills the whole
    window and A* has no lane around it at all -- and ``route`` then
    falls back to a dogleg that ignores every obstacle and every other
    wire.
    """
    lo_x, hi_x = min(start[0], stop[0]) - margin, max(start[0], stop[0]) + margin
    lo_z, hi_z = min(start[1], stop[1]) - margin, max(start[1], stop[1]) + margin

    rects = _obstacle_rects(project, lo_x, lo_z, hi_x, hi_z, ignore_wire=ignore_wire)

    # Each pass can only grow the window, and it can't grow past the
    # obstacles that exist, so this terminates; the cap is just a guard.
    for _ in range(16):
        new_lo_x, new_hi_x, new_lo_z, new_hi_z = lo_x, hi_x, lo_z, hi_z

        for r_min_x, r_min_z, r_max_x, r_max_z in rects:
            new_lo_x = min(new_lo_x, r_min_x - margin)
            new_hi_x = max(new_hi_x, r_max_x + margin)
            new_lo_z = min(new_lo_z, r_min_z - margin)
            new_hi_z = max(new_hi_z, r_max_z + margin)

        if (new_lo_x, new_hi_x, new_lo_z, new_hi_z) == (lo_x, hi_x, lo_z, hi_z):
            break

        lo_x, hi_x, lo_z, hi_z = new_lo_x, new_hi_x, new_lo_z, new_hi_z
        rects = _obstacle_rects(project, lo_x, lo_z, hi_x, hi_z, ignore_wire=ignore_wire)

    return lo_x, lo_z, hi_x, hi_z, rects


class WireEnds(NamedTuple):
    """Where one wire being routed starts and stops, all ``(x, z)`` in mm.

    ``start_stub`` / ``stop_stub`` are the mandatory straight run out of a
    terminal (``None`` for an end with no stub, e.g. a splice), and
    ``ignore_rects`` the padded footprints of the splices the wire is
    attached to -- its own fixed end sits AT a splice's centre, deep inside
    that splice's box, so those don't count as obstacles for this wire (see
    :func:`_obstacle_rects`).
    """
    start: tuple[float, float]
    stop: tuple[float, float]
    start_stub: tuple[float, float] | None
    stop_stub: tuple[float, float] | None
    ignore_rects: list[tuple[float, float, float, float]]


def attached_splice_rects(project: "_project.Project", wire) -> list[tuple[float, float, float, float]]:
    """The padded footprint of each splice *wire* is directly attached to,
    computed exactly as :func:`_obstacle_rects` computes it -- so painting
    one into a routing grid and taking it back out are exact opposites."""
    margin = _lane_spacing() / 2.0
    pool = project.mainframe.bounds_manager.editor_schematic.aabb

    rects = []
    for splice in project.splices:
        if splice not in (wire.start_sibling, wire.stop_sibling):
            continue

        row = pool.read(splice.objschematic._aabb_index).astype(np.float64)  # NOQA
        if row[1, 0] > row[0, 0] and row[1, 2] > row[0, 2]:
            rects.append((row[0, 0] - margin, row[0, 2] - margin, row[1, 0] + margin, row[1, 2] + margin))

    return rects


def _scaled(values: np.ndarray) -> np.ndarray:
    return np.rint(values * _SCALE).astype(np.int64)


def _frame_axis(exact: list[float], anchor: float, lo: float, hi: float, pitch: float) -> np.ndarray:
    """One axis of a :class:`RoutingFrame` grid, as sorted unique scaled
    integers: every value in *exact* (obstacle edges, wire ends and stubs --
    all of which must be grid lines), plus lanes every *pitch* from *anchor*
    across ``[lo, hi]``.

    A lane that falls within tolerance of an exact line is dropped in
    favour of it. Terminals stack at exactly one lane pitch, so their own
    coordinates would otherwise sit a few micrometres of float32 noise
    away from the lane lines and double up every line in the region for
    nothing.
    """
    exact_i = np.unique(_scaled(np.array(exact)))

    first = math.ceil((lo - anchor) / pitch)
    last = math.floor((hi - anchor) / pitch)
    lattice = _scaled(anchor + np.arange(first, last + 1) * pitch)

    tol = int(round(_LANE_EPS * _SCALE))
    at = np.searchsorted(exact_i, lattice)
    left = exact_i[np.clip(at - 1, 0, len(exact_i) - 1)]
    right = exact_i[np.clip(at, 0, len(exact_i) - 1)]
    near = (np.abs(lattice - left) <= tol) | (np.abs(lattice - right) <= tol)

    return np.unique(np.concatenate((exact_i, lattice[~near])))


class RoutingFrame:
    """A routing grid built ONCE for a whole batch of wires -- the wires
    attached to an object being dragged, all rerouted every frame -- instead
    of once per wire.

    :func:`route` builds a grid from scratch for every call: the axes, which
    housings and other wires are in the way, which steps of the grid that
    blocks. For a housing with a hundred wires on it that is a hundred
    near-identical grids per frame. Here the grid spans the whole scene, the
    housings and every wire NOT in the batch are painted into it once
    (:class:`astar.Router` keeps availability as counts, so painting is
    reversible), and routing the batch is just, for each wire in turn: take
    back the stubs it had reserved, search, and paint the path it settled on
    so the wires after it route around it.

    The batch works the way the drag handler always has: every wire in it
    starts out *unsettled*, represented only by the fixed exit stubs of its
    terminals (mandatory geometry that will exist whatever route it ends up
    with), and is replaced by its full path once routed.

    Only available when the compiled search is (see :func:`build_frame`).
    """

    def __init__(self, project: "_project.Project", batch: dict, pack_with=()):
        """
        :param batch: ``{wire: WireEnds}`` for every wire that will be routed
            through this frame.
        :param pack_with: Wires OUTSIDE the batch that share a housing with it
            (the ones that just followed a moved housing, say). Together with
            each batch wire as it settles, their runs are what a wire being
            routed prefers to run right alongside -- see
            :meth:`astar.Router.paint_pack`.
        """
        pitch = _lane_spacing()

        self._ends = batch
        self.relaxed = []
        self._bend = int(round(_BEND_COST_FACTOR * Config.layout.routing_grid * _SCALE))
        self._limit = int(round((pitch - _LANE_EPS) * _SCALE))

        rects = _obstacle_rects(project, -math.inf, -math.inf, math.inf, math.inf)

        x_exact = []
        z_exact = []
        for x1, z1, x2, z2 in rects:
            x_exact.extend((x1, x2))
            z_exact.extend((z1, z2))

        for ends in batch.values():
            for point in (ends.start, ends.stop, ends.start_stub, ends.stop_stub):
                if point is not None:
                    x_exact.append(point[0])
                    z_exact.append(point[1])

        # Room around the outside for a whole bundle to run side by side.
        margin = Config.layout.housing_spacing + (len(batch) + 2) * pitch
        anchor = next(iter(batch.values())).start

        self._xs = _frame_axis(x_exact, anchor[0], min(x_exact) - margin, max(x_exact) + margin, pitch)
        self._zs = _frame_axis(z_exact, anchor[1], min(z_exact) - margin, max(z_exact) + margin, pitch)

        self._router = _astar_ext.Router(self._xs, self._zs, self._limit)
        self._router.paint_rects(_scaled(np.array(rects, dtype=np.float64).reshape(-1, 4)), 1)

        # Every connected wire outside the batch, as it stands.
        self._paint(_static_segments(project, batch), 1)

        # Siblings to pack against: the static ones that share a housing with
        # the batch (they are painted as lanes above; this only makes running
        # beside them cheaper).
        pack = _wire_segments_of(project, pack_with)
        if pack.shape[0]:
            self._pack(pack, 1)

        # The batch, unsettled: just the stubs its terminals are known to have.
        self._stubs = {}
        for wire, ends in batch.items():
            stubs = []
            if ends.start_stub is not None:
                stubs.append((ends.start, ends.start_stub))
            if ends.stop_stub is not None:
                stubs.append((ends.stop, ends.stop_stub))

            self._stubs[wire] = np.array(stubs, dtype=np.float64).reshape(-1, 2, 2)
            self._paint(self._stubs[wire], 1)

    def __contains__(self, wire) -> bool:
        return wire in self._ends

    def _paint(self, segments: np.ndarray, delta: int) -> None:
        h_lanes, v_lanes = _prepare_lanes(segments)
        self._router.paint_lanes(_scaled(h_lanes), _scaled(v_lanes), delta)

    def _pack(self, segments: np.ndarray, delta: int) -> None:
        h_lanes, v_lanes = _prepare_lanes(segments)
        self._router.paint_pack(_scaled(h_lanes), _scaled(v_lanes), delta)

    def _node(self, point: tuple[float, float]) -> tuple[int, int]:
        x = round(point[0] * _SCALE)
        z = round(point[1] * _SCALE)

        i = int(np.searchsorted(self._xs, x))
        j = int(np.searchsorted(self._zs, z))

        # Every end and stub was made a grid line on purpose; if one is missing
        # something is badly wrong, and routing from the wrong node would be worse.
        if self._xs[i] != x or self._zs[j] != z:
            raise ValueError(f'{point} is not a grid line of this routing frame')

        return i, j

    def route(self, wire) -> list[tuple[float, float]]:
        """Route *wire* (one of the batch) and settle it into the grid.
        Returns what :func:`route` does -- the interior ``(x, z)`` bend points
        between its two stub-side ends."""
        ends = self._ends[wire]
        router = self._router

        start = ends.start if ends.start_stub is None else ends.start_stub
        stop = ends.stop if ends.stop_stub is None else ends.stop_stub

        # The splices it's attached to don't block it. Its OWN stubs stay in the
        # grid on purpose: they're part of its path, and a run alongside one
        # (say, overshooting a stub end and doubling back over it) is exactly as
        # illegal as a run alongside another wire. The start and goal nodes ARE
        # the stub ends, so nothing legitimate is shut out.
        ignore = _scaled(np.array(ends.ignore_rects, dtype=np.float64).reshape(-1, 4))
        router.paint_rects(ignore, -1)

        forbid_start = -1
        if ends.start_stub is not None:
            forbid_start = _direction_code(_direction_sign(ends.start[0] - start[0], ends.start[1] - start[1]))

        forbid_goal = -1
        if ends.stop_stub is not None:
            forbid_goal = _direction_code(_direction_sign(stop[0] - ends.stop[0], stop[1] - ends.stop[1]))

        si, sj = self._node(start)
        gi, gj = self._node(stop)

        path = router.search(si, sj, gi, gj, self._bend, forbid_start, forbid_goal, True)

        if path is None:
            # Boxed in by other wires' lanes -- still avoid every housing, splice
            # and note (run close to a wire rather than through a housing).
            path = router.search(si, sj, gi, gj, self._bend, forbid_start, forbid_goal, False)

            self.relaxed.append(wire)

            # if path is not None:
                # print('ROUTE RELAXED (ignored wire lanes, housings still avoided)',  # DEBUG (temporary)
                      # f'start={start} stop={stop}')

        router.paint_rects(ignore, 1)

        if path is None:
            # DEBUG (temporary)
            # print(f'ROUTE FALLBACK (dogleg) start={start} stop={stop} grid={len(self._xs)}x{len(self._zs)}')

            interior = [(stop[0], start[1])]
        else:
            nz = len(self._zs)
            xs_mm = (self._xs / _SCALE).tolist()
            zs_mm = (self._zs / _SCALE).tolist()
            interior = _collapse([(xs_mm[n // nz], zs_mm[n % nz]) for n in path.tolist()])

        # Settled: its real path replaces the stubs, for the wires still to route.
        full = [ends.start]
        if ends.start_stub is not None:
            full.append(ends.start_stub)
        full.extend(interior)
        if ends.stop_stub is not None:
            full.append(ends.stop_stub)
        full.append(ends.stop)

        settled = np.array(list(zip(full, full[1:])), dtype=np.float64).reshape(-1, 2, 2)
        self._paint(settled, 1)

        # ... and a sibling for the wires after it to run alongside.
        self._pack(settled, 1)

        return interior


def _wire_segments_of(project: "_project.Project", wires) -> np.ndarray:
    """The ``(S, 2, 2)`` segments of just *wires* (connected ones), from the pool."""
    wanted = {wire for wire in wires if wire.is_connected}
    if not wanted:
        return np.empty((0, 2, 2), dtype=np.float64)

    skip = [wire.objschematic for wire in project.wires if wire not in wanted]

    pool = project.mainframe.bounds_manager.editor_schematic.segments
    return pool.segments(skip).astype(np.float64)


def _static_segments(project: "_project.Project", batch) -> np.ndarray:
    """Every connected wire's ``(S, 2, 2)`` segments except those of *batch*
    (a container of wires) -- the lanes that stay put while the batch is
    being routed or shifted. An unconnected wire isn't really "there" yet."""
    skip = []
    for wire in project.wires:
        if wire in batch or not wire.is_connected:
            skip.append(wire.objschematic)

    pool = project.mainframe.bounds_manager.editor_schematic.segments
    return pool.segments(skip).astype(np.float64)


def _runs(segments: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """``(S, 2, 2)`` segments as parallel arrays ``horizontal?, lane
    coordinate, lo, hi`` (lane = ``z`` for a horizontal run, ``x`` for a
    vertical one)."""
    x1 = segments[:, 0, 0]
    z1 = segments[:, 0, 1]
    x2 = segments[:, 1, 0]
    z2 = segments[:, 1, 1]

    horizontal = np.abs(z1 - z2) < _EPS

    lane = np.where(horizontal, z1, x1)
    lo = np.where(horizontal, np.minimum(x1, x2), np.minimum(z1, z2))
    hi = np.where(horizontal, np.maximum(x1, x2), np.maximum(z1, z2))

    return horizontal, lane, lo, hi


def _runs_hit_rects(runs, rects: np.ndarray) -> bool:
    """Whether any of *runs* cuts through the interior of any of *rects* --
    the :func:`_edge_crosses_obstacle` test, vectorized over both."""
    horizontal, lane, lo, hi = runs

    if rects.shape[0] == 0 or lane.shape[0] == 0:
        return False

    min_x, min_z, max_x, max_z = (rects[:, k][None, :] for k in range(4))
    lane = lane[:, None]
    lo = lo[:, None]
    hi = hi[:, None]
    horizontal = horizontal[:, None]

    across_h = (min_z + _EPS < lane) & (lane < max_z - _EPS) & (hi > min_x + _EPS) & (lo < max_x - _EPS)
    across_v = (min_x + _EPS < lane) & (lane < max_x - _EPS) & (hi > min_z + _EPS) & (lo < max_z - _EPS)

    return bool(np.where(horizontal, across_h, across_v).any())


def _runs_hit_runs(runs, other, other_owner: np.ndarray, owner: int, limit: float) -> bool:
    """Whether any of *runs* runs within *limit* of, and over a real stretch
    of, any run in *other* that isn't owned by *owner* -- the lane rule of
    :func:`_edge_too_close_to_wire`, vectorized over both."""
    horizontal, lane, lo, hi = runs
    o_horizontal, o_lane, o_lo, o_hi = other

    if o_lane.shape[0] == 0 or lane.shape[0] == 0:
        return False

    hit = ((horizontal[:, None] == o_horizontal[None, :])
           & (np.abs(lane[:, None] - o_lane[None, :]) < limit)
           & (hi[:, None] > o_lo[None, :] + _EPS) & (lo[:, None] < o_hi[None, :] - _EPS)
           & (other_owner[None, :] != owner))

    return bool(hit.any())


def _path_folds(runs, limit: float) -> bool:
    """Whether a path's runs come back to run too close and parallel to an
    earlier stretch of the SAME path -- the rule :func:`_astar` holds every
    route to, applied to a path that was reshaped instead of searched. A
    jog that has shrunk to nothing is the classic case: the runs on either
    side of it end up a hair apart. (Neighbouring runs are perpendicular,
    so only runs at least two apart can conflict.)"""
    horizontal, lane, lo, hi = runs
    n = lane.shape[0]

    if n < 3:
        return False

    hit = ((horizontal[:, None] == horizontal[None, :])
           & (np.abs(lane[:, None] - lane[None, :]) < limit)
           & (hi[:, None] > lo[None, :] + _EPS) & (lo[:, None] < hi[None, :] - _EPS)
           & np.triu(np.ones((n, n), dtype=bool), 2))

    return bool(hit.any())


class ShiftJob(NamedTuple):
    """One wire whose end sits on an object that just moved -- see
    :func:`plan_shift`. ``path`` is the wire's polyline with the MOVING end
    FIRST, exactly as it stands now: that end already at its new place,
    every other point still where it was. ``axis`` / ``sign`` give the
    direction of the terminal's exit stub (0 = along x, 1 = along z)."""
    wire: object
    path: list[tuple[float, float]]
    axis: int
    sign: int
    stub_length: float


def _shift_candidates(job: ShiftJob, delta: tuple[float, float]) -> list[list[tuple[int, tuple[float, float]]]]:
    """The ways *job*'s path can follow its moved end without a new route,
    each a list of ``(index into job.path, new point)`` -- the cheapest
    first; empty if the path can't follow at all.

    The path leaves the terminal along its stub and turns at some first
    waypoint ``W1`` (``path[1]``), then runs to ``W2``. Movement across the
    stub drags ``W1`` along sideways; movement along it only lengthens or
    shortens the first run -- which has to stay at least a stub long.

    While there is slack in the first run:

    1. Slide ``W1`` sideways with the terminal -- ``W2`` and everything
       beyond stays put; only the run ``W1 -> W2`` changes length.
    2. Shift the jog rigidly: ``W1``, ``W2`` and ``W3`` all move sideways
       together, keeping the shape the router laid out (and the bundle's
       even spacing); only the run ``W3 -> W4`` changes length.

    Once the terminal has caught up with the turn (no slack left -- typically
    a wire that turns right at its stub end):

    3. Carry the first vertical run forward with the terminal: ``W1`` and
       ``W2`` both move along the stub direction by the same amount, so the
       first run keeps its length; only the run ``W2 -> W3`` changes.
    """
    path = job.path
    if len(path) < 3:
        return []

    u = job.axis
    p = 1 - u
    tol = 1e-3

    terminal = path[0]
    first = path[1]
    second = path[2]
    old_terminal = (terminal[0] - delta[0], terminal[1] - delta[1])

    # Is this the shape we expect: out along the stub, then turn?
    if abs(first[p] - old_terminal[p]) > tol or abs(first[u] - second[u]) > tol:
        return []

    shift = terminal[p] - old_terminal[p]
    advance = terminal[u] - old_terminal[u]

    if abs(shift) < 1e-9 and abs(advance) < 1e-9:
        return [[]]

    def moved(point, amount, axis):
        new = list(point)
        new[axis] = point[axis] + amount
        return (new[0], new[1])

    def keeps_direction(before, after, target, axis):
        # Still runs the same way to *target*, and by more than nothing.
        old = target[axis] - before[axis]
        new = target[axis] - after[axis]
        return abs(new) > tol and (old > 0) == (new > 0)

    candidates = []

    if (first[u] - terminal[u]) * job.sign >= job.stub_length - 1e-4:
        first_new = moved(first, shift, p)

        if abs(shift) < 1e-9:
            candidates.append([])
        elif keeps_direction(first, first_new, second, p):
            candidates.append([(1, first_new)])

        if (abs(shift) >= 1e-9 and len(path) >= 5
                and abs(second[p] - path[3][p]) <= tol and abs(path[3][u] - path[4][u]) <= tol):
            third = path[3]
            second_new = moved(second, shift, p)
            third_new = moved(third, shift, p)

            if keeps_direction(third, third_new, path[4], p):
                candidates.append([(1, first_new), (2, second_new), (3, third_new)])

    elif len(path) >= 4 and abs(second[p] - path[3][p]) <= tol:
        # Out of slack: carry the first vertical run along with the terminal.
        third = path[3]
        first_new = moved(moved(first, advance, u), shift, p)
        second_new = moved(second, advance, u)

        if keeps_direction(second, second_new, third, u):
            candidates.append([(1, first_new), (2, second_new)])

    return candidates


def plan_shift(project: "_project.Project", jobs: list[ShiftJob], delta: tuple[float, float]
               ) -> dict:
    """Let wires FOLLOW an object that just moved by *delta* without a new
    route, wherever that stays legal -- ``{wire: updates}`` where
    *updates* is a list of ``(index into that job's path, new point)`` to
    apply, or ``None`` for a wire that has to be routed properly instead
    (its path can't follow, or following would run through a housing or too
    close to another wire).

    A route is worth keeping until it collides: nothing here searches. Each
    wire's candidates (see :func:`_shift_candidates`) are checked against
    every housing (the WHOLE path -- the moved object itself may now be in
    the way of a run that used to be clear) and, for the parts that
    actually changed, against every other wire's lanes. Wires are taken in
    order and a wire not yet placed counts only as its fixed exit stub and
    the part of its path no candidate touches, the way the drag handler's
    unsettled wires always have; each placed wire then counts as its new
    path for the wires after it.
    """
    limit = _lane_spacing() - _LANE_EPS
    rects = np.array(_obstacle_rects(project, -math.inf, -math.inf, math.inf, math.inf),
                     dtype=np.float64).reshape(-1, 4)

    batch = {job.wire for job in jobs}
    static = _static_segments(project, batch)

    segments = [static]
    owners = [np.full(static.shape[0], -1)]

    def add(owner, points):
        if len(points) >= 2:
            segments.append(np.array(list(zip(points, points[1:])), dtype=np.float64).reshape(-1, 2, 2))
            owners.append(np.full(len(points) - 1, owner))

    # Everyone starts out unplaced: just the stub, and the far part of the path.
    for index, job in enumerate(jobs):
        end = list(job.path[0])
        end[job.axis] += job.sign * job.stub_length
        add(index, [job.path[0], (end[0], end[1])])
        add(index, job.path[4:])

    result = {}
    for index, job in enumerate(jobs):
        result[job.wire] = None

        all_segments = np.concatenate(segments)
        other = _runs(all_segments)
        other_owner = np.concatenate(owners)

        for updates in _shift_candidates(job, delta):
            path = list(job.path)
            for at, point in updates:
                path[at] = point

            changed = np.array(list(zip(path, path[1:])), dtype=np.float64).reshape(-1, 2, 2)
            if changed.shape[0] == 0:
                continue

            runs = _runs(changed)
            if _runs_hit_rects(runs, rects) or _path_folds(runs, limit):
                continue

            # The WHOLE path against everyone else's lanes, not just the part that
            # moved: a wire placed later may still be sitting where this wire's
            # moved front now lands, and this is the only moment the pair is checked.
            if _runs_hit_runs(runs, other, other_owner, index, limit):
                continue

            result[job.wire] = updates
            add(index, path)
            break

    return result


def build_frame(project: "_project.Project", batch: dict, pack_with=()) -> "RoutingFrame | None":
    """A :class:`RoutingFrame` for *batch* (``{wire: WireEnds}``), or
    ``None`` when there's nothing to route or the compiled search isn't
    built here -- callers then route wire by wire with :func:`route`."""
    if not batch or _astar_ext is None:
        return None

    return RoutingFrame(project, batch, pack_with)


def route(project: "_project.Project", start: tuple[float, float], stop: tuple[float, float],
         ignore_wire=None, skip_wires=frozenset(),
         start_anchor: tuple[float, float] | None = None,
         stop_anchor: tuple[float, float] | None = None,
         extra_segments: list[tuple[tuple[float, float], tuple[float, float]]] | None = None
         ) -> list[tuple[float, float]]:
    """Return the minimal list of interior ``(x, z)`` bend points for an
    orthogonal path from *start* to *stop* that avoids every housing,
    splice, and note, doesn't run along another connected wire's own
    lane (crossing one is fine), and never doubles back to run too close
    and parallel to a stretch of its own path either (see :func:`_astar`).
    Empty list if the two points are already reachable by a straight
    horizontal/vertical run.

    :param ignore_wire: The wire being (re-)routed, if it already exists
        as a row -- excluded from the "don't run along another wire"
        check so it never blocks its own path, and from the obstacle
        list for any splice it's directly attached to (see
        :func:`_obstacle_rects`).
    :param skip_wires: See :func:`_wire_segments`.
    :param start_anchor: If *start* is itself a terminal exit stub (not
        the wire's true endpoint), the true endpoint behind it -- the
        returned path's first step is forbidden from heading back
        toward it, so it can never fold back over that already-placed
        stub segment. ``None`` (the default) applies no such
        constraint, for a *start* with no stub (e.g. splice-attached).
    :param stop_anchor: The mirror image of *start_anchor* for *stop*.
    :param extra_segments: Additional ``((x1, z1), (x2, z2))`` lanes to
        treat like any other wire's segment -- used for the fixed exit
        stubs of the *skip_wires* siblings (see ``reroute.reroute_wire``):
        a sibling's final path is ignored while it's unsettled, but the
        short straight run out of its terminal is mandatory geometry that
        will be there regardless, so this route must not squat on it.
    """
    pitch = _lane_spacing()
    margin = Config.layout.housing_spacing

    # start_anchor sits BEHIND start (the already-placed stub segment runs
    # anchor -> start) -- forbid the interior's first step from heading
    # back toward it, i.e. the exact reverse of that stub's own direction.
    forbid_start_dir = (None if start_anchor is None
                        else _direction_sign(start_anchor[0] - start[0], start_anchor[1] - start[1]))

    # stop_anchor sits AHEAD of stop (the already-placed stub segment
    # continues stop -> anchor) -- forbid the interior's LAST step (its
    # arrival direction at stop) from being the exact reverse of that
    # same stub direction, i.e. from arriving already headed away from
    # the anchor (mirror image of the start case above, opposite sign).
    forbid_goal_dir = (None if stop_anchor is None
                       else _direction_sign(stop[0] - stop_anchor[0], stop[1] - stop_anchor[1]))

    path = None
    for _ in range(_MAX_WINDOW_RETRIES):
        lo_x, lo_z, hi_x, hi_z, rects = _search_window(
            project, start, stop, margin, ignore_wire)

        segments = _wire_segments(project, lo_x, lo_z, hi_x, hi_z,
                                  ignore_wire=ignore_wire, skip_wires=skip_wires)

        if extra_segments:
            segments = np.concatenate((segments, np.array(extra_segments, dtype=np.float64).reshape(-1, 2, 2)))

        x_lines = [v for r in rects for v in (r[0], r[2])]
        z_lines = [v for r in rects for v in (r[1], r[3])]

        # The window can be wider than start/stop's own bbox (it grows to
        # take in every obstacle it touches, see _search_window), so the
        # axes cover all of it -- otherwise A* couldn't reach the lanes
        # that go around them.
        xs = _build_axis(start[0], stop[0], x_lines, lo_x, hi_x, pitch)
        zs = _build_axis(start[1], stop[1], z_lines, lo_z, hi_z, pitch)

        start_ij = (int(np.searchsorted(xs, round(start[0] * _SCALE))),
                    int(np.searchsorted(zs, round(start[1] * _SCALE))))
        goal_ij = (int(np.searchsorted(xs, round(stop[0] * _SCALE))),
                   int(np.searchsorted(zs, round(stop[1] * _SCALE))))

        path = _astar(xs, zs, start_ij, goal_ij, rects, _prepare_lanes(segments),
                      forbid_start_dir, forbid_goal_dir)
        if path is not None:
            break

        # Boxed in at this width -- try again with a wider berth.
        margin *= 2.0

    if path is None:
        # Boxed in by other wires' lanes -- still avoid every housing, splice
        # and note (run close to a wire rather than through a housing).
        # xs/zs/start_ij/goal_ij are from the last, widest attempt above.
        path = _astar(xs, zs, start_ij, goal_ij, rects, _NO_LANES, forbid_start_dir, forbid_goal_dir)

        # if path is not None:
            # print('ROUTE RELAXED (ignored wire lanes, housings still avoided)',  # DEBUG (temporary)
                  # f'start={start} stop={stop}')

    if path is None:
        # DEBUG (temporary): A* found nothing even after widening -- dump
        # everything it was given so the failure can be reproduced.
        # print(f'ROUTE FALLBACK (dogleg) start={start} stop={stop} '
              # f'start_anchor={start_anchor} stop_anchor={stop_anchor} '
              # f'forbid_start_dir={forbid_start_dir} forbid_goal_dir={forbid_goal_dir}')
        # print(f'    window=({lo_x:.3f}, {lo_z:.3f}, {hi_x:.3f}, {hi_z:.3f}) margin={margin}')
        # print(f'    start_blocked={_node_blocked(start[0], start[1], rects)} '
              # f'stop_blocked={_node_blocked(stop[0], stop[1], rects)}')
        # for rect in rects:
            # print(f'    rect {tuple(round(v, 3) for v in rect)}')
        # for seg in segments:
            # print(f'    seg {seg}')

        # No orthogonal route avoiding every obstacle exists at this
        # resolution/margin -- fall back to a direct single dogleg
        # (matches _build_axis always including both endpoints, so this
        # can only happen with obstacles genuinely boxing the endpoint
        # in) rather than leaving the wire with no path at all.
        return [(stop[0], start[1])]

    xs_mm = (xs / _SCALE).tolist()
    zs_mm = (zs / _SCALE).tolist()

    return _collapse([(xs_mm[i], zs_mm[j]) for i, j in path])
