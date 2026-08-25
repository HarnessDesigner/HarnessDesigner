# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive bundle-waypoint placement for the pegboard editor.

Mirrors ``add_handlers.editor_pegboard.wire_layout`` -- see its own
module docstring for the full reasoning (context-menu-only entry point,
3D-chord insertion mapping). Started from the target bundle's own "Add
Waypoint" context-menu action (``objects_pegboard.bundle.BundleMenu.
on_add_waypoint``), pinned to that one bundle for the whole session.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types
from . import wire_layout as _wire_layout_pegboard


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ...objects import bundle as _bundle


class BundleLayout(_base.AddHandlerBase):
    """Interactive bundle-waypoint placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", bundle: "_bundle.Bundle"
    ):
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
        world_pos = self.camera.screen_to_world(mouse_pos)
        raw_pos, _is_at_endpoint, _endpoint = _wire_layout_pegboard.closest_point_on_chain(
            self._bundle, world_pos.as_numpy)

        pos = self.target.objpegboard.position
        pos += _point.Point(*raw_pos.tolist()) - pos

        self.target.objpegboard.is_visible = True

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ...handlers import bundle_layout_handler as _bundle_layout_handler

        world_pos = self.camera.screen_to_world(mouse_pos)
        raw_pos, is_at_endpoint, endpoint = _wire_layout_pegboard.closest_point_on_chain(
            self._bundle, world_pos.as_numpy)

        diameter = self._bundle.obj3d.diameter

        if is_at_endpoint:
            if endpoint == 'start':
                self._bundle.objpegboard.start_position.attach(self.target.objpegboard.position)
            else:
                self._bundle.objpegboard.stop_position.attach(self.target.objpegboard.position)

            self.target.db_obj.position3d_id = self.target.objpegboard.position.db_id[:-2]
            self.target.db_obj.diameter = diameter
            self.target.objpegboard.is_visible = True
            self.mainframe.project.add_bundle_layout(self.target)
        else:
            objpegboard = self._bundle.objpegboard
            seg_start = objpegboard.start_position.as_numpy
            seg_stop = objpegboard.stop_position.as_numpy
            chord = seg_stop - seg_start
            chord_len_sq = float(np.dot(chord, chord))

            if chord_len_sq < 1e-12:
                t = 0.0
            else:
                t = max(0.0, min(1.0, float(np.dot(raw_pos - seg_start, chord)) / chord_len_sq))

            p1_3d = self._bundle.obj3d.start_position.as_numpy
            p2_3d = self._bundle.obj3d.stop_position.as_numpy
            position_3d = p1_3d + t * (p2_3d - p1_3d)

            self.target.delete()

            new_obj = _bundle_layout_handler._create_bundle_layout_on_bundle(  # NOQA
                self.mainframe.project, self._bundle,
                _point.Point(*position_3d.tolist()), diameter)

            new_obj.objpegboard.is_visible = True
            pos = new_obj.objpegboard.position
            pos += _point.Point(*raw_pos.tolist()) - pos

            self.target = new_obj

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
