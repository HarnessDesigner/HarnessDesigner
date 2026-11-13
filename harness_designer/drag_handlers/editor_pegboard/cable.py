# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Cable in the peg-board editor: the wire's drag, for a cable.

See :mod:`~harness_designer.drag_handlers.editor_3d.cable` for what is the same as a wire's drag and what differs (a cable
never snaps, and its conductors follow). On the board the Y of every move is held at 0 as it is for a wire.

A cable's length on the board is its length in 3D when it is seeded (:meth:`~harness_designer.objects.objects_pegboard.cable.
Cable.seed_from_3d`).

**The rope pull (user, 2026-11-12):** a drag used to move the cable's points and carry the free ends of its leads along, so a lead
with a terminal (a housing) on its far end was simply stretched, as long as the drag went on. Now, while the rope pull is on
(:func:`~harness_designer.handlers.rope_pull_handler.is_enabled`), the dragged points and, for a split end, the whole end (the
cable's end point, the split points and the free lead ends: ``_cable_node``) are one rigid unit moved by
:func:`~harness_designer.handlers.rope_pull_handler.resolve_rigid_move`, as a bundle's drag is: the conductors keep their lengths,
the housings and everything else on the far ends of the leads are pulled along when a lead is taut (the cascade), and the unit stops
at the farthest place the leads allow. Without the rope pull the old behaviour is kept.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...handlers import wire_drag_base as _wire_drag_base
from ...handlers import rope_pull_handler as _rope_pull_handler
from ...handlers import wire_slack_handler as _wire_slack_handler
from ...geometry import point as _point_module
from . import wire as _wire
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...geometry import point as _point
    from ...gl.canvas_pegboard import canvas_window as _canvas_window
    from ...objects import cable as _cable_object
    from ...objects import project as _project


class Cable(_wire.Wire):
    """Segment-local drag for a Cable in the peg-board editor."""

    @classmethod
    @_check_types.do
    def plan_wire_drag(cls, project: "_project.Project", wire_obj: "_cable_object.Cable",
                       mouse_pos: "_point.Point") -> "_wire_drag_base.WireDragPlan | None":
        """What a click on the cable's body at *mouse_pos* drags: the wire's plan, without the snap.

        :param project: The project.
        :param wire_obj: The cable.
        :param mouse_pos: Where the mouse went down.
        :returns: The plan, or ``None`` when nothing at the click can be dragged.
        """
        plan = super().plan_wire_drag(project, wire_obj, mouse_pos)

        if plan is not None:
            plan.snap_point = None

        return plan

    @classmethod
    @_check_types.do
    def _route_locked_point_ids(cls, project: "_project.Project", wire_obj: "_cable_object.Cable") -> set[bytes]:
        """No point of a cable is held by a bundle or transition (a cable is not routed through them), so none is locked.

        :param project: The project.
        :param wire_obj: The cable.
        """
        return set()

    @_check_types.do
    def __init__(self, canvas: "_canvas_window.CanvasWindow", target: "_cable_object.Cable",  # NOQA
                 plan: "_wire_drag_base.WireDragPlan"):
        _wire.Wire.__init__(self, canvas, target, plan)

        # The rope pull: every board point this drag moves, each at its own place when the drag began (see the module docstring)
        self._rope_starts: list[tuple[bytes, object]] = []
        self._rope_points: list = []
        self._rope_rows: list = []  # the rows stay referenced: a point's write-back to its row is a weak callback
        self._rope_full = (0.0, 0.0)
        self._rope_applied = (0.0, 0.0)

        if _rope_pull_handler.is_enabled():
            self._rope_collect(plan)

    @_check_types.do
    def _rope_collect(self, plan: "_wire_drag_base.WireDragPlan") -> None:
        """List the points that move as one unit: the points of the plan and, for a point that is the cable's end (or one of the end's
        split points / free lead ends), the whole end with it."""
        ptables = self.canvas.mainframe.project.ptables
        table = ptables.pjt_points_pegboard_table
        seen: set[bytes] = set()

        def add(point_id: bytes, point: object) -> None:
            if point_id in seen:
                return

            seen.add(point_id)
            self._rope_starts.append((point_id, point.copy()))
            self._rope_points.append(point)

        for point in plan.moving:
            point_id = point.db_id[:-2]
            add(point_id, point)

            node = _rope_pull_handler._cable_node(ptables, point_id)  # NOQA

            if node is None:
                continue

            for other_id in node[1]:
                row = table[other_id]
                self._rope_rows.append(row)
                add(other_id, row.point)

    @_check_types.do
    def __call__(self, delta: "_point.Point", mouse_pos: "_point.Point") -> None:
        """Drag the cable: its conductors keep their lengths and what is attached to them is pulled along (the rope pull), or, with the
        rope pull off, drag as the wire does and let the free conductors follow."""
        if self._rope_starts:
            self._rope_call(delta)
            return

        view = self.target.objpegboard
        before_start = np.array(view.start_position.as_numpy, dtype=np.float64)
        before_stop = np.array(view.stop_position.as_numpy, dtype=np.float64)

        _wire.Wire.__call__(self, delta, mouse_pos)

        self.target.follow_drag('pegboard', before_start, before_stop)

    @_check_types.do
    def _rope_call(self, delta: "_point.Point") -> None:
        """One frame of the rope-pull drag: the total the mouse has moved since the drag began is resolved against every chain the unit
        touches (:func:`~harness_designer.handlers.rope_pull_handler.resolve_rigid_move`: the farthest reachable fraction of it, the
        wires pulled along), and the unit is put there. The mouse's reference point follows the mouse, not the (possibly held back)
        unit, so a drag that was held back at a limit is not stuck there once the mouse is back inside it."""
        step = self._move_delta(self.anchor, self.last_pos, delta, self._get_view_object(self.target).aabb)

        if step is None:
            return

        self.anchor += step
        self.last_pos = self.anchor.copy()
        self._rope_full = (self._rope_full[0] + float(step.x), self._rope_full[1] + float(step.z))

        fraction = _rope_pull_handler.resolve_rigid_move(self.canvas.mainframe, self._rope_starts, self._rope_full)
        applied = (self._rope_full[0] * fraction, self._rope_full[1] * fraction)
        self._rope_applied = applied

        # resolve_rigid_move already reconciled every chain these points touch: moving the points one by one must not reconcile again
        _wire_slack_handler.WireSlackHandler._reconciling_any = True  # NOQA

        try:
            for (_point_id, start), point in zip(self._rope_starts, self._rope_points):
                point += _point_module.Point(
                    float(start.x) + applied[0] - float(point.x), 0.0, float(start.z) + applied[1] - float(point.z))
        finally:
            _wire_slack_handler.WireSlackHandler._reconciling_any = False  # NOQA

        # the split points lie on the trunk's split plane again (the end's segment may have turned), and a sleeve goes with them
        self.target.sync_board_split_ends()

    @_check_types.do
    def delete(self) -> None:
        """End the drag; the rope pull's last frame is the real (not overlay) reconcile, so the bends get their layouts."""
        _wire.Wire.delete(self)

        if self._rope_starts and self._rope_applied != (0.0, 0.0):
            _rope_pull_handler.resolve_rigid_move(
                self.canvas.mainframe, self._rope_starts, self._rope_applied, in_progress=False)

            self.target.sync_board_split_ends()
