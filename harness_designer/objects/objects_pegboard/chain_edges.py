# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared peg-board chain/length-budget math for :class:`Wire`/:class:`Bundle`.

A wire or bundle's peg-board "chain" is its start anchor point, every
interior waypoint (a live :class:`~.wire_layout.WireLayout`/
:class:`~.bundle_layout.BundleLayout` object, in ``idx`` order), and its
stop anchor point. :func:`touching_edges` returns, for one point in that
chain, the neighbor position(s) and length budget(s) of whichever
segment(s) touch it -- a start/stop anchor always has exactly one
touching edge, an interior waypoint always has exactly two (previous and
next). Used by ``drag_handlers.editor_pegboard`` to clamp a drag so it
never stretches an attached wire/bundle segment past its real remaining
length.

Each edge's budget is computed fresh on every call, never cached/
persisted: the chain's real total length (``db_obj.length_mm``, itself
derived live from the real 3D path) split proportionally by that edge's
*current* 2D peg-board distance against the chain's total current 2D
distance -- so summing every edge's budget for one wire/bundle always
equals its real ``length_mm`` exactly. A waypoint has no independent 3D
position of its own, so there is no independent 3D sub-length to derive
a per-edge share from directly; this proportional split is the
substitute. Deliberately recomputed on every call rather than cached at
drag-arm time -- the edge touching whatever's actually being dragged
would otherwise chase its own tail (its own budget growing right along
with the distance it's meant to be constraining), defeating the clamp.
"""

import math
from typing import TYPE_CHECKING

from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from typing import Union as _Union


@_check_types.do
def touching_edges(db_obj, point_pegboard_id: bytes) -> list:
    """Return every ``(neighbor_x, neighbor_z, max_length_mm)`` edge in
    *db_obj*'s peg-board chain that touches *point_pegboard_id*.

    :param db_obj: A :class:`PJTWire` or :class:`PJTBundle` row -- both
        expose the same ``start_position_pegboard``/
        ``stop_position_pegboard``/``waypoints_pegboard``/``length_mm``
        shape, so this works unchanged for either.
    :param point_pegboard_id: The dragged point's own
        ``pjt_points_pegboard`` row id (for a waypoint) or the anchor's
        own point id (for a start/stop anchor).
    :returns: One tuple per touching edge (one for an anchor endpoint,
        two for an interior waypoint), or an empty list if
        *point_pegboard_id* isn't part of this chain at all.
    :rtype: list[tuple[float, float, float]]
    """
    start = db_obj.start_position_pegboard
    stop = db_obj.stop_position_pegboard
    waypoints = db_obj.waypoints_pegboard

    ids = [db_obj.start_position_pegboard_id]
    positions = [(float(start.x), float(start.z))]

    for wp in waypoints:
        ids.append(wp.db_id)
        positions.append((float(wp.x), float(wp.z)))

    ids.append(db_obj.stop_position_pegboard_id)
    positions.append((float(stop.x), float(stop.z)))

    if point_pegboard_id not in ids:
        return []

    total_length_mm = db_obj.length_mm

    distances = [
        math.hypot(positions[i + 1][0] - positions[i][0],
                   positions[i + 1][1] - positions[i][1])
        for i in range(len(positions) - 1)
    ]
    total_distance = sum(distances)

    if total_distance < 1e-9:
        # Degenerate (every node coincident) -- split the real length
        # evenly rather than dividing by zero.
        budgets = [total_length_mm / len(distances)] * len(distances)
    else:
        budgets = [total_length_mm * (d / total_distance) for d in distances]

    index = ids.index(point_pegboard_id)
    edges = []

    if index > 0:
        nx, nz = positions[index - 1]
        edges.append((nx, nz, budgets[index - 1]))

    if index < len(positions) - 1:
        nx, nz = positions[index + 1]
        edges.append((nx, nz, budgets[index]))

    return edges
