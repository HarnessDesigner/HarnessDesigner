# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive bundle-waypoint placement for the pegboard editor.

Mirrors ``add_handlers.editor_pegboard.wire_layout`` -- see its own
module docstring for the full reasoning (context-menu-only entry
point). Started from the target bundle's own "Add Waypoint" context-
menu action (``objects_pegboard.bundle.BundleMenu.on_add_waypoint``),
pinned to that one bundle for the whole session.
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types
from . import wire_layout as _wire_layout_pegboard


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ...objects import bundle as _bundle
    from ...objects import bundle_layout as _bundle_layout_facade


@_check_types.do
def create_bundle_layout_on_bundle_pegboard(
    project, bundle: "_bundle.Bundle", position: _point.Point, insert_idx: int
) -> "_bundle_layout_facade.BundleLayout":
    """Insert a new interior peg-board waypoint into *bundle*'s own
    peg-board path at *position* and mark it with a BundleLayout --
    peg-board equivalent of ``handlers.bundle_layout_handler.
    _create_bundle_layout_on_bundle``, against ``pjt_points_pegboard``
    instead of ``pjt_points3d``. Mirrors ``add_handlers.editor_pegboard.
    wire_layout.create_wire_layout_on_wire_pegboard`` exactly -- see its
    own docstring for the full rationale (a ``PJTBundleLayout`` row is
    exclusive to exactly one view, so this never maps onto the bundle's
    3D chord; the new row gets its own peg-board-only point, and its
    diameter is derived automatically from the bundle it's now attached
    to -- see ``PJTBundleLayout.diameter``, never passed in here).
    """
    from ...objects import bundle_layout as _bundle_layout_facade  # NOQA -- avoid a cycle at import time

    ptables = project.ptables

    existing = bundle.db_obj.waypoints_pegboard
    for waypoint in reversed(existing[insert_idx:]):
        waypoint.idx = waypoint.idx + 1

    pos_db = ptables.pjt_points_pegboard_table.insert(
        float(position.x), 0.0, float(position.z),
        bundle_id=bundle.db_obj.db_id, idx=insert_idx)

    db_obj = ptables.pjt_bundle_layouts_table.insert(point_pegboard_id=pos_db.db_id)

    layout_obj = _bundle_layout_facade.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    bundle.objpegboard.refresh_waypoints()

    return layout_obj


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
        interaction_type: _interaction.MouseInteraction, clicked_object
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
        world_pos = self.camera.screen_to_world(mouse_pos)
        raw_pos, is_at_endpoint, endpoint = _wire_layout_pegboard.closest_point_on_chain(
            self._bundle, world_pos.as_numpy)

        if is_at_endpoint:
            if endpoint == 'start':
                self._bundle.objpegboard.start_position.attach(self.target.objpegboard.position)
            else:
                self._bundle.objpegboard.stop_position.attach(self.target.objpegboard.position)

            self.target.db_obj.position_pegboard_id = self.target.objpegboard.position.db_id[:-2]
            self.target.objpegboard.is_visible = True
            self.mainframe.project.add_bundle_layout(self.target)
        else:
            # A new interior waypoint gets its own peg-board-only point
            # (see create_bundle_layout_on_bundle_pegboard's own
            # docstring -- "a layout gets added ... specific to the view
            # it was added in", explicit direction) -- never the
            # bundle's 3D chord the way an earlier version of this
            # branch mapped onto.
            insert_idx = _wire_layout_pegboard.segment_insertion_index(self._bundle, raw_pos)

            self.target.delete()

            new_obj = create_bundle_layout_on_bundle_pegboard(
                self.mainframe.project, self._bundle,
                _point.Point(*raw_pos.tolist()), insert_idx)

            new_obj.objpegboard.is_visible = True

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
