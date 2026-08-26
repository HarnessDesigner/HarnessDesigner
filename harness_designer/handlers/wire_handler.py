# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-merge/compat-lookup helpers reused by the object-owned wire
add-handlers (``add_handlers.editor_3d.wire``/``add_handlers.editor_
schematic.wire``, and ``objects.objects_3d.wire.WireMenu``'s Extend
Wire/Add to Wire actions), which replaced this module's own former
``AddWireHandler``.
"""

import numpy as np

from ..geometry import point as _point
from ..objects import wire_layout as _wire_layout
from ..objects import wire as _wire
from .. import check_types as _check_types


@_check_types.do
def _wire_layout_end_wire(wire_layout_obj, project, part_id: bytes):
    """Return (wire, endpoint) if the layout sits at one endpoint of a wire with matching part_id.

    Returns (None, None) when the layout is mid-wire (split point, two wires share it)
    or when no wire with the given part_id is attached.
    """
    if part_id is None:
        return None, None

    layout_pos_id = wire_layout_obj.db_obj.position3d_id
    matching = []

    for w in project.wires:
        if not w.is_in_3dview:
            continue

        start_str = w.obj3d.start_position.db_id
        stop_str = w.obj3d.stop_position.db_id
        if start_str and start_str[:-2] == layout_pos_id:
            matching.append((w, 'start'))

        elif stop_str and stop_str[:-2] == layout_pos_id:
            matching.append((w, 'stop'))

    if len(matching) == 1:
        w, ep = matching[0]
        if w.db_obj.part_id == part_id:
            return w, ep

    return None, None


@_check_types.do
def merge_wire_into(project, wire_obj: _wire.Wire, other_wire: _wire.Wire, other_end: str,
                     own_end: str = 'stop'):
    """Join *wire_obj*'s own dangling *own_end* ('start' or 'stop';
    default 'stop' -- the two-click preview flow's own always-growing end,
    the only case that existed before this took an own_end parameter) to
    *other_wire*'s dangling *other_end*, merging them into a single row --
    part_id must already match (checked by the caller). Also the commit
    path for a snapped wire-to-wire endpoint drag (see
    handlers.wire_snap.commit_snap) -- own_end there is whichever end was
    actually dragged, which can be either one.

    *wire_obj*'s own current *own_end* point becomes a permanent interior
    waypoint marking the seam (a WireLayout is dropped there), same as an
    ordinary bend; *other_wire*'s own waypoints follow, reversed first if
    joining to its start (so the merged chain still reads start->stop in
    one consistent direction), renumbered to continue. circuit_id is
    inherited from whichever of the two already had one set, not
    required to match. Both original rows are deleted; returns the new
    merged wire.
    """
    ptables = project.ptables
    mainframe = project.mainframe

    if own_end == 'start':
        # Mirror image of the 'stop' case below: wire_obj's own far/outer
        # end is now its stop (own_end is the seam), so its own waypoints
        # need reversing to still walk outer-end-toward-seam in the
        # merged wire's own start->stop order.
        seam_point_id = wire_obj.obj3d.start_position.db_id[:-2]
        own_waypoints = list(reversed(wire_obj.db_obj.waypoints3d))
        start_id_3d = wire_obj.obj3d.stop_position.db_id[:-2]
        start_id_2d = wire_obj.db_obj.stop_position2d_id
        orig_start_sibling = wire_obj.stop_sibling
    else:
        seam_point_id = wire_obj.obj3d.stop_position.db_id[:-2]
        own_waypoints = wire_obj.db_obj.waypoints3d
        start_id_3d = wire_obj.obj3d.start_position.db_id[:-2]
        start_id_2d = wire_obj.db_obj.start_position2d_id
        orig_start_sibling = wire_obj.start_sibling

    seam_idx = len(own_waypoints)

    part_id = wire_obj.db_obj.part_id
    name = wire_obj.db_obj.name

    circuit_id = wire_obj.db_obj.circuit_id
    if circuit_id is None:
        circuit_id = other_wire.db_obj.circuit_id

    layer_id = wire_obj.db_obj.layer_id
    layer_view_point_id = wire_obj.db_obj.layer_view_position_id
    is_filler_wire = wire_obj.db_obj.is_filler_wire
    is_visible3d = wire_obj.db_obj.is_visible3d
    is_visible2d = wire_obj.db_obj.is_visible2d

    if other_end == 'start':
        stop_id_3d = other_wire.obj3d.stop_position.db_id[:-2]
        stop_id_2d = other_wire.db_obj.stop_position2d_id
        other_waypoints = other_wire.db_obj.waypoints3d  # already start->stop order
        other_stop_sibling = other_wire.stop_sibling
    else:
        stop_id_3d = other_wire.obj3d.start_position.db_id[:-2]
        stop_id_2d = other_wire.db_obj.start_position2d_id
        other_waypoints = list(reversed(other_wire.db_obj.waypoints3d))
        other_stop_sibling = other_wire.start_sibling

    merged_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, stop_id_3d,
        start_id_2d, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire)

    for i, wp in enumerate(own_waypoints):
        wp.wire_id = merged_db.db_id
        wp.idx = i

    seam_point = ptables.pjt_points3d_table[seam_point_id]
    seam_point.wire_id = merged_db.db_id
    seam_point.idx = seam_idx

    for i, wp in enumerate(other_waypoints):
        wp.wire_id = merged_db.db_id
        wp.idx = seam_idx + 1 + i

    merged_obj = _wire.Wire(mainframe, merged_db)

    layout_db = ptables.pjt_wire_layouts_table.insert(seam_point_id)
    layout_obj = _wire_layout.WireLayout(mainframe, layout_db)
    project.add_wire_layout(layout_obj)

    if orig_start_sibling is not None:
        merged_obj.set_sibling(orig_start_sibling, 'start')
        orig_start_sibling.replace_wire(wire_obj, merged_obj)
    if other_stop_sibling is not None:
        merged_obj.set_sibling(other_stop_sibling, 'stop')
        other_stop_sibling.replace_wire(other_wire, merged_obj)

    project.add_wire(merged_obj)

    old_ids = (wire_obj.db_obj.db_id, other_wire.db_obj.db_id)
    for marker in project.wire_markers:
        if marker.db_obj.wire_id in old_ids:
            marker.db_obj.wire_id = merged_db.db_id
            marker.obj3d.rebind_wire(merged_db)

    for w in (wire_obj, other_wire):
        if mainframe.get_selected() is w:
            w.set_selected(False)
        w.delete()

    return merged_obj


@_check_types.do
def _get_terminal_compat_pns(mainframe, terminal_obj):
    """Return wire part numbers whose outer diameter fits *terminal_obj*'s crimp range."""
    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return []

    dia_min = term_part.wire_size_dia_min
    dia_max = term_part.wire_size_dia_max

    if dia_min is None and dia_max is None:
        return []

    table = mainframe.global_db.wires_table

    if dia_min is not None and dia_max is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=? AND od_mm<=?;',
            (dia_min, dia_max))
    elif dia_min is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=?;', (dia_min,))
    else:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm<=?;', (dia_max,))

    return [row[0] for row in table.fetchall()]


