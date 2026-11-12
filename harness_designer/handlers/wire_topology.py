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
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..objects import project as _project
    from ..database.project_db.pjt_bases import ProjectTables as _ProjectTables


@_check_types.do
def segment_index(wire: _wire.Wire, position: np.ndarray, view: str = '3d') -> int:
    """Return which sub-segment of *wire*'s current path *position* falls
    closest to -- equivalently, how many of its existing interior
    waypoints come before it. *view* selects which of the wire's
    independent per-view point lists to walk (``'3d'``, the original and
    still the default, or ``'pegboard'`` -- added for
    handlers.wire_routing_handler's own peg-board routing pass; each
    view's waypoints are independent, per BUNDLE_PLACEMENT.md, so the
    same *position* against a different view's own list can legitimately
    return a different index). Public (not module-private) because
    handlers.wire_routing_handler calls this from outside this module."""
    if view == '3d':
        start = wire.obj3d.start_position.as_numpy
        stop = wire.obj3d.stop_position.as_numpy
        waypoints = wire.db_obj.waypoints3d
    elif view == 'pegboard':
        start = wire.objpegboard.start_position.as_numpy
        stop = wire.objpegboard.stop_position.as_numpy
        waypoints = wire.db_obj.waypoints_pegboard
    else:
        raise ValueError(f"view must be '3d' or 'pegboard', got {view!r}")

    points = [start]
    for wp in waypoints:
        points.append(wp.point.as_numpy)
    points.append(stop)

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


@_check_types.do
def hidden_waypoint_ids(ptables: "_ProjectTables", wire_id: bytes, view: str) -> set:
    """Point ids (raw ``pjt_points3d``/``pjt_points_pegboard`` row ids,
    matching ``PJTWirePath.point_id`` -- NOT a live geometry ``Point``'s
    own suffixed ``db_id``, see e.g. ``objects.objects_3d.wire.Wire.
    is_housing_attached``) on *wire_id*'s own route for *view* that sit
    inside a bundle or transition's span -- BUNDLE_DESIGN.md 2.6's
    ``bundle_id``/``transition_id`` tag columns on ``pjt_wire_paths``.

    BUNDLE_PLACEMENT.md section 12: the stretch of wire between two such
    tagged points runs through the bundle/transition's own rendered
    geometry and must never be drawn a second time as a bare wire
    segment -- see ``objects.objects_3d/objects_pegboard.wire.Wire.
    _segment_transforms``, the only callers (via each view's own cached
    ``_hidden_waypoint_ids``, refreshed by ``_bind_waypoints``, never
    recomputed per frame). The entry/exit guard points bracketing that
    stretch (``handlers.wire_routing_handler``'s own guard waypoints)
    carry neither tag, so the open-air stub segment on their outward
    side stays visible.
    """
    rows = ptables.pjt_wire_paths_table.for_wire(wire_id, view)

    hidden = set()
    for row in rows:
        if row.bundle_id is not None or row.transition_id is not None:
            hidden.add(row.point_id)

    return hidden


@_check_types.do
def _refresh_housing_tables(wires: list[_wire.Wire]) -> None:
    """Tell the peg-board wire table of every housing a terminal on the ends of *wires* is seated in that its wires changed.

    A housing's table bakes in the ids of the wires on it; a wire that was split or merged is a row that is gone, and the table
    would show it (and fail when it is picked) until it requeries. Only the call site that changed the membership can say which
    tables are affected (see ``objects_pegboard.base_pegboard.notify_table_wires_changed``).
    """
    from ..objects.objects_pegboard import base_pegboard as _base_pegboard  # NOQA -- avoid a cycle at import time

    done = []

    for wire in wires:
        for sibling in (wire.start_sibling, wire.stop_sibling):
            if sibling is None or not sibling.is_terminal:
                continue

            cavity_db = sibling.db_obj.cavity

            if cavity_db is None:
                continue

            cavity_obj = cavity_db.get_object()

            if cavity_obj is None or cavity_obj.housing is None:
                continue

            housing_db = cavity_obj.housing.db_obj

            if any(housing_db is other for other in done):
                continue

            done.append(housing_db)
            _base_pegboard.notify_table_wires_changed(housing_db)


@_check_types.do
def _board_ends(ptables: "_ProjectTables", wire_db: object) -> tuple[bytes, bytes] | None:
    """The ids of *wire_db*'s two peg-board end points, or ``None`` when it has no board geometry (read without the lazy creation
    of a missing point at the origin that the row's own ``start_position_pegboard_id`` does)."""
    rows = ptables.pjt_wires_table.select(
        'start_point_pegboard_id', 'stop_point_pegboard_id', id=wire_db.db_id)

    if not rows or rows[0][0] is None or rows[0][1] is None:
        return None

    return rows[0][0], rows[0][1]


