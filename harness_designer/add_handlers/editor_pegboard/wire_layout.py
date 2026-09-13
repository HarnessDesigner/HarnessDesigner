# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive wire-waypoint placement for the pegboard editor.

Mirrors ``add_handlers.editor_3d.wire_layout`` -- started from the
target wire's own "Add Waypoint" context-menu action
(``objects_pegboard.wire.WireMenu.on_add_waypoint``), pinned to that
one wire for the whole session. Plain left-click-drag on a wire's own
rendered strand already does segment-dragging (see
``objects_pegboard.wire.Wire.handle_interaction``), so unlike the 3D/
schematic editors this session is reached only through the context
menu, never a bare click -- see ``ui.mainframe._on_obj_right_click_
pegboard``.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ...objects import wire as _wire
    from ...objects import wire_layout as _wire_layout_facade


_SNAP_THRESHOLD_MM = 5.0


@_check_types.do
def closest_point_on_chain(wire_or_bundle, world_pos: np.ndarray):
    """Closest point on *wire_or_bundle*'s own pegboard chain
    (``objpegboard._segments()``) to *world_pos* -- returns
    ``(position, is_at_endpoint, endpoint)``, same shape as
    ``objects_3d.mixins.wire_type.WireTypeMixin.get_closest_endpoint``.
    """
    objpegboard = wire_or_bundle.objpegboard
    segments = objpegboard._segments()  # NOQA

    best_point = None
    best_dist = math.inf

    for p1, p2 in segments:
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-12:
            continue

        t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
        candidate = p1 + t * seg
        dist = float(np.sum((world_pos - candidate) ** 2))

        if dist < best_dist:
            best_dist = dist
            best_point = candidate

    if best_point is None:
        best_point = objpegboard.start_position.as_numpy

    p1 = objpegboard.start_position.as_numpy
    p2 = objpegboard.stop_position.as_numpy

    if float(np.linalg.norm(best_point - p1)) < _SNAP_THRESHOLD_MM:
        return p1, True, 'start'

    if float(np.linalg.norm(best_point - p2)) < _SNAP_THRESHOLD_MM:
        return p2, True, 'stop'

    return best_point, False, None


@_check_types.do
def segment_insertion_index(wire_or_bundle, world_pos: np.ndarray) -> int:
    """Which sub-segment of *wire_or_bundle*'s own pegboard chain
    (``objpegboard._segments()``) *world_pos* falls closest to --
    equivalently, how many of its existing interior peg-board waypoints
    come before a new one inserted there. Peg-board-chain equivalent of
    ``handlers.wire_layout_handler._find_insertion_index``, which walks
    the wire's 3D path instead -- this view has its own, independent
    waypoint set (see ``PJTWire.waypoints_pegboard``'s own docstring),
    so the insertion index has to come from this view's own geometry,
    not the 3D one.
    """
    objpegboard = wire_or_bundle.objpegboard
    segments = objpegboard._segments()  # NOQA

    best_idx = 0
    best_dist = math.inf

    for i, (p1, p2) in enumerate(segments):
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-12:
            continue

        t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
        closest = p1 + t * seg
        dist = float(np.sum((world_pos - closest) ** 2))

        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


@_check_types.do
def create_wire_layout_on_wire_pegboard(
    project, wire: "_wire.Wire", position: _point.Point, insert_idx: int
) -> "_wire_layout_facade.WireLayout":
    """Insert a new interior peg-board waypoint into *wire*'s own
    peg-board path at *position* and mark it with a WireLayout --
    peg-board equivalent of ``handlers.wire_layout_handler.
    _create_wire_layout_on_wire``, against ``pjt_points_pegboard``
    instead of ``pjt_points3d``.

    A ``PJTWireLayout`` row is exclusive to exactly one view (see that
    class's own docstring) and "a layout gets added ... specific to the
    view it was added in" (explicit direction) -- so this never reuses
    or maps onto the wire's 3D chord the way an earlier version of this
    module's own ``_finalize`` did; the new row gets its own peg-board-
    only point, with no ``position3d``/``position2d`` counterpart at
    all.
    """
    from ...objects import wire_layout as _wire_layout_facade  # NOQA -- avoid a cycle at import time

    ptables = project.ptables

    existing = wire.db_obj.waypoints_pegboard
    for waypoint in reversed(existing[insert_idx:]):
        waypoint.idx = waypoint.idx + 1

    pos_db = ptables.pjt_points_pegboard_table.insert(
        float(position.x), 0.0, float(position.z),
        wire_id=wire.db_obj.db_id, idx=insert_idx)

    db_obj = ptables.pjt_wire_layouts_table.insert(point_pegboard_id=pos_db.db_id)

    layout_obj = _wire_layout_facade.WireLayout(project.mainframe, db_obj)
    project.add_wire_layout(layout_obj)

    wire.objpegboard.refresh_waypoints()

    return layout_obj


class WireLayout(_base.AddHandlerBase):
    """Interactive wire-waypoint placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", wire: "_wire.Wire"
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera
        self._wire = wire
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
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
    def hover(self, mouse_pos: _point.Point) -> None:
        world_pos = self.camera.screen_to_world(mouse_pos)
        raw_pos, _is_at_endpoint, _endpoint = closest_point_on_chain(
            self._wire, world_pos.as_numpy)

        pos = self.target.objpegboard.position
        pos += _point.Point(*raw_pos.tolist()) - pos

        self.target.objpegboard.is_visible = True

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        world_pos = self.camera.screen_to_world(mouse_pos)
        raw_pos, is_at_endpoint, endpoint = closest_point_on_chain(
            self._wire, world_pos.as_numpy)

        if is_at_endpoint:
            if endpoint == 'start':
                self._wire.objpegboard.start_position.attach(self.target.objpegboard.position)
            else:
                self._wire.objpegboard.stop_position.attach(self.target.objpegboard.position)

            self.target.db_obj.position_pegboard_id = self.target.objpegboard.position.db_id[:-2]
            self.target.objpegboard.is_visible = True
            self.mainframe.project.add_wire_layout(self.target)
        else:
            # A new interior waypoint gets its own peg-board-only point
            # (see create_wire_layout_on_wire_pegboard's own docstring --
            # "a layout gets added ... specific to the view it was added
            # in", explicit direction) -- never the wire's 3D chord the
            # way an earlier version of this branch mapped onto.
            insert_idx = segment_insertion_index(self._wire, raw_pos)

            self.target.delete()

            new_obj = create_wire_layout_on_wire_pegboard(
                self.mainframe.project, self._wire,
                _point.Point(*raw_pos.tolist()), insert_idx)

            new_obj.objpegboard.is_visible = True

            self.target = new_obj

        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
