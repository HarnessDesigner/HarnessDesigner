# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Nearest-free-spot placement for a new peg-board floating wire table.

Run exactly once, at the moment a :class:`PJTPegboardTable` row is created
alongside its owning anchor (see ``pegboard_table.py``) -- not an ongoing
constraint; the user is free to drag a table on top of anything afterward.

Deliberately takes plain ``(min_x, min_z, max_x, max_z)`` obstacle rects
rather than live view objects/a canvas, so the actual search is a pure,
independently testable function -- the caller is responsible for gathering
those rects from whatever's actually in view (each object's own
:attr:`BaseVar.aabb`, X/Z only: peg-board is a top-down layout, so Y --
height off the board -- has no bearing on whether two footprints overlap).
Mirrors ``objects_schematic.auto_arrange._rects_overlap`` exactly (same
half-open overlap test), since that module already established the
convention for this codebase.
"""

import math

from ...geometry import point as _point
from ... import check_types as _check_types


# Ring expansion step, and how many candidate angles are sampled per ring --
# a fixed angle count (rather than one that grows with the ring's own
# circumference) is a deliberately simple, adequate-for-this-purpose
# choice: this runs once per new table, not per frame, so the search
# doesn't need to be more thorough than "good enough to reliably clear a
# normal peg-board's worth of clutter" -- see _MAX_RINGS's own comment for
# the failure-mode this trades against.
_ANGLE_SAMPLES = 16

# Hard cap so a pathologically cluttered board can't turn this into an
# unbounded search -- past this many rings, the anchor's own position is
# used as a last-resort fallback (better than hanging, and the user can
# always drag the table afterward anyway).
_MAX_RINGS = 200


@_check_types.do
def _rect_overlaps(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float]) -> bool:
    """Same half-open AABB overlap test as
    ``objects_schematic.auto_arrange._rects_overlap``.
    """
    a_min_x, a_min_z, a_max_x, a_max_z = a
    b_min_x, b_min_z, b_max_x, b_max_z = b

    return not (a_max_x <= b_min_x or b_max_x <= a_min_x
                or a_max_z <= b_min_z or b_max_z <= a_min_z)


@_check_types.do
def _table_rect(center_x: float, center_z: float, width: float,
                height: float) -> tuple[float, float, float, float]:
    half_w = width / 2.0
    half_h = height / 2.0
    return (center_x - half_w, center_z - half_h,
            center_x + half_w, center_z + half_h)


@_check_types.do
def _is_free(center_x: float, center_z: float, width: float, height: float,
            obstacles: list[tuple[float, float, float, float]]) -> bool:
    candidate = _table_rect(center_x, center_z, width, height)
    return not any(_rect_overlaps(candidate, obstacle) for obstacle in obstacles)


@_check_types.do
def find_free_position(
    anchor_center: _point.Point, width: float, height: float,
    obstacles: list[tuple[float, float, float, float]],
) -> _point.Point:
    """Return the nearest position (to *anchor_center*) where a
    ``width`` x ``height`` table doesn't overlap any rect in *obstacles*.

    Expanding-ring search: tries *anchor_center* itself first, then rings
    of :data:`_ANGLE_SAMPLES` candidate points at increasing radius (step
    = the table's own smaller dimension, so consecutive rings are spaced
    roughly one table-width apart) -- the first free candidate found is
    returned. Radius grows fastest first, so the first hit is always at
    least as close as every ring already exhausted, though not
    necessarily the single globally-nearest free point (a discrete
    ring/angle search over a continuous plane can't guarantee that
    without a much more expensive search this one-time placement doesn't
    need). Falls back to *anchor_center* unchanged if
    :data:`_MAX_RINGS` is exhausted with nothing free -- letting an
    unreasonably cluttered board still produce a table rather than fail
    outright; the user can always drag it afterward.

    :param anchor_center: World-space X/Z position the search starts
        from and stays closest to -- typically the owning anchor's own
        peg-board position. ``anchor_center.y`` is ignored -- the
        result is always returned at Y=0.0 regardless of it (see
        below).
    :type anchor_center: :class:`_point.Point`
    :param width: Table width, in world units.
    :type width: float
    :param height: Table height, in world units.
    :type height: float
    :param obstacles: Every other object's world-space X/Z footprint to
        avoid, as ``(min_x, min_z, max_x, max_z)`` tuples -- include the
        anchor's own footprint too if the table shouldn't sit directly on
        top of it.
    :type obstacles: list[tuple[float, float, float, float]]
    :returns: The chosen CENTER position for the new table, at Y=0.0 --
        this search is purely an X/Z footprint-avoidance concern
        (peg-board DEPTH, which controls OpenGL render/occlusion order
        on this permanently top-down view, is a separate, LATER
        decision belonging to whoever actually stores the result -- see
        ``pjt_pegboard_table.PJTPegboardTablesTable.insert()``, which
        elevates to ``TABLE_DEPTH_Y`` itself rather than trusting
        whatever this function returns).
    :rtype: :class:`_point.Point`
    """
    ax, az = anchor_center.x, anchor_center.z

    if _is_free(ax, az, width, height, obstacles):
        return _point.Point(ax, 0.0, az)

    step = max(min(width, height), 1.0)

    for ring in range(1, _MAX_RINGS + 1):
        radius = ring * step

        for sample in range(_ANGLE_SAMPLES):
            angle = (2.0 * math.pi * sample) / _ANGLE_SAMPLES
            cx = ax + (radius * math.cos(angle))
            cz = az + (radius * math.sin(angle))

            if _is_free(cx, cz, width, height, obstacles):
                return _point.Point(cx, 0.0, cz)

    return _point.Point(ax, 0.0, az)


@_check_types.do
def obstacle_rects_from_objects(objects, exclude=None) -> list[tuple[float, float, float, float]]:
    """Convenience gatherer: every object's own X/Z footprint from its
    :attr:`BaseVar.aabb` (Y dropped -- see module docstring), skipping
    any object with no computed AABB yet (``aabb`` is only populated once
    an object has a real ``vbo``/``position``/``scale``/``angle`` -- see
    ``BaseVar._compute_aabb``; an object with no rendering presence, or
    not yet fully constructed, has none) and, optionally, one object to
    leave out entirely (pass the peg-board table's own OWNING anchor here
    if it should be allowed to sit under its own table -- omit it, the
    default, to keep the table off the anchor's own footprint too).

    :param objects: View objects to gather footprints from (e.g. a
        canvas's own ``objects_in_view``, resolved to their peg-board
        view objects).
    :type objects: Iterable
    :param exclude: One object to skip, or ``None``.
    :type exclude: UNKNOWN
    :returns: Obstacle rects, ready for :func:`find_free_position`.
    :rtype: list[tuple[float, float, float, float]]
    """
    rects = []
    for obj in objects:
        if obj is exclude:
            continue

        aabb = getattr(obj, 'aabb', None)
        if aabb is None:
            continue

        min_x, _min_y, min_z = aabb[0]
        max_x, _max_y, max_z = aabb[1]
        rects.append((float(min_x), float(min_z), float(max_x), float(max_z)))

    return rects
