# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generic single-position drag for the 3D editor.

Applies to: housing, transition, splice, wire service loops, bundle
layouts, wire layouts -- anything whose entire position is the one thing
a drag ever needs to move (contrast :mod:`~.wire`/:mod:`~.bundle`, which
move a specific point/segment along a path instead).

Eligibility for the two starred cases below is decided on the object
itself (``can_drag()`` -- see
``harness_designer.objects.objectsvar.base_var.BaseVar``), not here:

- A bundle layout that's shared with a boot or a transition is not
  draggable.
- A wire layout that shares its position with a cavity, terminal, or
  splice is not draggable.

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.base.DragObject`
(proven, working code from before this package existed).
"""

from typing import TYPE_CHECKING

from .. import editor_3d as _editor_3d
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class Generic(_editor_3d.DragHandler3D):
    """Generic single-position drag -- moves ``obj3d.position`` directly."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        # Last object world Point used for incremental moves.
        self.last_pos = target.obj3d.position.copy()

        # Duck-typed: only WireServiceLoop3D defines this (see its own
        # begin_move_session docstring) -- caches its collision-candidate
        # list for the whole drag instead of rebuilding it on every one
        # of the many position updates a drag produces.
        if hasattr(target.obj3d, 'begin_move_session'):
            target.obj3d.begin_move_session()

    @_check_types.do
    def delete(self) -> None:
        if hasattr(self.target.obj3d, 'end_move_session'):
            self.target.obj3d.end_move_session()

        super().delete()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, part of the shared contract
        position = self.target.obj3d.position

        delta3d = self._axis_locked_delta3d(
            position, self.last_pos, delta, self.target.obj3d.aabb)
        if delta3d is None:
            return

        position += delta3d
        self.last_pos = position.copy()
