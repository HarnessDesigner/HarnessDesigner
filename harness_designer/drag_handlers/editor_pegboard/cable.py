# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Cable in the peg-board editor: the wire's drag, for a cable.

See :mod:`~harness_designer.drag_handlers.editor_3d.cable` for what is the same as a wire's drag and what differs (a cable
never snaps, and its conductors follow). On the board the Y of every move is held at 0 as it is for a wire.

A cable's length on the board is its length in 3D when it is seeded (:meth:`~harness_designer.objects.objects_pegboard.cable.
Cable.seed_from_3d`); dragging a point here changes the board's length, not the cable's, as it does for a wire (no length budget
is enforced on the board yet, see ``WireDragMixin._apply_budget_clamp``).
"""

from typing import TYPE_CHECKING

import numpy as np

from ...handlers import wire_drag_base as _wire_drag_base
from . import wire as _wire
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...geometry import point as _point
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
    def __call__(self, delta: "_point.Point", mouse_pos: "_point.Point") -> None:
        """Drag as the wire does, then let the cable's conductors follow the move."""
        view = self.target.objpegboard
        before_start = np.array(view.start_position.as_numpy, dtype=np.float64)
        before_stop = np.array(view.stop_position.as_numpy, dtype=np.float64)

        _wire.Wire.__call__(self, delta, mouse_pos)

        self.target.follow_drag('pegboard', before_start, before_stop)
