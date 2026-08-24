# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared locked-plane mechanics for every 2D Schematic Editor drag
handler.

Like the peg board (:mod:`~harness_designer.drag_handlers.editor_pegboard`),
this view's camera is a locked top-down orthographic projection (see
``gl.canvas_schematic.camera.Camera.screen_to_world``), so a screen
position maps unambiguously to a world X/Z position -- no directional-
arrows gizmo, no axis lock. Unlike the peg board, schematic dragging is
never length-budget clamped (a schematic wire's path is entirely
auto-routed around whatever's connected to it, not a fixed-length
physical run -- see :mod:`~harness_designer.objects.objects_schematic.
wire_routing`/``wire_reroute``), so this base owns only the screen<->
world projection, nothing else.
"""

from typing import TYPE_CHECKING

from .. import base as _base
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class DragHandlerSchematic(_base.DragHandlerBase):
    """Shared schematic locked-plane mechanics -- see the module
    docstring for the full rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

    @_check_types.do
    def _world_xz(self, mouse_pos: _point.Point) -> _point.Point:
        """Return the locked top-down world position under *mouse_pos*."""
        return self.canvas.camera.screen_to_world(mouse_pos)
