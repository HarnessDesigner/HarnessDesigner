# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared wire-topology helpers: forking a wire in two around a real
junction (splice, wire service loop) and merging two forked wires back
into one when that junction is removed.

Ordinary bends never go through here -- they're just waypoints on a
single wire row (see handlers.wire_layout_handler). This module is only
for the two junction types that actually change a wire's own identity:
inserting one splits a wire into two rows; removing one merges them back.
Used by handlers.splice_handler and handlers.wire_service_loop_handler.
"""

from typing import TYPE_CHECKING

import numpy as np

from ..geometry import line as _line
from ..objects import wire as _wire

if TYPE_CHECKING:
    from ..objects.project import Project


def _segment_index(wire: _wire.Wire, position: np.ndarray) -> int:
    """Return which sub-segment of *wire*'s current path *position* falls
    closest to -- equivalently, how many of its existing interior
    waypoints come before it."""
    points = [wire.obj3d.start_position.as_numpy]
    for wp in wire.db_obj.waypoints3d:
        points.append(wp.point.as_numpy)
    points.append(wire.obj3d.stop_position.as_numpy)

    best_idx = 0
    best_dist = None

    for i, (p1, p2) in enumerate(zip(points, points[1:])):
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


def split_wire_at_point(
    project: "Project",
    wire: _wire.Wire,
    coord_id_3d: int,
) -> tuple[_wire.Wire, _wire.Wire]:
    """Fork *wire* into two new wires meeting at *coord_id_3d* -- an
    already-created ``pjt_points3d`` row (e.g. a splice/loop's own attach
    point). Interior waypoints are sliced at the corresponding position
    and each half renumbered from 0; wire markers are reassigned to
    whichever half they now belong to; whatever was attached to *wire*'s
    own start/stop (a Terminal, another Splice/Loop) is re-homed onto the
    correct new half.

    The two new wires' own 2D endpoint at the fork is a fresh placeholder
    point (0, 0) -- there's no schematic-view drawing tool yet to supply
    a real 2D cut position (see the caller's own junction object, which
    is where a real one would eventually come from), and interior 2D
    waypoints (also none in practice yet) are split using the same index
    as the 3D side for lack of any independent 2D geometry to go by.

    Returns (wire_before, wire_after) -- wire_before keeps *wire*'s own
    start; wire_after keeps its stop.
    """
    orig = wire.db_obj
    ptables = project.ptables
    mainframe = project.mainframe

    part_id = orig.part_id
    name = orig.name
    circuit_id = orig.circuit_id
    layer_id = orig.layer_id
    layer_view_point_id = orig.layer_view_position_id
    is_filler_wire = orig.is_filler_wire
    is_visible3d = orig.is_visible3d
    is_visible2d = orig.is_visible2d

    start_id_3d = int(wire.obj3d.start_position.db_id[:-2])
    stop_id_3d = int(wire.obj3d.stop_position.db_id[:-2])
    start_id_2d = orig.start_position2d_id
    stop_id_2d = orig.stop_position2d_id

    coord_point = ptables.pjt_points3d_table[coord_id_3d]
    split_idx = _segment_index(wire, coord_point.point.as_numpy)

    waypoints3d = orig.waypoints3d
    before_3d = waypoints3d[:split_idx]
    after_3d = waypoints3d[split_idx:]

    waypoints2d = orig.waypoints2d
    split_idx_2d = min(split_idx, len(waypoints2d))
    before_2d = waypoints2d[:split_idx_2d]
    after_2d = waypoints2d[split_idx_2d:]

    coord_id_2d_before = ptables.pjt_points2d_table.insert(0.0, 0.0).db_id
    coord_id_2d_after = ptables.pjt_points2d_table.insert(0.0, 0.0).db_id

    orig_start_sibling = wire.start_sibling
    orig_stop_sibling = wire.stop_sibling

    wire1_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, coord_id_3d,
        start_id_2d, coord_id_2d_before,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire)

    wire2_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        coord_id_3d, stop_id_3d,
        coord_id_2d_after, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire)

    for i, wp in enumerate(before_3d):
        wp.wire_id = wire1_db.db_id
        wp.idx = i
    for i, wp in enumerate(after_3d):
        wp.wire_id = wire2_db.db_id
        wp.idx = i
    for i, wp in enumerate(before_2d):
        wp.wire_id = wire1_db.db_id
        wp.idx = i
    for i, wp in enumerate(after_2d):
        wp.wire_id = wire2_db.db_id
        wp.idx = i

    wire1_obj = _wire.Wire(mainframe, wire1_db)
    wire2_obj = _wire.Wire(mainframe, wire2_db)

    if orig_start_sibling is not None:
        wire1_obj.set_sibling(orig_start_sibling, 'start')
        orig_start_sibling.replace_wire(wire, wire1_obj)
    if orig_stop_sibling is not None:
        wire2_obj.set_sibling(orig_stop_sibling, 'stop')
        orig_stop_sibling.replace_wire(wire, wire2_obj)

    project.add_wire(wire1_obj)
    project.add_wire(wire2_obj)

    # Original's waypoints have all already been re-tagged above, so
    # Wire.delete()'s own waypoint cleanup (which deletes everything
    # still tagged to *this* wire_id) finds nothing left to touch.
    split_distance = _line.Line(
        wire.obj3d.start_position, wire1_obj.obj3d.stop_position).length()

    for marker in project.wire_markers:
        if marker.db_obj.wire_id != orig.db_id:
            continue

        marker_distance = _line.Line(
            wire.obj3d.start_position, marker.obj3d.position).length()
        new_wire = wire1_obj if marker_distance <= split_distance else wire2_obj

        marker.db_obj.wire_id = new_wire.db_obj.db_id
        marker.obj3d.rebind_wire(new_wire.db_obj)

    if mainframe.get_selected() is wire:
        wire.set_selected(False)
    wire.delete()

    return wire1_obj, wire2_obj


def merge_wires(
    project: "Project",
    wire_before: _wire.Wire,
    wire_after: _wire.Wire,
) -> _wire.Wire:
    """Merge two wires that were forked around a now-removed junction
    (splice/service loop) back into a single row spanning
    *wire_before*'s own start to *wire_after*'s own stop.

    Concatenates both wires' waypoint lists (*wire_before*'s kept as-is,
    *wire_after*'s renumbered to continue directly after), re-homes
    whatever was attached to their own outer ends (*wire_before*'s start,
    *wire_after*'s stop) onto the merged wire, and reassigns wire
    markers. Both original rows are deleted; returns the new merged wire.
    """
    ptables = project.ptables
    mainframe = project.mainframe

    orig = wire_before.db_obj
    part_id = orig.part_id
    name = orig.name
    circuit_id = orig.circuit_id
    layer_id = orig.layer_id
    layer_view_point_id = orig.layer_view_position_id
    is_filler_wire = orig.is_filler_wire
    is_visible3d = orig.is_visible3d
    is_visible2d = orig.is_visible2d

    start_id_3d = int(wire_before.obj3d.start_position.db_id[:-2])
    stop_id_3d = int(wire_after.obj3d.stop_position.db_id[:-2])
    start_id_2d = wire_before.db_obj.start_position2d_id
    stop_id_2d = wire_after.db_obj.stop_position2d_id

    before_waypoints3d = wire_before.db_obj.waypoints3d
    after_waypoints3d = wire_after.db_obj.waypoints3d
    before_waypoints2d = wire_before.db_obj.waypoints2d
    after_waypoints2d = wire_after.db_obj.waypoints2d

    orig_start_sibling = wire_before.start_sibling
    orig_stop_sibling = wire_after.stop_sibling

    merged_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, stop_id_3d,
        start_id_2d, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire)

    offset_3d = len(before_waypoints3d)
    for i, wp in enumerate(before_waypoints3d):
        wp.wire_id = merged_db.db_id
        wp.idx = i
    for i, wp in enumerate(after_waypoints3d):
        wp.wire_id = merged_db.db_id
        wp.idx = offset_3d + i

    offset_2d = len(before_waypoints2d)
    for i, wp in enumerate(before_waypoints2d):
        wp.wire_id = merged_db.db_id
        wp.idx = i
    for i, wp in enumerate(after_waypoints2d):
        wp.wire_id = merged_db.db_id
        wp.idx = offset_2d + i

    merged_obj = _wire.Wire(mainframe, merged_db)

    if orig_start_sibling is not None:
        merged_obj.set_sibling(orig_start_sibling, 'start')
        orig_start_sibling.replace_wire(wire_before, merged_obj)
    if orig_stop_sibling is not None:
        merged_obj.set_sibling(orig_stop_sibling, 'stop')
        orig_stop_sibling.replace_wire(wire_after, merged_obj)

    project.add_wire(merged_obj)

    before_id = wire_before.db_obj.db_id
    after_id = wire_after.db_obj.db_id

    for marker in project.wire_markers:
        if marker.db_obj.wire_id not in (before_id, after_id):
            continue

        marker.db_obj.wire_id = merged_db.db_id
        marker.obj3d.rebind_wire(merged_db)

    # Waypoints from both originals have already been re-tagged onto
    # merged_db above, so each delete() finds nothing left of its own to
    # clean up (see Wire.delete's waypoint-cleanup loop).
    for w in (wire_before, wire_after):
        if mainframe.get_selected() is w:
            w.set_selected(False)
        w.delete()

    return merged_obj