@_check_types.do
def _split_board(
    ptables: "_ProjectTables", orig: object, wire: _wire.Wire, coord_point: object, split_idx: int,
    board_ends: tuple[bytes, bytes],
) -> tuple[bytes, list[bytes], list[bytes]]:
    """Where a wire's board route is cut when the wire is split at *coord_point* in 3D: at the same fraction of the route's length.

    :returns: ``(cut_point_id, waypoint_ids_before, waypoint_ids_after)``; the cut is a new peg-board point both halves share (as
        they share the 3D one), and the board waypoints are divided the way the 3D ones are (the ones before the cut segment go
        to the first half).
    """
    points3d = [wire.obj3d.start_position.as_numpy]
    points3d.extend(wp.point.as_numpy for wp in orig.waypoints3d)
    points3d.append(wire.obj3d.stop_position.as_numpy)

    lengths3d = [float(np.linalg.norm(b - a)) for a, b in zip(points3d, points3d[1:])]
    total3d = sum(lengths3d)

    fraction = 0.5
    if total3d > 1e-9:
        a = points3d[split_idx]
        segment = points3d[split_idx + 1] - a
        segment_sq = float(np.dot(segment, segment))
        t = 0.0

        if segment_sq > 1e-12:
            t = max(0.0, min(1.0, float(np.dot(coord_point.point.as_numpy - a, segment)) / segment_sq))

        fraction = (sum(lengths3d[:split_idx]) + t * lengths3d[split_idx]) / total3d

    board_points = ptables.pjt_points_pegboard_table
    waypoints = orig.waypoints_pegboard
    points = [board_points[board_ends[0]].point.as_numpy]
    points.extend(wp.point.as_numpy for wp in waypoints)
    points.append(board_points[board_ends[1]].point.as_numpy)

    lengths = [float(np.linalg.norm(b - a)) for a, b in zip(points, points[1:])]
    remaining = fraction * sum(lengths)
    index = len(lengths) - 1

    for i, length in enumerate(lengths):
        if remaining <= length or i == len(lengths) - 1:
            index = i
            break

        remaining -= length

    a = points[index]
    segment = points[index + 1] - a
    t = 0.0

    if lengths[index] > 1e-9:
        t = max(0.0, min(1.0, remaining / lengths[index]))

    position = a + segment * t
    cut = board_points.insert(float(position[0]), float(position[1]), float(position[2]))

    return cut.db_id, [wp.db_id for wp in waypoints[:index]], [wp.db_id for wp in waypoints[index:]]


@_check_types.do
def split_wire_at_point(
    project: "_project.Project",
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

    # The lead of a cable's conductor is split too: BOTH halves stay that conductor's wire (its colour, size and resistance come from
    # the conductor through this id). The lead proper is still the half that ends on the split plane, the conductor's junction.
    conductor_id = orig.cable_conductor_id

    start_id_3d = wire.obj3d.start_position.db_id[:-2]
    stop_id_3d = wire.obj3d.stop_position.db_id[:-2]
    start_id_2d = orig.start_position2d_id
    stop_id_2d = orig.stop_position2d_id

    coord_point = ptables.pjt_points3d_table[coord_id_3d]
    split_idx = segment_index(wire, coord_point.point.as_numpy)

    waypoints3d = orig.waypoints3d
    before_3d = waypoints3d[:split_idx]
    after_3d = waypoints3d[split_idx:]

    waypoints2d = orig.waypoints2d
    split_idx_2d = min(split_idx, len(waypoints2d))
    before_2d = waypoints2d[:split_idx_2d]
    after_2d = waypoints2d[split_idx_2d:]

    coord_id_2d_before = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0).db_id
    coord_id_2d_after = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0).db_id

    orig_start_sibling = wire.start_sibling
    orig_stop_sibling = wire.stop_sibling

    # A wire that is on the board is cut there too, at the same fraction of its length: a half with no board end points would be
    # given them at the board's origin, a wire nobody can see.
    board_ends = _board_ends(ptables, orig)
    board_cut = None

    if board_ends is not None:
        board_cut = _split_board(ptables, orig, wire, coord_point, split_idx, board_ends)

    wire1_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, coord_id_3d,
        start_id_2d, coord_id_2d_before,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire, cable_conductor_id=conductor_id)

    wire2_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        coord_id_3d, stop_id_3d,
        coord_id_2d_after, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire, cable_conductor_id=conductor_id)

    # Both halves keep the temperature the wire worked in.
    operating_temp = orig.operating_temp
    if operating_temp is not None:
        wire1_db.operating_temp = operating_temp
        wire2_db.operating_temp = operating_temp

    paths_table = ptables.pjt_wire_paths_table
    paths_table.set_route(wire1_db.db_id, '3d', [wp.db_id for wp in before_3d])
    paths_table.set_route(wire2_db.db_id, '3d', [wp.db_id for wp in after_3d])
    paths_table.set_route(wire1_db.db_id, '2d', [wp.db_id for wp in before_2d])
    paths_table.set_route(wire2_db.db_id, '2d', [wp.db_id for wp in after_2d])

    if board_cut is not None:
        cut_id, before_board, after_board = board_cut

        wire1_db.start_position_pegboard_id = board_ends[0]
        wire1_db.stop_position_pegboard_id = cut_id
        wire2_db.start_position_pegboard_id = cut_id
        wire2_db.stop_position_pegboard_id = board_ends[1]

        paths_table.set_route(wire1_db.db_id, 'pegboard', before_board)
        paths_table.set_route(wire2_db.db_id, 'pegboard', after_board)

    # The waypoints now belong to the two new wires; take them out of the
    # original's own route so its delete() finds nothing of its own to
    # clean up (see PJTWire.delete's WireLayout sweep over its waypoints).
    paths_table.delete_for_wire(orig.db_id)

    wire1_obj = _wire.Wire(mainframe, wire1_db)
    wire2_obj = _wire.Wire(mainframe, wire2_db)

    if orig_start_sibling is not None:
        wire1_obj.set_sibling(orig_start_sibling, wire1_obj.obj3d.start_position)
        orig_start_sibling.replace_wire(wire, wire1_obj)
    if orig_stop_sibling is not None:
        wire2_obj.set_sibling(orig_stop_sibling, wire2_obj.obj3d.stop_position)
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

    _refresh_housing_tables([wire1_obj, wire2_obj])

    return wire1_obj, wire2_obj


