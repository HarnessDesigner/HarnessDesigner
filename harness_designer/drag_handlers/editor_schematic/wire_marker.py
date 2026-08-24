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

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        position = self.target.objschematic.position

        world_pos = self._world_xz(mouse_pos)
        world_delta = _point.Point(
            float(world_pos.x) - float(position.x), 0.0, float(world_pos.z) - float(position.z))

        position += world_delta
