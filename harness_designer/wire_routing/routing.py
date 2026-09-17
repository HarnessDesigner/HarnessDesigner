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
uniform ``Config.editor_schematic.layout.routing_grid``-spaced lines
filled in between for room to jog around obstacles. A* (4-directional,
with a bend-cost penalty so straighter runs are preferred) finds the
path; consecutive non-turning nodes are then collapsed away, so a wire
that doesn't need to bend at all comes back with an empty waypoint
list.
"""

import heapq
from typing import TYPE_CHECKING

from .. import config as _config
from .. import check_types as _check_types

if TYPE_CHECKING:
    from ..objects import project as _project


Config = _config.Config.editor_schematic

# Extra cost added at every turn -- keeps A* from taking a longer but
# straighter path over a shorter one with more bends only when the
# difference is small; a large detour still wins on raw distance.
_BEND_COST_FACTOR = 4.0

_EPS = 1e-6


@_check_types.do
def _pad_rect(rect: tuple[float, float, float, float], margin: float
             ) -> tuple[float, float, float, float]:
    """Grow *rect* by *margin* on every side."""
    min_x, min_z, max_x, max_z = rect
    return min_x - margin, min_z - margin, max_x + margin, max_z + margin


@_check_types.do
def _obstacle_rects(project: "_project.Project", ignore_wire=None
                    ) -> list[tuple[float, float, float, float]]:
    """Every housing's/splice's/note's world AABB
    (``(min_x, min_z, max_x, max_z)``), each padded out by half
    ``Config.layout.wire_spacing`` -- the hard obstacles a routed path
    may never cross. A splice's (small, circular) footprint and a
    note's (text-label) footprint are both real ``BaseSchematic``-backed
    objects with their own AABB, exactly like a housing's -- same
    ``get_bounds()`` call, nothing splice/note-specific needed here.

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
    margin = Config.layout.wire_spacing / 2.0

    rects = []
    for housing in project.housings:
        bounds = housing.objschematic.get_bounds()
        if bounds is not None:
            rects.append(_pad_rect(bounds, margin))

    for splice in project.splices:
        if ignore_wire is not None and splice in (ignore_wire.start_sibling, ignore_wire.stop_sibling):
            continue
        bounds = splice.objschematic.get_bounds()
        if bounds is not None:
            rects.append(_pad_rect(bounds, margin))

    for note in project.notes:
        bounds = note.objschematic.get_bounds()
        if bounds is not None:
            rects.append(_pad_rect(bounds, margin))

    return rects


