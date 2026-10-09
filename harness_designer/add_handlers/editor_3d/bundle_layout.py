# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive bundle-waypoint placement for the 3D editor.

Ported from ``handlers.bundle_layout_handler.AddBundleLayoutHandler`` --
started only from the target bundle's own "Add Handle" context-menu
action (``objects_3d.bundle.BundleMenu.on_add_handle``), so unlike the
original handler's own project-wide ``_find_bundle`` snap, this session
is pinned to that one bundle for its whole life (there is no toolbar
mode for this, so there is no "which bundle" ambiguity to resolve via
picking). Endpoint-snap detection (dropping the new waypoint exactly on
the bundle's own true start/stop instead of an interior point) is
reused as-is via ``bundle.obj3d.get_closest_endpoint``.
"""

from typing import TYPE_CHECKING, Union as _Union

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...objects import bundle as _bundle


class BundleLayout(_base.AddHandlerBase):
    """
    Interactive bundle-waypoint placement -- see the module docstring.
    """

    @_check_types.do
    def __init__(
        self,
        canvas: "_canvas.Canvas",
        target: "_objects.ObjectBase",
        bundle: "_bundle.Bundle"
    ) -> None:
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera
        self._bundle = bundle
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
                 interaction_type: _interaction.MouseInteraction,
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
        raw_pos, _is_at_endpoint, _endpoint = (
            self._bundle.obj3d.get_closest_endpoint(mouse_pos))

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.target.obj3d.position
        pos += raw_pos - pos

        self.target.obj3d.is_visible = True

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ...handlers import bundle_layout_handler as _bundle_layout_handler

        # Set before the self.target.delete() below (the not-at-endpoint
        # branch), not after -- that delete tears down self.target.obj3d,
        # which finds its own _active_handler is still this same handler
        # and calls this object's delete() again, re-entrantly, while
        # we're still inside this call. That delete() only cancels
        # (deleting self.target a second time) when _finalized is still
        # False, so it has to already be True before the delete ever runs.
        self._finalized = True

        raw_pos, is_at_endpoint, endpoint = (
            self._bundle.obj3d.get_closest_endpoint(mouse_pos))

        if is_at_endpoint:
            if endpoint == 'start':
                self._bundle.obj3d.start_position.attach(
                    self.target.obj3d.position)
            else:
                self._bundle.obj3d.stop_position.attach(
                    self.target.obj3d.position)

            self.target.db_obj.position3d_id = (
                self.target.obj3d.position.db_id[:-2])

            self.target.obj3d.is_visible = True
            self.mainframe.project.add_bundle_layout(self.target)
        else:
            preview_position = _point.Point(*self.target.obj3d.position.as_float)
            self.target.delete()

            self.target = _bundle_layout_handler._create_bundle_layout_on_bundle(  # NOQA
                self.mainframe.project, self._bundle, preview_position)

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
