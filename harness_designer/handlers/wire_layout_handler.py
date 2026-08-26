# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding wire layout points.
"""

import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import wire as _wire
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_3d import camera as _camera


_SNAP_THRESHOLD = 5.0


@_check_types.do
def _wire_segments(wire: _wire.Wire):
    """Every (p1, p2) sub-segment of *wire*'s current 3D path, as numpy
    arrays -- start, through each interior waypoint in idx order, to
    stop. Mirrors objects.objects_3d.mixins.wire_type.WireTypeMixin's own
    _segments (kept as a small local helper here rather than reaching
    into that mixin, matching this file's existing style of self-
    contained module-level helpers)."""
    points = [wire.obj3d.start_position.as_numpy]
    for waypoint in wire.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)
    points.append(wire.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


@_check_types.do
def _find_wire(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project
) -> _wire.Wire | None:
    """Return the wire under the mouse, or the closest one within the snap threshold."""
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera, _handler_base.HandlerBase._get_view_object)

    if isinstance(selected, _wire.Wire):
        return selected

    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    best_wire = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for w in project.wires:
        if not w.is_in_3dview:
            continue

        for p1, p2 in _wire_segments(w):
            seg = p2 - p1
            seg_len_sq = float(np.dot(seg, seg))
            if seg_len_sq < 1e-8:
                continue

            t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
            closest = p1 + t * seg
            dist_sq = float(np.sum((world_pos - closest) ** 2))

            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_wire = w

    return best_wire


@_check_types.do
def _find_insertion_index(wire: _wire.Wire, position: np.ndarray) -> int:
    """Return which sub-segment of *wire*'s current path *position* falls
    closest to -- equivalently, how many of its existing interior
    waypoints come before a new one inserted there. Same technique as
    handlers.wire_topology._segment_index (duplicated locally rather than
    imported -- that module is for the splice/service-loop fork/merge
    case specifically; this file never forks a wire's own row anymore)."""
    best_idx = 0
    best_dist = None

    for i, (p1, p2) in enumerate(_wire_segments(wire)):
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-12:
            continue

        t = max(0.0, min(1.0, float(np.dot(position - p1, seg)) / seg_len_sq))
        closest = p1 + t * seg
        dist = float(np.sum((position - closest) ** 2))

        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


@_check_types.do
def _create_wire_layout_at_endpoint(
    project,
    wire: _wire.Wire,
    endpoint: str
) -> _wire_layout.WireLayout:
    if endpoint == 'start':
        point = wire.obj3d.start_position
    else:
        point = wire.obj3d.stop_position

    coord_id = point.db_id[:-2]
    db_obj = project.ptables.pjt_wire_layouts_table.insert(coord_id)
    layout_obj = _wire_layout.WireLayout(project.mainframe, db_obj)
    project.add_wire_layout(layout_obj)

    return layout_obj


@_check_types.do
def _create_wire_layout_on_wire(
    project,
    wire: _wire.Wire,
    position: _point.Point,
    insert_idx: int | None = None,
) -> _wire_layout.WireLayout:
    """Insert a new interior waypoint into *wire*'s own path at
    *position* and mark it with a WireLayout.

    Unlike the row-splitting this used to do, no new ``pjt_wires`` row is
    created -- an ordinary bend is just a tagged waypoint (``wire_id``/
    ``idx``) on the same wire, shifting every existing waypoint at or
    past the insertion point up by one index. Mirrors
    ``handlers.pegboard_handler._insert_waypoint_on_edge``'s own shift-
    in-reverse-order technique for a bundle's waypoint chain.

    *insert_idx* should be the segment index
    ``wire.obj3d.get_closest_point`` already found *position* on -- that
    walk already determines which segment (and so which insertion index)
    wins, so passing it through here avoids a second, separate walk over
    the same segments to re-derive it. Only computed here (via
    _find_insertion_index) when the caller doesn't have one on hand, e.g.
    a position that didn't come from get_closest_point at all (the
    wire's own midpoint, when no click was captured).
    """
    ptables = project.ptables

    if insert_idx is None:
        insert_idx = _find_insertion_index(wire, position.as_numpy)

    existing = wire.db_obj.waypoints3d
    for waypoint in reversed(existing[insert_idx:]):
        waypoint.idx = waypoint.idx + 1

    pos_db = ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z),
        wire_id=wire.db_obj.db_id, idx=insert_idx)

    db_obj = ptables.pjt_wire_layouts_table.insert(pos_db.db_id)
    layout_obj = _wire_layout.WireLayout(project.mainframe, db_obj)
    project.add_wire_layout(layout_obj)

    wire.obj3d.refresh_waypoints()

    return layout_obj