@_check_types.do
def merge_wires(
    project: "_project.Project",
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

    start_id_3d = wire_before.obj3d.start_position.db_id[:-2]
    stop_id_3d = wire_after.obj3d.stop_position.db_id[:-2]
    start_id_2d = wire_before.db_obj.start_position2d_id
    stop_id_2d = wire_after.db_obj.stop_position2d_id

    before_waypoints3d = wire_before.db_obj.waypoints3d
    after_waypoints3d = wire_after.db_obj.waypoints3d
    before_waypoints2d = wire_before.db_obj.waypoints2d
    after_waypoints2d = wire_after.db_obj.waypoints2d

    orig_start_sibling = wire_before.start_sibling
    orig_stop_sibling = wire_after.stop_sibling

    before_board = _board_ends(ptables, wire_before.db_obj)
    after_board = _board_ends(ptables, wire_after.db_obj)
    board_waypoints = None

    if before_board is not None and after_board is not None:
        board_waypoints = (
            [wp.db_id for wp in wire_before.db_obj.waypoints_pegboard]
            + [wp.db_id for wp in wire_after.db_obj.waypoints_pegboard])

    # Two halves of a cable conductor's lead (a splice or service loop in it was deleted) are one wire of that conductor again.
    conductor_id = wire_before.db_obj.cable_conductor_id
    if conductor_id is None:
        conductor_id = wire_after.db_obj.cable_conductor_id

    merged_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, stop_id_3d,
        start_id_2d, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire, cable_conductor_id=conductor_id)

    # The merged wire works in the temperature the first half worked in, or
    # else the second's.
    operating_temp = wire_before.db_obj.operating_temp
    if operating_temp is None:
        operating_temp = wire_after.db_obj.operating_temp

    if operating_temp is not None:
        merged_db.operating_temp = operating_temp

    paths_table = ptables.pjt_wire_paths_table
    paths_table.set_route(
        merged_db.db_id, '3d',
        [wp.db_id for wp in before_waypoints3d] + [wp.db_id for wp in after_waypoints3d])
    paths_table.set_route(
        merged_db.db_id, '2d',
        [wp.db_id for wp in before_waypoints2d] + [wp.db_id for wp in after_waypoints2d])

    if board_waypoints is not None:
        merged_db.start_position_pegboard_id = before_board[0]
        merged_db.stop_position_pegboard_id = after_board[1]
        paths_table.set_route(merged_db.db_id, 'pegboard', board_waypoints)

    # The waypoints now belong to the merged wire; take them out of both
    # originals' routes so their delete() finds nothing of its own to
    # clean up (see PJTWire.delete's WireLayout sweep over its waypoints).
    paths_table.delete_for_wire(wire_before.db_obj.db_id)
    paths_table.delete_for_wire(wire_after.db_obj.db_id)

    merged_obj = _wire.Wire(mainframe, merged_db)

    if orig_start_sibling is not None:
        merged_obj.set_sibling(orig_start_sibling, merged_obj.obj3d.start_position)
        orig_start_sibling.replace_wire(wire_before, merged_obj)
    if orig_stop_sibling is not None:
        merged_obj.set_sibling(orig_stop_sibling, merged_obj.obj3d.stop_position)
        orig_stop_sibling.replace_wire(wire_after, merged_obj)

    project.add_wire(merged_obj)

    before_id = wire_before.db_obj.db_id
    after_id = wire_after.db_obj.db_id

    for marker in project.wire_markers:
        if marker.db_obj.wire_id not in (before_id, after_id):
            continue

        marker.db_obj.wire_id = merged_db.db_id
        marker.obj3d.rebind_wire(merged_db)

    # Waypoints from both originals have already been moved onto
    # merged_db above, so each delete() finds nothing left of its own to
    # clean up (see Wire.delete's waypoint-cleanup loop).
    for w in (wire_before, wire_after):
        if mainframe.get_selected() is w:
            w.set_selected(False)
        w.delete()

    _refresh_housing_tables([merged_obj])

    return merged_obj


