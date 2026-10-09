# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-into-skeleton drag-and-drop for the 3D editor -- BUNDLE_PLACEMENT.md
section 12. Thin per-view glue around :class:`~harness_designer.handlers.
wire_routing_drag.WireRouteMixin`, mirroring exactly how :mod:`.wire`
itself is a thin per-view shell around :class:`~harness_designer.handlers.
wire_drag_base.WireDragMixin` -- the whole eligibility-scan/two-tier-
highlight/drop-tracking algorithm lives there exactly once, shared with
the peg-board editor's own :mod:`~harness_designer.drag_handlers.
editor_pegboard.wire_route`.

:class:`WireRoute` subclasses this view's own ordinary :class:`.wire.Wire`
drag handler rather than ``DragHandler3D``/``WireDragMixin`` directly, so
every bit of the ordinary bend-drag behavior (segment-pair planning,
axis-locked move, snap-probe machinery for a true-end drag) is inherited
completely unchanged -- the only thing layered on top is the eligibility
scan (on arm), the hover-highlight update (on every move), and tracking
which eligible target (if any) is under the cursor at release
(``drop_hit``), per BUNDLE_PLACEMENT.md section 12's own rule that this
is the SAME gesture as an ordinary bend, classified by what's under the
cursor at drop time, not a different one.

Which concrete drag handler gets constructed for a given click
(:class:`.wire.Wire` or :class:`WireRoute`) is decided by the caller --
see ``objects.objects_3d.wire.Wire.handle_interaction``'s own LEFT_DOWN
branch, not here.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...handlers import wire_drag_base as _wire_drag_base
from ...handlers import wire_routing_drag as _wire_routing_drag
from ... import check_types as _check_types
from . import wire as _wire


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ...objects import wire as _wire_object


class WireRoute(_wire.Wire, _wire_routing_drag.WireRouteMixin):
    """3D view's own wire-routing drag handler -- see module docstring."""

    _view = '3d'

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
    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:
        _wire.Wire.__call__(self, delta, mouse_pos)
        self._update_hover(mouse_pos)
