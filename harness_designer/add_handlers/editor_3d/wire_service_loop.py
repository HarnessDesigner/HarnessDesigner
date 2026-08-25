# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Fixed-wire service-loop placement for the 3D editor.

Ported from ``handlers.wire_service_loop_handler.AddWireServiceLoopHandler``
-- started only from a wire segment's own context menu, never a toolbar
tool, and the wire is fixed for the life of the session (no picking, no
re-snapping to a different wire mid-placement): the wire is cut live the
moment the session starts (see ``objects.objects_3d.wire_service_loop.
WireServiceLoop.start_add``'s own ``_split_wire_for_loop``), before this
class ever exists, so unlike Splice/Bundle/Transition there is no
placeholder-preview phase here at all -- the real, already-split preview
is the target from the start.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from ...handlers import wire_topology as _wire_topology
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...objects import wire as _wire
    from ...objects import wire_layout as _wire_layout


class SplitState:
    """Snapshot of the wire that's been split to make room for the loop --
    see handlers.wire_service_loop_handler._SplitState, ported verbatim.
    """
    wire1: "_wire.Wire" = None
    wire2: "_wire.Wire" = None
    layout1: "_wire_layout.WireLayout" = None
    layout2: "_wire_layout.WireLayout" = None
    line: _line.Line = None


@_check_types.do
def wire_segments(wire: "_wire.Wire"):
    """Every (p1, p2) sub-segment of *wire*'s current 3D path, as numpy
    arrays. Ported from handlers.wire_service_loop_handler._wire_segments."""
    points = [wire.obj3d.start_position.as_numpy]
    for waypoint in wire.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)
    points.append(wire.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


@_check_types.do
def split_wire_for_loop(
    mainframe, wire: "_wire.Wire", start_point_id, stop_point_id, seg_idx: int
) -> SplitState:
    """Cut *wire* into two pieces around a gap spanning start_point_id/
    stop_point_id, and insert a WireLayout at each cut. Ported from
    AddWireServiceLoopHandler._split_wire_for_loop."""
    from ...objects import wire_layout as _wire_layout_facade

    project = mainframe.project
    ptables = project.ptables

    state = SplitState()
    seg_p1, seg_p2 = wire_segments(wire)[seg_idx]
    state.line = _line.Line(_point.Point(*seg_p1), _point.Point(*seg_p2))

    wire_b, wire_a = _wire_topology.split_wire_at_point(project, wire, start_point_id)
    wire_d, wire_c = _wire_topology.split_wire_at_point(project, wire_b, stop_point_id)

    if mainframe.get_selected() is wire_c:
        wire_c.set_selected(False)
    wire_c.delete()

    state.wire1, state.wire2 = wire_a, wire_d

    layout1_db = ptables.pjt_wire_layouts_table.insert(start_point_id)
    layout2_db = ptables.pjt_wire_layouts_table.insert(stop_point_id)
    state.layout1 = _wire_layout_facade.WireLayout(mainframe, layout1_db)
    state.layout2 = _wire_layout_facade.WireLayout(mainframe, layout2_db)
    project.add_wire_layout(state.layout1)
    project.add_wire_layout(state.layout2)

    return state


@_check_types.do
def restore_wire_from_split(mainframe, state: SplitState) -> None:
    """Reverse split_wire_for_loop. Ported from
    AddWireServiceLoopHandler._restore_wire_from_split."""
    project = mainframe.project

    for layout_obj in (state.layout1, state.layout2):
        layout_obj.delete()

    _wire_topology.merge_wires(project, state.wire1, state.wire2)

    for wire_obj in (state.wire1, state.wire2):
        if mainframe.get_selected() is wire_obj:
            wire_obj.set_selected(False)
        wire_obj.delete()


class WireServiceLoop(_base.AddHandlerBase):
    """Fixed-wire service-loop placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", split_state: SplitState
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._split_state = split_state
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def _closest_point_on_line(self, line: _line.Line, mouse_pos: _point.Point):
        """Pin the hover position to *line* instead of the (already-split)
        wire's own endpoints -- see the original handler's own docstring
        for why: wire1's stop / wire2's start IS the loop's own
        live-dragged point, so projecting against them directly would
        feed the drag position back into its own input every frame.
        """
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        position = line.project_to_line(world_pos)

        p1 = line.p1.as_numpy
        p2 = line.p2.as_numpy
        direction = p2 - p1
        length = np.linalg.norm(direction)

        if length < 0.001:
            return None, None

        direction = direction / length
        wire_angle = _angle.Angle.from_direction(direction)

        return position, wire_angle

    @_check_types.do
    def _update_preview(self, position: _point.Point) -> None:
        if self.target is None:
            return

        start_p = self.target.obj3d.start_position
        start_p += position - start_p

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        if self._split_state is None or self.target is None:
            return

        position, wire_angle = self._closest_point_on_line(self._split_state.line, mouse_pos)
        if position is None or wire_angle is None:
            return

        with self.mainframe.editor3d.context:
            self._update_preview(position)

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        if self._split_state is None or self.target is None:
            return

        state = self._split_state

        position, wire_angle = self._closest_point_on_line(state.line, mouse_pos)

        if position is None or wire_angle is None:
            self._teardown_preview()
            return

        with self.mainframe.editor3d.context:
            self._update_preview(position)
            self.target.obj3d.end_move_session()

        self.target.identify(None)
        self.mainframe.project.add_wire_service_loop(self.target)
        self.target = None
        self._split_state = None

    @_check_types.do
    def _teardown_preview(self) -> None:
        if self.target is not None:
            self.target.obj3d.end_move_session()
            self.target.delete()
            self.target = None

        if self._split_state is not None:
            with self.mainframe.editor3d.context:
                restore_wire_from_split(self.mainframe, self._split_state)

            self._split_state = None

    @_check_types.do
    def cancel(self) -> None:
        self._teardown_preview()

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
