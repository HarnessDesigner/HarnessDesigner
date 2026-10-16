# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-marker drag for the Schematic Editor.

A wire marker can only be repositioned along the wire it was added to --
enforced by the object itself (``objects.objects_schematic.wire_marker.
WireMarker._update_position``, bound to the marker's own live position),
which projects any position change back onto the wire's current line.
No gizmo (unlike the 3D editor's rotated directional-arrow) -- the
locked top-down camera makes the drag direction unambiguous, and the
object's own re-projection is the only constraint that matters.
"""

from typing import TYPE_CHECKING

from .. import editor_schematic as _editor_schematic
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class WireMarker(_editor_schematic.DragHandlerSchematic):
    """Wire-marker drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase") -> None:
        super().__init__(canvas, target)

        # Open the move gesture for this drag's whole lifetime -- see
        # drag_handlers.editor_pegboard.generic.Generic.__init__ for the
        # same hook and WRITE_DESIGN.md section 4.12. Closed in delete()
        # below. Without this, every position write this drag makes
        # hits the database immediately and individually on every frame
        # instead of deferring into the gesture's own batched flush --
        # confirmed live, 2026-10-12: this class never opened a gesture
        # at all.
        canvas.mainframe.project.begin_gesture()

    @_check_types.do
    def delete(self) -> None:
        try:
            super().delete()
        finally:
            # Close the gesture opened in __init__ -- see that method's
            # comment. Must run even if super().delete() raises, or the
            # gesture would silently stay open and defer every later
            # write app-wide until something else closes it.
            self.canvas.mainframe.project.end_gesture()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        position = self.target.objschematic.position

        world_pos = self._world_xz(mouse_pos)
        world_delta = _point.Point(
            float(world_pos.x) - float(position.x), 0.0, float(world_pos.z) - float(position.z))

        position += world_delta
