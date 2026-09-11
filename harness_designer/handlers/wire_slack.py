# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Automatic wire-length slack between the 3D and peg-board views.

The 3D view is the source of truth for a wire's real physical length --
``PJTWire.length_mm`` is derived live from its real 3D path. A wire drawn
(fully or partly) from the peg-board view still needs its 3D and
peg-board paths to agree on that one real length, without ever asking
the user to hand-tune either side to match the other (they'd never get
the two distances to line up exactly by eye):

- If the peg-board's own straight-line distance between a wire's two
  endpoints is *longer* than what the 3D path naturally comes out to,
  the 3D path doesn't have enough real length to reach that far -- a
  single waypoint gets bowed into the 3D path (see
  :meth:`~harness_designer.geometry.line.Line.bow_midpoint`) just far
  enough that its new real length matches the peg-board distance.
- If the 3D path is *longer* than the peg-board's straight-line
  distance, the wire has real length left over that the peg-board's
  straight line isn't using -- the same bow is applied on the
  peg-board side instead, so the peg-board rendering visibly uses up
  that slack instead of just showing a plain straight line shorter
  than the wire's own real length.

Only one side ever gets a waypoint out of this -- whichever view's
straight-line distance is shorter. The longer view's own distance
becomes ``length_mm`` outright, needing no waypoint at all. This runs
once, right after a wire's two real endpoints are both known (see
``add_handlers.editor_pegboard.wire``) -- it is not a continuous
constraint-solver: any *later* peg-board dragging is already kept
within whatever ``length_mm`` this settles on by the existing
per-segment length-budget clamp
(``objects_pegboard.chain_edges.touching_edges``, used by
``drag_handlers.editor_pegboard``).
"""

from typing import TYPE_CHECKING

from ..geometry import line as _line
from ..objects import wire_layout as _wire_layout
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import wire as _wire


@_check_types.do
def reconcile(mainframe: "_ui.MainFrame", wire_obj: "_wire.Wire") -> None:
    """Bow whichever of *wire_obj*'s two view-paths is shorter so its
    length matches the other -- see the module docstring.

    Call once, right after both of *wire_obj*'s real endpoints (3D and
    peg-board) are known/attached.
    """
    db_obj = wire_obj.db_obj

    line3d = _line.Line(db_obj.start_position3d, db_obj.stop_position3d)
    line_peg = _line.Line(db_obj.start_position_pegboard, db_obj.stop_position_pegboard)

    d3d = line3d.length()
    dpeg = line_peg.length()

    if dpeg > d3d:
        _add_waypoint_3d(mainframe, wire_obj, line3d, dpeg)
    elif d3d > dpeg:
        _add_waypoint_pegboard(mainframe, wire_obj, line_peg, d3d)


@_check_types.do
def _add_waypoint_3d(mainframe: "_ui.MainFrame", wire_obj: "_wire.Wire",
                     line3d: _line.Line, target_length: float) -> None:
    """Bow a single 3D waypoint into *wire_obj*'s path so its real
    length reaches *target_length* (the peg-board's own straight-line
    distance, which the natural 3D distance alone fell short of).
    """
    waypoint = line3d.bow_midpoint(target_length)
    if waypoint is None:
        return

    ptables = mainframe.project.ptables

    point_db = ptables.pjt_points3d_table.insert(
        float(waypoint.x), float(waypoint.y), float(waypoint.z))
    point_db.wire_id = wire_obj.db_obj.db_id
    point_db.idx = 0

    layout_db = ptables.pjt_wire_layouts_table.insert(point3d_id=point_db.db_id)
    layout_obj = _wire_layout.WireLayout(mainframe, layout_db)
    mainframe.project.add_wire_layout(layout_obj)

    wire_obj.obj3d.refresh_waypoints()


@_check_types.do
def _add_waypoint_pegboard(mainframe: "_ui.MainFrame", wire_obj: "_wire.Wire",
                           line_peg: _line.Line, target_length: float) -> None:
    """Bow a single peg-board waypoint into *wire_obj*'s path so its
    peg-board rendering uses up the real length left over after the 3D
    path already settled *target_length* (the 3D view's own straight-
    line distance, longer than the peg-board's).

    ``bow_midpoint``'s perpendicular offset (``cross(world_up,
    direction)``) is exactly in-plane for two points that already share
    Y (both peg-board endpoints do), so the returned waypoint's own Y
    comes out at exactly 0.0 with no separate flattening step needed.
    """
    waypoint = line_peg.bow_midpoint(target_length)
    if waypoint is None:
        return

    ptables = mainframe.project.ptables

    point_db = ptables.pjt_points_pegboard_table.insert(
        float(waypoint.x), float(waypoint.y), float(waypoint.z))
    point_db.wire_id = wire_obj.db_obj.db_id
    point_db.idx = 0

    layout_db = ptables.pjt_wire_layouts_table.insert(point_pegboard_id=point_db.db_id)
    layout_obj = _wire_layout.WireLayout(mainframe, layout_db)
    mainframe.project.add_wire_layout(layout_obj)

    wire_obj.objpegboard.refresh_waypoints()
