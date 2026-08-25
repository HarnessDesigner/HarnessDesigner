# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive wire-waypoint placement for the 3D editor.

Ported from ``handlers.wire_layout_handler.AddWireLayoutHandler`` --
started only from the target wire's own "Add Handle" context-menu
action (``objects_3d.wire.WireMenu.on_add_handle``), pinned to that one
wire for the whole session -- see
``add_handlers.editor_3d.bundle_layout``'s own module docstring for the
identical reasoning (no toolbar mode exists for this, so there's no
"which wire" ambiguity to resolve via picking).
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...objects import wire as _wire


class WireLayout(_base.AddHandlerBase):
    """Interactive wire-waypoint placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", wire: "_wire.Wire"
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera
        self._wire = wire
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        raw_pos, _is_at_endpoint, _endpoint = self._wire.obj3d.get_closest_endpoint(mouse_pos)
        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.target.obj3d.position
        pos += raw_pos - pos

        self.target.obj3d.is_visible = True

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ...handlers import wire_layout_handler as _wire_layout_handler

        raw_pos, is_at_endpoint, endpoint = self._wire.obj3d.get_closest_endpoint(mouse_pos)

        if is_at_endpoint:
            if endpoint == 'start':
                self._wire.obj3d.start_position.attach(self.target.obj3d.position)
            else:
                self._wire.obj3d.stop_position.attach(self.target.obj3d.position)

            self.target.db_obj.position3d_id = self.target.obj3d.position.db_id[:-2]
            self.target.obj3d.is_visible = True
            self.mainframe.project.add_wire_layout(self.target)
        else:
            preview_position = _point.Point(*self.target.obj3d.position.as_float)
            self.target.delete()
            self.target = _wire_layout_handler._create_wire_layout_on_wire(  # NOQA
                self.mainframe.project, self._wire, preview_position)
            self.target.obj3d.is_visible = True

        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
