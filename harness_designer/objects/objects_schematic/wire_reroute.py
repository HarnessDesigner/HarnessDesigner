# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared "reroute one wire" transaction for the 2D schematic editor's
auto-router (see ``wire_routing.py``) -- the single choke point every
caller (initial wire finalize, live drag rerouting, the release-time
overlap sweep, Auto Arrange's full-project pass) goes through to
replace a wire's interior 2D waypoints. Owns deleting the old waypoint
rows -- and any ``WireLayout`` handle anchored to one of them, via
``database/project_db/pjt_wire.py``'s ``delete_layouts_at`` -- inserting
the newly routed ones, and refreshing the live ``Wire`` object's
bindings, so callers never touch ``pjt_points2d_table`` directly.

Also owns resolving "every wire directly attached to this object" (used
by both the live per-frame drag hook and Auto Arrange) and the cheap
release-time overlap sweep that catches a wire elsewhere in the project
left crossing an object that was just moved.
"""

from typing import TYPE_CHECKING

from . import wire_routing as _wire_routing
from ...database.project_db import pjt_wire as _pjt_wire
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import project as _project
    from .. import wire as _wire_obj
    from .. import terminal as _terminal_obj
    from .. import splice as _splice_obj
    from .. import housing as _housing_obj


@_check_types.do
def reroute_wire(project: "_project.Project", wire: "_wire_obj.Wire") -> None:
    """Recompute *wire*'s orthogonal 2D path and replace its interior
    waypoint rows (and any ``WireLayout`` anchored to one of the old
    ones) with the result -- always, even when the new path needs zero
    interior waypoints, so stale bindings never linger.
    """
    ptables = project.ptables
    db_obj = wire.db_obj

    start = db_obj.start_position2d
    stop = db_obj.stop_position2d
    od_mm = float(wire.objschematic._part.od_mm)  # NOQA

    waypoints = _wire_routing.route(
        project, (float(start.x), float(start.z)), (float(stop.x), float(stop.z)),
        ignore_wire=wire, od_mm=od_mm)

    old_waypoints = list(db_obj.waypoints2d)

    layouts_table = ptables.pjt_wire_layouts_table
    for point in old_waypoints:
        _pjt_wire.delete_layouts_at(layouts_table, 'point2d_id', point.db_id)
        point.delete()

    for i, (x, z) in enumerate(waypoints):
        ptables.pjt_points2d_table.insert(x, z, wire_id=db_obj.db_id, idx=i)

    wire.objschematic.refresh_waypoints()


@_check_types.do
def wires_attached_to(obj) -> list["_wire_obj.Wire"]:
    """Every wire directly attached to *obj* -- a ``Terminal``/``Splice``
    exposes ``.wires`` directly; a ``Housing`` has none of its own, so
    it's built from every seated terminal across its cavities (those
    already have correct live positions by the time this is called each
    drag frame -- ``objects_schematic/housing.py``'s ``Housing._update_position``/
    ``_update_angle`` cascade to every child first). Anything else
    (a bare wire segment/handle, dragged through its own dedicated
    segment-drag interaction, not this generic path) returns an empty
    list.
    """
    from .. import terminal as _terminal
    from .. import splice as _splice
    from .. import housing as _housing

    if isinstance(obj, (_terminal.Terminal, _splice.Splice)):
        return list(obj.wires)

    if isinstance(obj, _housing.Housing):
        result = []
        for cavity in obj.cavities:
            terminal = cavity.terminal
            if terminal is not None:
                result.extend(terminal.wires)
        return result

    return []


@_check_types.do
def _path_overlaps_rect(wire: "_wire_obj.Wire",
                        rect: tuple[float, float, float, float]) -> bool:
    """Cheap check: does any of *wire*'s current 2D sub-segments cross
    or run inside *rect* (``(min_x, min_z, max_x, max_z)``)? Used to
    filter which wires actually need the expensive
    :func:`reroute_wire`/A* call during :func:`sweep_for_overlaps`,
    rather than blindly rerouting every wire in the project.
    """
    min_x, min_z, max_x, max_z = rect

    for p1, p2 in wire.objschematic._segments():  # NOQA
        x1, z1 = float(p1[0]), float(p1[2])
        x2, z2 = float(p2[0]), float(p2[2])

        seg_min_x, seg_max_x = min(x1, x2), max(x1, x2)
        seg_min_z, seg_max_z = min(z1, z2), max(z1, z2)

        if seg_max_x < min_x or max_x < seg_min_x:
            continue
        if seg_max_z < min_z or max_z < seg_min_z:
            continue

        return True

    return False


@_check_types.do
def sweep_for_overlaps(project: "_project.Project", moved_obj,
                       already_rerouted: list["_wire_obj.Wire"]) -> None:
    """Run once, on drag release: for every connected wire *not* already
    live-rerouted this drag, reroute it if its current path now overlaps
    *moved_obj*'s new footprint -- a cheap AABB-vs-segment check first,
    the real (expensive) A* reroute only for wires actually violated.
    """
    bounds = moved_obj.objschematic.get_bounds()
    if bounds is None:
        return

    already = set(already_rerouted)

    for wire in project.wires:
        if wire in already or not wire.is_connected:
            continue

        if _path_overlaps_rect(wire, bounds):
            reroute_wire(project, wire)
