# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive wire-waypoint placement for the 3D editor.

Ported from ``handlers.wire_layout_handler.AddWireLayoutHandler`` --
started only from the target wire's own "Add Layout" context-menu
action (``objects_3d.wire.WireMenu.on_add_handle``), pinned to that one
wire for the whole session -- see
``add_handlers.editor_3d.bundle_layout``'s own module docstring for the
identical reasoning (no toolbar mode exists for this, so there's no
"which wire" ambiguity to resolve via picking).
"""

from typing import TYPE_CHECKING, Union as _Union

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas_window as _canvas_window
    from ... import objects as _objects
    from ...objects import wire as _wire


class WireLayout(_base.AddHandlerBase):
    """Interactive wire-waypoint placement -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas_window.CanvasWindow", target: "_objects.ObjectBase",
                 wire: "_wire.Wire"):

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
    def __call__(self, last_pos: _point.Point, current_pos: _point.Point,
                 had_motion: bool, interaction_type: _interaction.MouseInteraction,
                 clicked_object: _Union["_objects.ObjectBase", None]) -> bool:

        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self._finalized = True
            self.cancel()
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if (
            interaction_type is _interaction.MouseInteraction.LEFT_UP and
            not had_motion
        ):
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        """Move the preview sphere to where the mouse points: onto the path AS DRAWN (the rounded corners), so it sits on the
        tube the user sees; onto the end itself when the mouse is close enough to snap there. Where the waypoint will really go
        (the straight path) is decided on the click, see :meth:`_finalize`."""
        raw_pos, is_at_endpoint = self._closest_endpoint(mouse_pos)

        if not is_at_endpoint:
            curve_pos = self._wire.obj3d.get_closest_curve_point(mouse_pos)

            if curve_pos is not None:
                raw_pos = curve_pos

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.target.obj3d.position
        pos += raw_pos - pos

        self.target.obj3d.is_visible = True

    @_check_types.do
    def _closest_endpoint(self, mouse_pos: _point.Point) -> tuple:
        """``get_closest_endpoint`` of the wire; a cable's ends are free and take no layout, so for a cable the mouse is never at an
        endpoint (its closest point on the route is all there is)."""
        raw_pos, is_at_endpoint = self._wire.obj3d.get_closest_endpoint(mouse_pos)

        if self._wire.is_cable:
            return raw_pos, False

        return raw_pos, is_at_endpoint

    @_check_types.do
    def _finalize_cable(self, mouse_pos: _point.Point) -> None:
        """Add the waypoint to the cable's route where the click is. The preview sphere is only a marker: it goes, and the cable
        draws its own rounded corner at the new point."""
        position, _angle, insert_idx = self._wire.obj3d.get_closest_point(mouse_pos)

        self.target.delete()
        self.target = None

        if position is not None:
            self._wire.obj3d.add_waypoint(position, insert_idx)

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ...handlers import wire_layout_handler as _wire_layout_handler

        # Set before the self.target.delete() below (the not-at-endpoint
        # branch), not after -- see editor_3d.bundle_layout.BundleLayout.
        # _finalize's own comment for why.
        self._finalized = True

        if self._wire.is_cable:
            self._finalize_cable(mouse_pos)
            return

        raw_pos, is_at_endpoint = (
            self._wire.obj3d.get_closest_endpoint(mouse_pos))

        if is_at_endpoint:
            if raw_pos is self._wire.obj3d.start_position:
                self._wire.obj3d.start_position.attach(
                    self.target.obj3d.position)
            else:
                self._wire.obj3d.stop_position.attach(
                    self.target.obj3d.position)

            self.target.db_obj.position3d_id = (
                self.target.obj3d.position.db_id[:-2])

            self.target.obj3d.end_preview()
            self.target.obj3d.is_visible = True
            self.mainframe.project.add_wire_layout(self.target)
        else:
            # the waypoint goes on the straight path (the preview sphere rides on the drawn, rounded one)
            if not isinstance(raw_pos, _point.Point):
                raw_pos = _point.Point(*raw_pos)

            preview_position = _point.Point(*raw_pos.as_float)

            self.target.delete()

            self.target = _wire_layout_handler._create_wire_layout_on_wire(  # NOQA
                self.mainframe.project, self._wire, preview_position)

            self.target.obj3d.is_visible = True

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self._finalized = True
            self.cancel()
