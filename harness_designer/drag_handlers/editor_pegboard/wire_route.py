# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-into-skeleton drag-and-drop for the peg-board editor --
BUNDLE_PLACEMENT.md section 12. Peg-board mirror of
:mod:`~harness_designer.drag_handlers.editor_3d.wire_route` -- see that
module's own docstring for the full rationale; the only difference here
is subclassing this view's own :class:`.wire.Wire` instead of the 3D
one, exactly mirroring how :mod:`.wire` itself only differs from its 3D
counterpart in accessors plus the Y-axis hard-lock, both already
inherited unchanged from that class.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...handlers import wire_drag_base as _wire_drag_base
from ...handlers import wire_routing_drag as _wire_routing_drag
from ... import check_types as _check_types
from . import wire as _wire


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ...objects import wire as _wire_object


class WireRoute(_wire.Wire, _wire_routing_drag.WireRouteMixin):
    """Peg-board view's own wire-routing drag handler -- see module
    docstring."""

    _view = 'pegboard'

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_wire_object.Wire",
                 plan: _wire_drag_base.WireDragPlan) -> None:
        _wire.Wire.__init__(self, canvas, target, plan)
        self._arm_routing()

    @_check_types.do
    def delete(self) -> None:
        self._disarm_routing()
        _wire.Wire.delete(self)

    @_check_types.do
    def __call__(self, delta: "_point.Point", mouse_pos: "_point.Point") -> None:
        _wire.Wire.__call__(self, delta, mouse_pos)
        self._update_hover(mouse_pos)
