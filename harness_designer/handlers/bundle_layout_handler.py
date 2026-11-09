# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding bundle layout points.
"""

from typing import TYPE_CHECKING

import numpy as np

from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import bundle_layout as _bundle_layout
from ..objects import bundle as _bundle
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_3d import camera as _camera
    from ..objects import project as _project


_SNAP_THRESHOLD = 5.0


@_check_types.do
def _bundle_segments(bundle: _bundle.Bundle) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Every (p1, p2) sub-segment of *bundle*'s current 3D path, as numpy
    arrays -- start, through each interior waypoint in idx order, to
    stop. Mirrors handlers.wire_layout_handler's own _wire_segments.
    """

    points = [bundle.obj3d.start_position.as_numpy]

    for waypoint in bundle.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)

    points.append(bundle.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


@_check_types.do
def _find_bundle(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project: "_project.Project"
) -> _bundle.Bundle | None:
    """
    Return the bundle under the mouse, or the closest one within the snap threshold.
    """

    selected = _object_picker.find_object(mouse_pos, camera, camera.canvas)

    if isinstance(selected, _bundle.Bundle):
        return selected

    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    best_bundle = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for bndl in project.bundles:
        if not bndl.is_in_3dview:
            continue

        for p1, p2 in _bundle_segments(bndl):
            seg = p2 - p1
            seg_len_sq = float(np.dot(seg, seg))
            if seg_len_sq < 1e-8:
                continue

            t = max(
                0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))

            closest = p1 + t * seg
            dist_sq = float(np.sum((world_pos - closest) ** 2))

            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_bundle = bndl

    return best_bundle


@_check_types.do
def _find_insertion_index(bundle: _bundle.Bundle, position: np.ndarray) -> int:
    """
    Return which sub-segment of *bundle*'s current path *position*
    falls closest to -- equivalently, how many of its existing interior
    waypoints come before a new one inserted there. Mirrors
    handlers.wire_layout_handler._find_insertion_index.
    """

    best_idx = 0
    best_dist = None

    for i, (p1, p2) in enumerate(_bundle_segments(bundle)):
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
def _create_bundle_layout_at_endpoint(
    project: "_project.Project",
    bundle: _bundle.Bundle,
    endpoint: str,
) -> _bundle_layout.BundleLayout:

    if endpoint == 'start':
        point = bundle.obj3d.start_position
    else:
        point = bundle.obj3d.stop_position

    coord_id = point.db_id[:-2]
    db_obj = project.ptables.pjt_bundle_layouts_table.insert(point3d_id=coord_id)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    return layout_obj


@_check_types.do
def _create_bundle_layout_on_bundle(
    project: "_project.Project",
    bundle: _bundle.Bundle,
    position: _point.Point,
    insert_idx: int | None = None,
) -> _bundle_layout.BundleLayout:
    """
    Insert a new interior waypoint into *bundle*'s own path at
    *position* and mark it with a BundleLayout.

    No new ``pjt_bundles`` row is created -- an ordinary bend is just a
    waypoint in the same bundle's own ``pjt_bundle_paths`` list, shifting
    every existing waypoint at or past the insertion point up by one
    index. Mirrors handlers.wire_layout_handler._create_wire_layout_on_wire.

    *insert_idx* should be the segment index
    ``bundle.obj3d.get_closest_point`` already found *position* on --
    only computed here (via _find_insertion_index) when the caller
    doesn't have one on hand, e.g. the bundle's own midpoint, when no
    click was captured.
    """

    ptables = project.ptables

    if insert_idx is None:
        insert_idx = _find_insertion_index(bundle, position.as_numpy)

    pos_db = ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z))

    ptables.pjt_bundle_paths_table.add(
        bundle.db_obj.db_id, '3d', insert_idx, pos_db.db_id)

    db_obj = ptables.pjt_bundle_layouts_table.insert(point3d_id=pos_db.db_id)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    bundle.obj3d.refresh_waypoints()

    return layout_obj


@_check_types.do
def remove_waypoint(project: "_project.Project", layout_db: object, view: str) -> None:
    """Take the waypoint a bundle layout marks out of its bundle's route in *view* (``'3d'`` or ``'pegboard'``) and delete its point.

    The layout's own row is deleted by the caller afterwards; without this the bundle would keep the waypoint (its ``pjt_bundle_paths``
    row and the point) with nothing left to show it. As for a wire's layout (``objects_3d.wire_layout.WireLayout._reconnect_wires``):
    nothing happens for a layout that is not a waypoint of exactly one bundle (an end, or a seam between two bundles, which is not merged
    back here). The wires routed through the bundle carry the same point in their own routes, so it comes out of those first (a point is
    not deleted while a route references it), and every owner is refreshed.

    :param project: The project.
    :param layout_db: The layout's row (``PJTBundleLayout``).
    :param view: ``'3d'`` or ``'pegboard'``.
    """
    ptables = project.ptables

    if view == '3d':
        point_id = layout_db.position3d_id
        points_table = ptables.pjt_points3d_table
    else:
        point_id = layout_db.position_pegboard_id
        points_table = ptables.pjt_points_pegboard_table

    if point_id is None:
        return

    bundles = layout_db.attached_bundles

    if len(bundles) != 1:
        return

    bundle_db = bundles[0]

    if bundle_db.db_id not in ptables.pjt_bundle_paths_table.bundle_ids_for_point(view, point_id):
        return

    bundle_obj = bundle_db.get_object()
    wire_ids = ptables.pjt_wire_paths_table.wire_ids_for_point(view, point_id)

    for wire_id in wire_ids:
        ptables.pjt_wire_paths_table.remove(wire_id, view, point_id)

    ptables.pjt_bundle_paths_table.remove(bundle_db.db_id, view, point_id)
    points_table[point_id].delete()

    owners = [bundle_obj]

    for wire_id in wire_ids:
        owners.append(ptables.pjt_wires_table[wire_id].get_object())

    for owner in owners:
        if owner is None:
            continue

        if view == '3d':
            owner.obj3d.refresh_waypoints()
        else:
            owner.objpegboard.refresh_waypoints()
