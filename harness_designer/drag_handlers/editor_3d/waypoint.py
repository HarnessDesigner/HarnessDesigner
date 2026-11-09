# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The 3D drag of a waypoint that has no layout object: a cable's (WAYPOINT_REWORK_DESIGN.md).

A wire's and a bundle's waypoints are dragged through the layout's data object (``generic.Generic``, which also keeps the peg-board
chains' lengths in step). A cable has no layouts at its waypoints, so its waypoint is dragged as the Point it is: moved by the same
axis-locked screen delta ``Generic`` uses, in one write gesture, the cable's own bound callbacks redrawing it as the point moves.
"""

from typing import TYPE_CHECKING

from .. import editor_3d as _editor_3d
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas_window as _canvas_window
    from ... import objects as _objects


class Waypoint(_editor_3d.DragHandler3D):
    """Drag one waypoint Point of *target* (a cable), the move-arrows gizmo sized by *arrow_object* (the cable's 3D view)."""

    @_check_types.do
    def __init__(self, canvas: "_canvas_window.CanvasWindow", target: "_objects.ObjectBase", point: _point.Point,
                 arrow_object: object):
        super().__init__(canvas, target)

        self._point = point
        self._arrow_object = arrow_object

        # A point writes its moves back to its row through a weak callback, so a move is saved only while something holds the row:
        # a cable's waypoint has no layout to hold it, so the drag does, for as long as it lasts
        self._row = canvas.mainframe.project.ptables.pjt_points3d_table[point.db_id[:-2]]
        self.last_pos = point.copy()

        # One write gesture for the whole drag (see generic.Generic.__init__). Last statement: if anything above raised, delete() is
        # never called and a gesture opened earlier would stay open.
        canvas.mainframe.project.begin_gesture()

    @_check_types.do
    def delete(self) -> None:
        try:
            super().delete()
        finally:
            self.canvas.mainframe.project.end_gesture()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, part of the shared contract
        delta3d = self._axis_locked_delta3d(self._point, self.last_pos, delta, self._arrow_object.aabb)

        if delta3d is None:
            return

        self._point += delta3d
        self.last_pos = self._point.copy()
