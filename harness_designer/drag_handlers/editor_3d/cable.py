# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Cable in the 3D editor: the wire's drag, for a cable.

A cable is dragged as a wire is (:class:`~harness_designer.drag_handlers.editor_3d.wire.Wire`, see its module and
:mod:`~harness_designer.handlers.wire_drag_base` for the rule): a click near a free end drags that end, a click between two
waypoints drags both, and a click on a cable with no waypoints and both ends free drags the whole cable. Two things differ:

* a cable never snaps. Its ends are always free (a terminal or splice is attached to a conductor's lead, after the cable is
  split), so the plan has no snap point: no snap probes are built and nothing is committed when the mouse is released;
* the conductors follow. A conductor's end point is a child of the cable's end, so an end that is not split carries them with
  it; for a split end the split points are laid on the new split plane and the leads' free ends that nothing is attached to move
  with the cable's end (:meth:`~harness_designer.objects.cable.Cable.follow_drag`). A lead with a terminal or splice on it
  stays where it is, as an attached wire end does.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...handlers import wire_drag_base as _wire_drag_base
from . import wire as _wire
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...geometry import point as _point
    from ...gl.canvas_3d import canvas_window as _canvas_window
    from ...objects import cable as _cable_object
    from ...objects import project as _project


class Cable(_wire.Wire):
    """Segment-local drag for a Cable in the 3D editor."""

    @classmethod
    @_check_types.do
    def plan_wire_drag(cls, project: "_project.Project", wire_obj: "_cable_object.Cable",
                       mouse_pos: "_point.Point") -> "_wire_drag_base.WireDragPlan | None":
        """What a click on the cable's body at *mouse_pos* drags: the wire's plan, without the snap (a cable's ends are
        always free and it is never connected to a terminal or splice itself).

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
        view = self.target.obj3d
        before_start = np.array(view.start_position.as_numpy, dtype=np.float64)
        before_stop = np.array(view.stop_position.as_numpy, dtype=np.float64)

        _wire.Wire.__call__(self, delta, mouse_pos)

        self.target.follow_drag('3d', before_start, before_stop)
