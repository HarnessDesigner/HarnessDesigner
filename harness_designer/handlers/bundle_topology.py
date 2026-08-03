# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared bundle-topology helpers.

Unlike wires, nothing forks a bundle's own row in the new waypoint model:
ordinary bends are just interior waypoints (handlers.bundle_layout_handler),
and a Transition is only a waypoint/branch marker a bundle's trunk end
terminates at -- it never splits a bundle in two. The one operation this
module still provides is the inverse of a wire-to-wire join: when two
independently-placed bundles are dragged together end-to-end, they merge
into a single row instead of staying two, mirroring handlers.wire_handler's
wire-to-wire join and handlers.wire_topology.merge_wires.
"""

from typing import TYPE_CHECKING

from ..objects import bundle as _bundle
from .. import check_types as _check_types

if TYPE_CHECKING:
    from ..objects.project import Project


@_check_types.do
def merge_bundles(
    project: "Project",
    bundle_before: _bundle.Bundle,
    bundle_after: _bundle.Bundle,
) -> _bundle.Bundle:
    """Merge two bundles touching end-to-end into a single row spanning
    *bundle_before*'s own start to *bundle_after*'s own stop.

    Concatenates both bundles' waypoint lists (*bundle_before*'s kept
    as-is, *bundle_after*'s renumbered to continue directly after),
    re-homes whatever was attached to their own outer ends (a Transition
    at *bundle_before*'s start and/or *bundle_after*'s stop) onto the
    merged bundle, and re-parents both bundles' concentric layers (the
    wires each one covers) onto a single fresh concentric for the merged
    row -- *bundle_before*'s own layers keep their index, *bundle_after*'s
    are offset to continue after them, same shape as the waypoint
    concatenation. Both original rows are deleted; returns the new
    merged bundle.
    """
    ptables = project.ptables
    mainframe = project.mainframe

    orig = bundle_before.db_obj
    part_id = orig.part_id
    name = orig.name

    start_id_3d = bundle_before.obj3d.start_position.db_id[:-2]
    stop_id_3d = bundle_after.obj3d.stop_position.db_id[:-2]

    before_waypoints3d = bundle_before.db_obj.waypoints3d
    after_waypoints3d = bundle_after.db_obj.waypoints3d

    orig_start_sibling = bundle_before.start_sibling
    orig_stop_sibling = bundle_after.stop_sibling

    merged_db = ptables.pjt_bundles_table.insert(part_id, name)
    merged_db.start_position3d_id = start_id_3d
    merged_db.stop_position3d_id = stop_id_3d

    offset_3d = len(before_waypoints3d)

    for i, wp in enumerate(before_waypoints3d):
        wp.bundle_id = merged_db.db_id
        wp.idx = i

    for i, wp in enumerate(after_waypoints3d):
        wp.bundle_id = merged_db.db_id
        wp.idx = offset_3d + i

    merged_concentric = ptables.pjt_concentrics_table.insert(merged_db.db_id,
                                                             None)

    if bundle_before.db_obj.concentric:
        before_layers = bundle_before.db_obj.concentric.layers
    else:
        before_layers = []

    if bundle_after.db_obj.concentric:
        after_layers = bundle_after.db_obj.concentric.layers
    else:
        after_layers = []

    for layer in before_layers:
        layer.concentric_id = merged_concentric.db_id

    layer_offset = len(before_layers)
    for i, layer in enumerate(after_layers):
        layer.concentric_id = merged_concentric.db_id
        layer.idx = layer_offset + i

    merged_obj = _bundle.Bundle(mainframe, merged_db)

    if orig_start_sibling is not None:
        merged_obj.set_sibling(orig_start_sibling, 'start')
        orig_start_sibling.replace_bundle(bundle_before, merged_obj)

    if orig_stop_sibling is not None:
        merged_obj.set_sibling(orig_stop_sibling, 'stop')
        orig_stop_sibling.replace_bundle(bundle_after, merged_obj)

    project.add_bundle(merged_obj)

    # Waypoints and concentric layers from both originals have already
    # been re-homed onto merged_db above, so each delete() finds nothing
    # left of its own to clean up (see PJTBundle.delete's waypoint
    # cleanup loop) -- their now-empty concentric rows are simply
    # abandoned, same as any other orphaned row this codebase doesn't
    # bother sweeping (there's no DB-enforced cascade for it either way).
    for b in (bundle_before, bundle_after):
        if mainframe.get_selected() is b:
            b.set_selected(False)

        b.delete()

    return merged_obj
