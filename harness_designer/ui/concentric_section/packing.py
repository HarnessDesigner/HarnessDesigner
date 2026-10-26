# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Circle packing for the concentric cross-section view.

A multi-conductor cable's conductors are drawn packed as tightly as possible
inside as near a circle as possible. Equal circles use the exact answers up to
seven (one ring, or one ring around a centre circle). Anything else -- more
conductors, or conductors of different sizes -- is relaxed numerically: the
circles start on a sunflower spiral, are pulled toward the middle and pushed
apart until none overlap, and the best of a few seeded restarts is kept.
Everything is deterministic, so a cable always draws the same way.

The view's screen coordinates have +y pointing DOWN, so "top" is -y.
"""

from functools import lru_cache

import math
import numpy as np

from ... import check_types as _check_types


_GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
_EQUAL_TOLERANCE = 1e-9
_RESTART_COUNT = 6
_RELAX_STEPS = 260
_RESOLVE_PASSES = 6
_FINAL_PASSES = 400
_SEARCH_DIRECTIONS = 16
_TOP = -math.pi / 2.0


@_check_types.do
def envelope_factor(count: int) -> float:
    """Return the diameter of the circle that holds *count* equal circles,
    divided by one circle's diameter, packed as :func:`pack_circles` does.

    Exact for one to seven (a ring is ``1 + 1 / sin(pi / count)``; six and
    seven are a ring around a centre circle, 3.0).

    :param count: How many equal circles.
    :type count: int
    :returns: The factor.
    :rtype: float
    """
    return pack_circles(tuple([1.0] * count))[1]


@_check_types.do
def _all_equal(radii: tuple[float, ...]) -> bool:
    first = radii[0]
    for radius in radii:
        if abs(radius - first) > _EQUAL_TOLERANCE:
            return False

    return True


@_check_types.do
def _ring(count: int, ring_radius: float, start_angle: float) -> list[tuple[float, float]]:
    points = []
    for index in range(count):
        angle = start_angle + index * 2.0 * math.pi / count
        points.append((ring_radius * math.cos(angle), ring_radius * math.sin(angle)))

    return points


@_check_types.do
def _resolve_overlaps(positions: np.ndarray, radii_sum: np.ndarray, passes: int) -> None:
    """Push overlapping circles apart, in place, until none overlap or
    *passes* are used."""
    for _ in range(passes):
        delta = positions[:, None, :] - positions[None, :, :]
        distance = np.sqrt(np.sum(delta * delta, axis=2))
        np.fill_diagonal(distance, 1.0e30)

        overlap = radii_sum - distance
        pushing = overlap > 1.0e-9
        if not pushing.any():
            return

        scale = np.where(pushing, overlap * 0.5 / np.maximum(distance, 1.0e-12), 0.0)
        positions += 0.6 * np.sum(scale[:, :, None] * delta, axis=1)


@_check_types.do
def _relax(radii: np.ndarray, seed: int) -> np.ndarray:
    """Return centres for circles of *radii*, packed toward the origin."""
    count = radii.shape[0]
    rng = np.random.default_rng(seed)
    area = float(np.sum(np.pi * radii * radii))
    spread = math.sqrt(area / 0.45 / math.pi)
    jitter = 0.15 * float(np.mean(radii))

    # biggest first, so the big circles start nearest the middle
    order = np.argsort(-radii, kind='stable')
    positions = np.zeros((count, 2), dtype=float)
    for rank in range(count):
        index = int(order[rank])
        rho = spread * math.sqrt((rank + 0.5) / count)
        theta = rank * _GOLDEN_ANGLE
        positions[index, 0] = rho * math.cos(theta) + rng.uniform(-jitter, jitter)
        positions[index, 1] = rho * math.sin(theta) + rng.uniform(-jitter, jitter)

    radii_sum = radii[:, None] + radii[None, :]
    for step in range(_RELAX_STEPS):
        pull = 0.04 * (1.0 - step / _RELAX_STEPS) + 0.002
        positions *= (1.0 - pull)
        _resolve_overlaps(positions, radii_sum, _RESOLVE_PASSES)

    _resolve_overlaps(positions, radii_sum, _FINAL_PASSES)
    return positions


@_check_types.do
def _reach(positions: np.ndarray, radii: np.ndarray, center: np.ndarray) -> float:
    offsets = positions - center
    return float(np.max(np.sqrt(np.sum(offsets * offsets, axis=1)) + radii))


@_check_types.do
def _enclosing_center(positions: np.ndarray, radii: np.ndarray) -> np.ndarray:
    """Return the centre of (very nearly) the smallest circle that holds
    every circle, found by a shrinking compass search -- the reach is convex,
    so it settles on the optimum."""
    center = (positions.min(axis=0) + positions.max(axis=0)) / 2.0
    best = _reach(positions, radii, center)
    step = best * 0.5

    directions = []
    for index in range(_SEARCH_DIRECTIONS):
        angle = index * 2.0 * math.pi / _SEARCH_DIRECTIONS
        directions.append(np.array((math.cos(angle), math.sin(angle))))

    while step > best * 1.0e-5:
        best_candidate = center
        best_value = best
        for direction in directions:
            candidate = center + step * direction
            value = _reach(positions, radii, candidate)
            if value < best_value:
                best_value = value
                best_candidate = candidate

        if best_value < best:
            best = best_value
            center = best_candidate
        else:
            step *= 0.5

    return center


@lru_cache(maxsize=None)
@_check_types.do
def _ring_pack(count: int) -> tuple[tuple[tuple[float, float], ...], float]:
    """Pack *count* equal UNIT circles as a ring of touching circles around a
    smaller pack of the rest (itself built this way), taking the ring size
    that gives the smallest enclosing circle. Exact for 8 and 9 circles, close
    for the rest; :func:`pack_circles` competes it with a numeric relaxation.
    """
    if count <= 7:
        return pack_circles(tuple([1.0] * count))

    best_reach = math.inf
    best_centers: tuple[tuple[float, float], ...] = ()

    for ring_count in range(6, count + 1):
        ring_center = 1.0 / math.sin(math.pi / ring_count)
        inner_count = count - ring_count

        inner: tuple[tuple[float, float], ...] = ()
        if inner_count > 0:
            inner, inner_reach = _ring_pack(inner_count)
            # the rest must fit inside the ring's circles
            if inner_reach > ring_center - 1.0 + 1.0e-9:
                continue

        reach = ring_center + 1.0
        if reach < best_reach - 1.0e-9:
            best_reach = reach
            best_centers = inner + tuple(_ring(ring_count, ring_center, _TOP))

    return best_centers, best_reach


@lru_cache(maxsize=512)
@_check_types.do
def pack_circles(radii: tuple[float, ...]) -> tuple[tuple[tuple[float, float], ...], float]:
    """Pack circles of the given radii as tightly as possible inside as near
    a circle as possible.

    :param radii: The radius of each circle (hashable, so results are cached).
    :type radii: tuple[float, ...]
    :returns: The centre of each circle (same order as *radii*, relative to
        the middle of the enclosing circle) and the enclosing circle's radius.
    :rtype: tuple[tuple[tuple[float, float], ...], float]
    """
    count = len(radii)

    if count == 0:
        return (), 0.0

    if count == 1:
        return ((0.0, 0.0),), radii[0]

    if count == 2:
        first, second = radii
        return ((-second, 0.0), (first, 0.0)), first + second

    equal = _all_equal(radii)

    if equal:
        radius = radii[0]

        if count <= 5:
            ring_radius = radius / math.sin(math.pi / count)
            start = _TOP
            if count % 2 == 0:
                start = _TOP + math.pi / count

            return tuple(_ring(count, ring_radius, start)), ring_radius + radius

        if count == 6:
            centers = [(0.0, 0.0)]
            centers.extend(_ring(5, 2.0 * radius, _TOP))
            return tuple(centers), 3.0 * radius

        if count == 7:
            centers = [(0.0, 0.0)]
            centers.extend(_ring(6, 2.0 * radius, _TOP))
            return tuple(centers), 3.0 * radius

    radii_array = np.array(radii, dtype=float)
    best_reach = math.inf
    best_positions = np.zeros((count, 2), dtype=float)

    if equal:
        # the ring construction is a candidate too; the relaxation below has to beat it
        ring_centers, ring_reach = _ring_pack(count)
        best_positions = np.array(ring_centers, dtype=float) * radii[0]
        best_reach = ring_reach * radii[0]

    for restart in range(_RESTART_COUNT):
        positions = _relax(radii_array, restart)
        center = _enclosing_center(positions, radii_array)
        positions = positions - center
        reach = _reach(positions, radii_array, np.zeros(2))

        if reach < best_reach:
            best_reach = reach
            best_positions = positions

    packed = tuple((float(x), float(y)) for x, y in best_positions)
    return packed, float(best_reach)