@_check_types.do
def merge_wires_in_place(
    project: "_project.Project",
    wire_before: _wire.Wire,
    wire_after: _wire.Wire,
) -> _wire.Wire:
    """Merge *wire_after* into *wire_before* and return *wire_before*.

    Same result as :func:`merge_wires` (one wire from *wire_before*'s own start to
    *wire_after*'s own stop, *wire_before*'s waypoints followed by *wire_after*'s), but
    no new row is made: *wire_before* keeps its row, its object and whatever refers to
    it, takes *wire_after*'s stop point ids in every view and rebinds its live stop
    ends to them, and *wire_after*'s route rows are moved onto it (the row's ``wire_id``
    and ``idx`` change; its bundle/transition tags stay). *wire_after*'s markers and
    whatever its far end is attached to follow, then the emptied *wire_after* is
    deleted.

    No point row is deleted. The two points the wires met at (*wire_before*'s old stop
    and *wire_after*'s old start) simply stop being used by either wire; they, and
    every point the merged wire still uses, are shared with whatever else refers to
    them. A wire service loop's own two points are these.

    *wire_before* is the wire whose stop is at the junction and *wire_after* the one whose
    start is: the order they run along the original wire. Peg-board geometry is merged
    only when both wires have it at both ends.
    """
    from ..wire_routing import reroute as _wire_reroute  # NOQA -- avoid a cycle at import time

    ptables = project.ptables
    mainframe = project.mainframe
    paths_table = ptables.pjt_wire_paths_table

    before_db = wire_before.db_obj
    after_db = wire_after.db_obj
    before_id = before_db.db_id
    after_id = after_db.db_id

    pegboard = (
        before_db.start_position_pegboard_id is not None
        and before_db.stop_position_pegboard_id is not None
        and after_db.start_position_pegboard_id is not None
        and after_db.stop_position_pegboard_id is not None)

    views = ['3d', '2d']
    if pegboard:
        views.append('pegboard')

    # Whatever wire_after's far end is attached to takes over wire_before's new
    # stop end (None for a dangling one, which clears the loop that was there).
    far_sibling = wire_after.stop_sibling

    # wire_after's route continues wire_before's: each row is handed over as it is,
    # numbered on from the end of wire_before's.
    for view in views:
        end = len(paths_table.for_wire(before_id, view))

        for offset, row in enumerate(paths_table.for_wire(after_id, view)):
            row.wire_id = before_id
            row.idx = end + offset

    far_3d = after_db.stop_position3d_id
    before_db.stop_position3d_id = far_3d
    wire_before.obj3d.set_stop_position(ptables.pjt_points3d_table[far_3d].point)

    if pegboard:
        far_pegboard = after_db.stop_position_pegboard_id
        before_db.stop_position_pegboard_id = far_pegboard
        wire_before.objpegboard.set_stop_position(ptables.pjt_points_pegboard_table[far_pegboard].point)

    # A free far end has no schematic point.
    far_2d = after_db.stop_position2d_id
    if far_2d is not None:
        before_db.stop_position2d_id = far_2d
        wire_before.objschematic.set_stop_position(ptables.pjt_points2d_table[far_2d].point)

    wire_before.set_sibling(far_sibling, wire_before.obj3d.stop_position)
    if far_sibling is not None:
        far_sibling.replace_wire(wire_after, wire_before)

    for marker in project.wire_markers:
        if marker.db_obj.wire_id == after_id:
            marker.db_obj.wire_id = before_id
            marker.obj3d.rebind_wire(before_db)

    # Its route rows and markers have all been moved, so its own delete() finds nothing
    # of theirs left to clean up (see PJTWire.delete).
    if mainframe.get_selected() is wire_after:
        wire_after.set_selected(False)
    wire_after.delete()

    wire_before.obj3d.refresh_waypoints()
    if pegboard:
        wire_before.objpegboard.refresh_waypoints()

    _refresh_housing_tables([wire_before])

    _wire_reroute.on_wire_attached(project, wire_before)

    return wire_before