@_check_types.do
def _wire_segments(project: "_project.Project", ignore_wire=None, skip_wires=frozenset()
                   ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Every connected wire's own (x, z) segment endpoints -- see
    ``objects_schematic/wire.py``'s ``Wire._segments()`` -- excluding
    *ignore_wire* (the wire currently being routed, if it already
    exists as a row, so it never blocks its own re-route) and every wire
    in *skip_wires*.

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
    segments = []
    for wire in project.wires:
        if wire is ignore_wire or wire in skip_wires or not wire.is_connected:
            continue

        for p1, p2 in wire.objschematic._segments():  # NOQA
            segments.append(((float(p1[0]), float(p1[2])), (float(p2[0]), float(p2[2]))))

    return segments


@_check_types.do
def _build_axis(a: float, b: float, extra_lines: list[float], margin: float,
                pitch: float) -> list[float]:
    """Sorted, deduplicated coordinates along one axis: *a* and *b*
    exactly, every value in *extra_lines* that falls within
    ``[min(a, b) - margin, max(a, b) + margin]``, plus uniform *pitch*
    samples across that same range for routing flexibility.
    """
    lo = min(a, b) - margin
    hi = max(a, b) + margin

    coords = {round(a, 6), round(b, 6)}
    for v in extra_lines:
        if lo <= v <= hi:
            coords.add(round(v, 6))

    steps = max(1, int((hi - lo) / pitch))
    for i in range(steps + 1):
        coords.add(round(lo + i * pitch, 6))

    return sorted(coords)


@_check_types.do
def _node_blocked(x: float, z: float, rects: list[tuple[float, float, float, float]]) -> bool:
    """Whether grid point *(x, z)* falls strictly inside any obstacle
    rect -- a boundary line (used to hug alongside an obstacle) is fine.
    """
    for min_x, min_z, max_x, max_z in rects:
        if min_x + _EPS < x < max_x - _EPS and min_z + _EPS < z < max_z - _EPS:
            return True

    return False


@_check_types.do
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


@_check_types.do
def _edge_too_close_to_wire(x1: float, z1: float, x2: float, z2: float,
                            segments: list[tuple[tuple[float, float], tuple[float, float]]]) -> bool:
    """Whether the edge from *(x1, z1)* to *(x2, z2)* runs parallel to,
    and within ``Config.layout.wire_spacing`` of, an existing connected
    wire's own segment, over any overlapping stretch (touching at a
    single point doesn't count). A perpendicular crossing is never a
    match here (wires may freely cross at a right angle -- only running
    the same lane too closely is disallowed), since one of the two
    pairs' coordinates won't be within spacing of the other.
    """
    horizontal = abs(z1 - z2) < _EPS
    spacing = Config.layout.wire_spacing

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
            if abs(sz1 - fixed) >= spacing - _EPS:
                continue
            s_lo, s_hi = min(sx1, sx2), max(sx1, sx2)
        else:
            if abs(sx1 - fixed) >= spacing - _EPS:
                continue
            s_lo, s_hi = min(sz1, sz2), max(sz1, sz2)

        if max(this_lo, s_lo) < min(this_hi, s_hi) - _EPS:
            return True

    return False


@_check_types.do
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
    rects = _obstacle_rects(project, ignore_wire=ignore_wire)
    segments = _wire_segments(project, ignore_wire=ignore_wire)

    x1, z1 = p1
    x2, z2 = p2

    if _node_blocked(x1, z1, rects) or _node_blocked(x2, z2, rects):
        return True

    if _edge_crosses_obstacle(x1, z1, x2, z2, rects):
        return True

    if _edge_too_close_to_wire(x1, z1, x2, z2, segments):
        return True

    return False


@_check_types.do
def _neighbors(i: int, j: int, xs: list[float], zs: list[float]):
    if i > 0:
        yield i - 1, j
    if i < len(xs) - 1:
        yield i + 1, j
    if j > 0:
        yield i, j - 1
    if j < len(zs) - 1:
        yield i, j + 1


@_check_types.do
def _direction_sign(dx: float, dz: float) -> tuple[float, float]:
    """Axis-aligned unit sign vector for *(dx, dz)* -- exactly one of the
    two components is nonzero (``dx``/``dz`` here always come from an
    orthogonal edge or an orthogonal stub), so this is just each
    component's own sign, not a true normalization.
    """
    return (0.0 if abs(dx) < _EPS else (1.0 if dx > 0.0 else -1.0),
            0.0 if abs(dz) < _EPS else (1.0 if dz > 0.0 else -1.0))


@_check_types.do
def _astar(xs: list[float], zs: list[float], start_ij: tuple[int, int], goal_ij: tuple[int, int],
          rects: list[tuple[float, float, float, float]],
          segments: list[tuple[tuple[float, float], tuple[float, float]]],
          forbid_start_dir: tuple[float, float] | None = None,
          forbid_goal_dir: tuple[float, float] | None = None
          ) -> list[tuple[int, int]] | None:
    """4-directional A* over the compressed ``xs``/``zs`` grid, from
    *start_ij* to *goal_ij*, blocked by *rects* (housings/splices/notes)
    and *segments* (other wires' own lanes). Returns the node path
    (inclusive of both ends), or ``None`` if unreachable.

    :param forbid_start_dir: If given, the one direction (as an axis-
        aligned sign vector, see :func:`_direction_sign`) the path's very
        first step out of *start_ij* may not take -- used to forbid a
        route from immediately reversing back over a terminal's own
        mandatory exit stub (a real, already-placed physical segment
        ``reroute.reroute_wire`` glues on *before* calling this, which
        this search has no other way of knowing about -- see
        ``reroute._terminal_exit_stub_point``). *start_ij* is only ever
        expanded once (its own cost is fixed at 0, never improved), so
        this only needs to apply to that single expansion.
    :param forbid_goal_dir: The mirror image at the other end: the one
        direction the path's very last step INTO *goal_ij* may not take,
        forbidding the same fold-back over the stop-side exit stub.

    Beyond that stub-seam case, a path also carries its own segments-so-
    far along as search state and runs every candidate edge through the
    exact same :func:`_edge_too_close_to_wire` check already used
    against *other* wires -- forbidding it from heading off, doubling
    back, and turning to run too close and parallel to a stretch of
    itself (a plain simple grid path can't revisit a node, so it can
    never retrace a segment exactly, but nothing otherwise stops it from
    looping back alongside its own earlier leg one grid line over).
    This is carried per-candidate-path rather than per-node: ``best_cost``
    still dominates purely on cost, so a cheaper route to a given node
    can in rare cases shadow a costlier one whose different shape would
    have avoided a self-fold a few steps later -- accepted the same way
    an unreachable goal already is elsewhere (``route``'s own dogleg
    fallback), rather than the full rewrite a path-shape-aware state
    would need.
    """
    gx, gz = xs[goal_ij[0]], zs[goal_ij[1]]

    @_check_types.do
    def _heuristic(ij: tuple[int, int]) -> float:
        return abs(xs[ij[0]] - gx) + abs(zs[ij[1]] - gz)

    open_heap = [(_heuristic(start_ij), 0.0, start_ij, None, ())]
    best_cost = {start_ij: 0.0}
    came_from = {}

    while open_heap:
        _, cost, node, direction, own_segments = heapq.heappop(open_heap)

        if cost > best_cost.get(node, float('inf')) + _EPS:
            # Stale heap entry -- a cheaper path to this node was already
            # relaxed after this one was pushed.
            continue

        if node == goal_ij:
            path = [node]
            while node in came_from:
                node = came_from[node]
                path.append(node)
            path.reverse()
            return path

        i, j = node
        x1, z1 = xs[i], zs[j]

        for ni, nj in _neighbors(i, j, xs, zs):
            if (ni, nj) == node:
                continue

            x2, z2 = xs[ni], zs[nj]

            if _node_blocked(x2, z2, rects):
                continue
            if _edge_crosses_obstacle(x1, z1, x2, z2, rects):
                continue
            if _edge_too_close_to_wire(x1, z1, x2, z2, segments):
                continue
            if _edge_too_close_to_wire(x1, z1, x2, z2, own_segments):
                continue
            if node == start_ij and forbid_start_dir is not None:
                if _direction_sign(x2 - x1, z2 - z1) == forbid_start_dir:
                    continue
            if (ni, nj) == goal_ij and forbid_goal_dir is not None:
                if _direction_sign(x2 - x1, z2 - z1) == forbid_goal_dir:
                    continue

            step_dir = 'h' if nj == j else 'v'
            step_cost = abs(x2 - x1) + abs(z2 - z1)
            if direction is not None and step_dir != direction:
                step_cost += _BEND_COST_FACTOR * Config.layout.routing_grid

            new_cost = cost + step_cost
            if new_cost < best_cost.get((ni, nj), float('inf')) - _EPS:
                best_cost[(ni, nj)] = new_cost
                came_from[(ni, nj)] = node
                new_own_segments = own_segments + (((x1, z1), (x2, z2)),)
                priority = new_cost + _heuristic((ni, nj))
                heapq.heappush(open_heap, (priority, new_cost, (ni, nj), step_dir, new_own_segments))

    return None


@_check_types.do
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


@_check_types.do
def route(project: "_project.Project", start: tuple[float, float], stop: tuple[float, float],
         ignore_wire=None, skip_wires=frozenset(),
         start_anchor: tuple[float, float] | None = None,
         stop_anchor: tuple[float, float] | None = None) -> list[tuple[float, float]]:
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
    """
    margin = Config.layout.housing_spacing
    pitch = Config.layout.routing_grid

    rects = _obstacle_rects(project, ignore_wire=ignore_wire)
    segments = _wire_segments(project, ignore_wire=ignore_wire, skip_wires=skip_wires)

    lo_x, hi_x = min(start[0], stop[0]) - margin, max(start[0], stop[0]) + margin
    lo_z, hi_z = min(start[1], stop[1]) - margin, max(start[1], stop[1]) + margin

    nearby_rects = [
        r for r in rects if not (r[2] < lo_x or hi_x < r[0] or r[3] < lo_z or hi_z < r[1])]

    x_lines = [v for r in nearby_rects for v in (r[0], r[2])]
    z_lines = [v for r in nearby_rects for v in (r[1], r[3])]

    xs = _build_axis(start[0], stop[0], x_lines, margin, pitch)
    zs = _build_axis(start[1], stop[1], z_lines, margin, pitch)

    start_ij = (xs.index(round(start[0], 6)), zs.index(round(start[1], 6)))
    goal_ij = (xs.index(round(stop[0], 6)), zs.index(round(stop[1], 6)))

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

    path = _astar(xs, zs, start_ij, goal_ij, rects, segments, forbid_start_dir, forbid_goal_dir)
    if path is None:
        # No orthogonal route avoiding every obstacle exists at this
        # resolution/margin -- fall back to a direct single dogleg
        # (matches _build_axis always including both endpoints, so this
        # can only happen with obstacles genuinely boxing the endpoint
        # in) rather than leaving the wire with no path at all.
        return [(stop[0], start[1])]

    path_xz = [(xs[i], zs[j]) for i, j in path]
    return _collapse(path_xz)