@_check_types.do
def _get_splice_compat_pns(mainframe, splice_obj):
    """Return wire part numbers whose outer diameter fits *splice_obj*'s crimp range."""
    splice_part = splice_obj.db_obj.part
    if splice_part is None:
        return []

    dia_min = splice_part.wire_size_dia_min
    dia_max = splice_part.wire_size_dia_max

    if dia_min is None and dia_max is None:
        return []

    table = mainframe.global_db.wires_table

    if dia_min is not None and dia_max is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=? AND od_mm<=?;',
            (dia_min, dia_max))
    elif dia_min is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=?;', (dia_min,))
    else:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm<=?;', (dia_max,))

    return [row[0] for row in table.fetchall()]


@_check_types.do
def _pick_free_end(mainframe, wire_obj: _wire.Wire, click_pos: _point.Point = None) -> str | None:
    """Return ``'start'``/``'stop'`` -- whichever end of *wire_obj* is free
    to extend/add onto (see ``objects.objects_3d.wire.WireMenu``'s Extend
    Wire/Add to Wire actions) -- or ``None`` if both ends are anchored to a
    terminal/cavity (those menu actions are disabled in that case).

    Exactly one free end wins outright; with both free, whichever is
    closer to *click_pos* (where the context menu was opened) wins, using
    the same closest-point-on-path technique
    ``drag_handlers.editor_3d.wire.plan_wire_drag`` already uses to decide
    "which end did the user mean" elsewhere.
    """
    from ..drag_handlers.editor_3d import wire as _dragging  # NOQA -- avoid a cycle at import time

    project = mainframe.project
    start_anchored, stop_anchored = _dragging.wire_end_anchors(project, wire_obj)

    if start_anchored and stop_anchored:
        return None

    if start_anchored:
        return 'stop'

    if stop_anchored:
        return 'start'

    obj3d = wire_obj.obj3d

    if click_pos is None:
        return 'stop'

    closest_point, _angle, _seg_idx = obj3d.get_closest_point(click_pos)
    if closest_point is None:
        return 'stop'

    start_dist = float(np.linalg.norm(closest_point.as_numpy - obj3d.start_position.as_numpy))
    stop_dist = float(np.linalg.norm(closest_point.as_numpy - obj3d.stop_position.as_numpy))

    return 'start' if start_dist <= stop_dist else 'stop'
