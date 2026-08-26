# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding bundle layout points.
"""

import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import bundle_layout as _bundle_layout
from ..objects import bundle as _bundle
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_3d import camera as _camera


_SNAP_THRESHOLD = 5.0


@_check_types.do
def _bundle_segments(bundle: _bundle.Bundle):
    """Every (p1, p2) sub-segment of *bundle*'s current 3D path, as numpy
    arrays -- start, through each interior waypoint in idx order, to
    stop. Mirrors handlers.wire_layout_handler's own _wire_segments."""
    points = [bundle.obj3d.start_position.as_numpy]

    for waypoint in bundle.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)

    points.append(bundle.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


@_check_types.do
def _find_bundle(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project
) -> _bundle.Bundle | None:
    """
    Return the bundle under the mouse, or the closest one within the snap threshold.
    """

    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera,
        _handler_base.HandlerBase._get_view_object)

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

            t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
            closest = p1 + t * seg
            dist_sq = float(np.sum((world_pos - closest) ** 2))

            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_bundle = bndl

    return best_bundle


@_check_types.do
def _find_insertion_index(bundle: _bundle.Bundle, position: np.ndarray) -> int:
    """Return which sub-segment of *bundle*'s current path *position*
    falls closest to -- equivalently, how many of its existing interior
    waypoints come before a new one inserted there. Mirrors
    handlers.wire_layout_handler._find_insertion_index."""
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
    project,
    bundle: _bundle.Bundle,
    endpoint: str,
    diameter: float
) -> _bundle_layout.BundleLayout:

    if endpoint == 'start':
        point = bundle.obj3d.start_position
    else:
        point = bundle.obj3d.stop_position

    coord_id = point.db_id[:-2]
    db_obj = project.ptables.pjt_bundle_layouts_table.insert(coord_id, diameter)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    return layout_obj


@_check_types.do
def _create_bundle_layout_on_bundle(
    project,
    bundle: _bundle.Bundle,
    position: _point.Point,
    diameter: float,
    insert_idx: int | None = None,
) -> _bundle_layout.BundleLayout:
    """Insert a new interior waypoint into *bundle*'s own path at
    *position* and mark it with a BundleLayout.

    No new ``pjt_bundles`` row is created -- an ordinary bend is just a
    tagged waypoint (``bundle_id``/``idx``) on the same bundle, shifting
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

    existing = bundle.db_obj.waypoints3d
    for waypoint in reversed(existing[insert_idx:]):
        waypoint.idx = waypoint.idx + 1

    pos_db = ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z),
        bundle_id=bundle.db_obj.db_id, idx=insert_idx)

    db_obj = ptables.pjt_bundle_layouts_table.insert(pos_db.db_id, diameter)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    bundle.obj3d.refresh_waypoints()

    return layout_obj
