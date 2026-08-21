# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Connectivity-weighted whole-project auto-arrange for the 2D
schematic editor.

Single entry point: :func:`auto_arrange`. Builds a graph of every
housing/splice weighted by how many wires connect each pair, runs a
bounded force-directed layout so heavily-wired pairs converge closer
together (never tighter than both objects' own footprints plus
clearance for however many wires will need to route between them),
snaps the result onto the routing grid and resolves any residual
overlap, picks each housing's best 0/90/180/270 orientation by actually
running the router against each candidate and comparing total routed
length, then re-routes every wire for real (see ``wire_reroute.py``).

Repositions and re-rotates every housing/splice unconditionally --
this is a deliberate, user-triggered command, not the conservative
single-housing insert-time placement ``housing_layout.py`` does.
"""

from typing import TYPE_CHECKING

from . import wire_routing as _wire_routing
from . import wire_reroute as _wire_reroute
from ... import config as _config
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import project as _project
    from .. import housing as _housing_obj


Config = _config.Config.editor_schematic

_MAX_ITERATIONS = 500
_CONVERGENCE_EPS = 0.01  # mm total displacement -- below this, stop early
_K_ATTRACT = 0.05
_K_REPEL = 4000.0
_ROTATION_CANDIDATES = (0.0, 90.0, 180.0, 270.0)
_BEND_PENALTY_MM = 10.0  # mm, per-bend penalty added to a rotation candidate's score


@_check_types.do
def _footprint_half_extent(node) -> tuple[float, float]:
    """This node's own unrotated ``(half_width, half_height)`` --
    dimensions are position-independent for both Housing and Splice, so
    this is safe to compute once up front, before the layout moves it.
    """
    bounds = node.objschematic.get_bounds()
    if bounds is None:
        return 0.0, 0.0

    min_x, min_z, max_x, max_z = bounds
    return (max_x - min_x) / 2.0, (max_z - min_z) / 2.0


@_check_types.do
def _node_center(node) -> tuple[float, float]:
    bounds = node.objschematic.get_bounds()
    if bounds is None:
        return 0.0, 0.0

    min_x, min_z, max_x, max_z = bounds
    return (min_x + max_x) / 2.0, (min_z + max_z) / 2.0


@_check_types.do
def _node_housing(terminal) -> "_housing_obj.Housing | None":
    """Resolve a ``Terminal`` wrapper up to its owning ``Housing``
    wrapper -- via its seated cavity's own ``HousingMixin``
    (``PJTCavity.housing``); ``PJTTerminal`` has no ``housing_id`` of its
    own, only ``cavity_id`` (see ``pjt_terminal.py``'s ``cavity``
    property), so the housing has to be resolved one hop further out.
    ``None`` for a bare/unhoused terminal.
    """
    pjt_cavity = terminal.db_obj.cavity
    if pjt_cavity is None:
        return None

    pjt_housing = pjt_cavity.housing
    if pjt_housing is None:
        return None

    return pjt_housing.get_object()


@_check_types.do
def _edge_weights(project: "_project.Project") -> dict:
    """``{frozenset({node_a, node_b}): wire_count}`` for every pair of
    graph nodes (housings/splices) connected by at least one wire. A
    wire ending at a bare/unhoused terminal (no owning housing) has
    nothing to weight on that end and is simply excluded from the graph
    -- it's still re-routed for real in the final pass, it just doesn't
    influence layout since there's no housing node to move for it.
    """
    from .. import terminal as _terminal
    from .. import splice as _splice

    weights = {}
    for wire in project.wires:
        if not wire.is_connected:
            continue

        ends = []
        for sibling in (wire.start_sibling, wire.stop_sibling):
            if isinstance(sibling, _splice.Splice):
                ends.append(sibling)
            elif isinstance(sibling, _terminal.Terminal):
                housing = _node_housing(sibling)
                if housing is not None:
                    ends.append(housing)

        if len(ends) != 2 or ends[0] is ends[1]:
            continue

        key = frozenset(ends)
        weights[key] = weights.get(key, 0) + 1

    return weights


@_check_types.do
def _average_od_mm(project: "_project.Project") -> float:
    ods = [float(w.objschematic._part.od_mm) for w in project.wires if w.is_connected]  # NOQA
    if not ods:
        return 1.0

    return sum(ods) / len(ods)


@_check_types.do
def _min_separation(node_a, node_b, half_extents: dict, weight: int, avg_od_mm: float) -> float:
    """Hard floor on center-to-center distance between *node_a*/*node_b*
    -- both footprints' own radii, plus ``housing_spacing`` clearance,
    plus room for however many wires (*weight*) will need to route
    through the gap between them.
    """
    half_w_a, half_h_a = half_extents[node_a]
    half_w_b, half_h_b = half_extents[node_b]
    radius_a = max(half_w_a, half_h_a)
    radius_b = max(half_w_b, half_h_b)

    bundle_margin = weight * (avg_od_mm + Config.layout.wire_spacing)

    return radius_a + radius_b + Config.layout.housing_spacing + bundle_margin


@_check_types.do
def _force_layout(project: "_project.Project", nodes: list, edge_weights: dict) -> dict:
    """Bounded force-directed layout: an attractive spring per connected
    pair scaled by wire count (heavier-wired pairs pull closer), an
    inverse-square repulsion between every pair, both softened/boosted
    around each pair's own :func:`_min_separation` floor so the result
    never converges tighter than routing could later fit. Returns
    ``{node: (x, z)}``.
    """
    if not nodes:
        return {}

    half_extents = {n: _footprint_half_extent(n) for n in nodes}
    avg_od_mm = _average_od_mm(project)

    positions = {node: list(_node_center(node)) for node in nodes}

    for _iteration in range(_MAX_ITERATIONS):
        forces = {node: [0.0, 0.0] for node in nodes}

        for a_idx, node_a in enumerate(nodes):
            ax, az = positions[node_a]
            for node_b in nodes[a_idx + 1:]:
                bx, bz = positions[node_b]
                dx, dz = bx - ax, bz - az
                dist = max((dx * dx + dz * dz) ** 0.5, 1e-6)
                ux, uz = dx / dist, dz / dist

                weight = edge_weights.get(frozenset((node_a, node_b)), 0)
                min_sep = _min_separation(node_a, node_b, half_extents, weight, avg_od_mm)

                f_attract = 0.0
                if weight > 0:
                    f_attract = _K_ATTRACT * weight * (dist - min_sep)

                f_repel = _K_REPEL / (dist * dist)
                overlap = min_sep - dist
                if overlap > 0.0:
                    f_repel += overlap * 10.0

                f = f_attract - f_repel

                forces[node_a][0] += ux * f
                forces[node_a][1] += uz * f
                forces[node_b][0] -= ux * f
                forces[node_b][1] -= uz * f

        total_displacement = 0.0
        for node in nodes:
            fx, fz = forces[node]
            positions[node][0] += fx
            positions[node][1] += fz
            total_displacement += (fx * fx + fz * fz) ** 0.5

        if total_displacement < _CONVERGENCE_EPS:
            break

    return {node: (positions[node][0], positions[node][1]) for node in nodes}


@_check_types.do
def _snap_and_resolve(nodes: list, positions: dict) -> dict:
    """Grid-snap every converged position to
    ``Config.editor_schematic.layout.routing_grid``, then nudge apart any pair
    snapping reintroduced an overlap in -- snapping error is at most
    half a grid cell, so a handful of cheap passes always converges.
    """
    grid = Config.layout.routing_grid
    half_extents = {n: _footprint_half_extent(n) for n in nodes}

    snapped = {}
    for node in nodes:
        x, z = positions[node]
        snapped[node] = [round(x / grid) * grid, round(z / grid) * grid]

    for _pass in range(20):
        moved = False
        for a_idx, node_a in enumerate(nodes):
            ax, az = snapped[node_a]
            half_w_a, half_h_a = half_extents[node_a]
            for node_b in nodes[a_idx + 1:]:
                bx, bz = snapped[node_b]
                half_w_b, half_h_b = half_extents[node_b]

                rect_a = (ax - half_w_a, az - half_h_a, ax + half_w_a, az + half_h_a)
                rect_b = (bx - half_w_b, bz - half_h_b, bx + half_w_b, bz + half_h_b)

                if not _rects_overlap(rect_a, rect_b):
                    continue

                dx, dz = bx - ax, bz - az
                dist = max((dx * dx + dz * dz) ** 0.5, 1e-6)
                push = grid
                ux, uz = dx / dist, dz / dist

                snapped[node_b][0] = round((bx + ux * push) / grid) * grid
                snapped[node_b][1] = round((bz + uz * push) / grid) * grid
                moved = True

        if not moved:
            break

    return {node: tuple(snapped[node]) for node in nodes}


@_check_types.do
def _rects_overlap(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float]) -> bool:
    a_min_x, a_min_z, a_max_x, a_max_z = a
    b_min_x, b_min_z, b_max_x, b_max_z = b

    return not (a_max_x <= b_min_x or b_max_x <= a_min_x
                or a_max_z <= b_min_z or b_max_z <= a_min_z)


@_check_types.do
def _apply_positions(positions: dict) -> None:
    """Write every converged/snapped ``(x, z)`` to its node's own
    ``position2d`` -- ``Housing``/``Splice`` both expose the same
    ``db_obj.position2d`` shape.
    """
    for node, (x, z) in positions.items():
        position = node.db_obj.position2d
        with position:
            position.x = x
            position.z = z


@_check_types.do
def _path_length(start: tuple[float, float], stop: tuple[float, float],
                 waypoints: list[tuple[float, float]]) -> float:
    points = [start] + waypoints + [stop]
    total = 0.0
    for (x1, z1), (x2, z2) in zip(points, points[1:]):
        total += abs(x2 - x1) + abs(z2 - z1)

    return total


@_check_types.do
def _score_rotation(project: "_project.Project", housing: "_housing_obj.Housing") -> float:
    """Total routed length + a per-bend penalty across every wire
    currently attached to *housing*, at its *current* angle2d -- lower
    is better. Does not persist any waypoints (unlike
    ``wire_reroute.reroute_wire``) -- purely a scoring pass.
    """
    score = 0.0
    for wire in _wire_reroute.wires_attached_to(housing):
        start = wire.db_obj.start_position2d
        stop = wire.db_obj.stop_position2d
        od_mm = float(wire.objschematic._part.od_mm)  # NOQA

        waypoints = _wire_routing.route(
            project, (float(start.x), float(start.z)), (float(stop.x), float(stop.z)),
            ignore_wire=wire, od_mm=od_mm)

        score += _path_length(
            (float(start.x), float(start.z)), (float(stop.x), float(stop.z)), waypoints)
        score += _BEND_PENALTY_MM * len(waypoints)

    return score


@_check_types.do
def _best_rotation(project: "_project.Project", housing: "_housing_obj.Housing") -> None:
    """Try every 90° candidate for *housing*, scoring each by actually
    routing its attached wires against it, and leave it set to whichever
    scored lowest -- reuses the router itself as the scoring function.
    """
    angle = housing.db_obj.angle2d

    best_angle = angle.y
    best_score = None

    for candidate in _ROTATION_CANDIDATES:
        angle.y = candidate
        score = _score_rotation(project, housing)

        if best_score is None or score < best_score:
            best_score = score
            best_angle = candidate

    angle.y = best_angle


@_check_types.do
def auto_arrange(project: "_project.Project") -> None:
    """Rearrange and re-rotate every housing/splice in *project* by
    connectivity, then re-route every wire. See module docstring.
    """
    nodes = list(project.housings) + list(project.splices)
    if not nodes:
        return

    edge_weights = _edge_weights(project)

    positions = _force_layout(project, nodes, edge_weights)
    positions = _snap_and_resolve(nodes, positions)
    _apply_positions(positions)

    for housing in project.housings:
        _best_rotation(project, housing)

    for wire in sorted(
            (w for w in project.wires if w.is_connected),
            key=lambda w: float(w.objschematic._part.od_mm), reverse=True):  # NOQA
        _wire_reroute.reroute_wire(project, wire)
