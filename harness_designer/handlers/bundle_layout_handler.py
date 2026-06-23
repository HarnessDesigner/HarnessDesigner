# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding bundle layout points.
"""

import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import bundle_layout as _bundle_layout
from ..objects import bundle as _bundle
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors

_SNAP_THRESHOLD = 5.0


def _find_bundle(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project
) -> "_bundle.Bundle | None":
    """Return the bundle under the mouse, or the closest one within the snap threshold."""
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _bundle.Bundle):
        return selected

    world_pos = _utils.get_position_on_focal_plane(mouse_pos, camera).as_numpy
    best_bundle = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for bndl in project.bundles:
        if not bndl.is_in_3dview:
            continue

        p1 = bndl.obj3d.start_position.as_numpy
        p2 = bndl.obj3d.stop_position.as_numpy
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-8:
            continue

        t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
        closest = p1 + t * seg
        dist_sq = float(np.sum((world_pos - closest) ** 2))

        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best_bundle = bndl

    return best_bundle


def _create_bundle_layout_at_endpoint(
    project,
    bundle: "_bundle.Bundle",
    endpoint: str,
    diameter: float
) -> "_bundle_layout.BundleLayout":
    if endpoint == 'start':
        point = bundle.obj3d.start_position
    else:
        point = bundle.obj3d.stop_position

    coord_id = int(point.db_id[:-2])
    db_obj = project.ptables.pjt_bundle_layouts_table.insert(coord_id, diameter)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)
    return layout_obj


def _create_bundle_layout_on_bundle(
    project,
    bundle: "_bundle.Bundle",
    position: _point.Point,
    diameter: float
) -> "_bundle_layout.BundleLayout":
    pos_db = project.ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z))
    coord_id = pos_db.db_id

    db_obj = project.ptables.pjt_bundle_layouts_table.insert(coord_id, diameter)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    _split_bundle_at_point(project, bundle, coord_id)

    return layout_obj


def _split_bundle_at_point(
    project,
    original_bundle: "_bundle.Bundle",
    shared_coord_id: int
):
    part_id = original_bundle.db_obj.part_id
    start_id = int(original_bundle.obj3d.start_position.db_id[:-2])
    stop_id = int(original_bundle.obj3d.stop_position.db_id[:-2])

    bundle1_db = project.ptables.pjt_bundles_table.insert(part_id)
    bundle1_db.start_position3d_id = start_id
    bundle1_db.stop_position3d_id = shared_coord_id

    bundle2_db = project.ptables.pjt_bundles_table.insert(part_id)
    bundle2_db.start_position3d_id = shared_coord_id
    bundle2_db.stop_position3d_id = stop_id

    bundle1_obj = _bundle.Bundle(project.mainframe, bundle1_db)
    bundle2_obj = _bundle.Bundle(project.mainframe, bundle2_db)

    project.add_bundle(bundle1_obj)
    project.add_bundle(bundle2_obj)

    original_bundle.delete()


class AddBundleLayoutHandler(_handler_base.HandlerBase):
    """Handle interactive placement of bundle layout points along existing bundles."""
    obj: _bundle_layout.BundleLayout = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialize the handler and create the placement preview.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """
        super().__init__(mainframe, None)

        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.bundle_highlight))

        self._snapped_bundle: "_bundle.Bundle | None" = None

        pos_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        layout_db = self.ptables.pjt_bundle_layouts_table.insert(pos_db.db_id, 10.0)
        self.obj = _bundle_layout.BundleLayout(mainframe, layout_db)
        self.obj.obj3d.is_visible = False

    def hover(self, mouse_pos: _point.Point):
        """Snap the preview to the nearest bundle and update its diameter and color.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        bundle = _find_bundle(mouse_pos, self.camera, self.mainframe.project)

        if bundle is None:
            self.obj.obj3d.is_visible = False
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None
            return

        raw_pos, _, _ = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.obj.obj3d.position
        pos += raw_pos - pos

        if bundle is not self._snapped_bundle:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)

            bundle.identify(self._highlight_material)

            diameter = bundle.obj3d._diameter
            scale = self.obj.obj3d._scale
            scale += _point.Point(diameter, diameter, diameter) - scale

            color = bundle.db_obj.part.color.ui
            material = _materials.Rubber(color)
            self.obj.obj3d._material = material
            self.obj.obj3d._unselected_material = material

            self._snapped_bundle = bundle

        self.obj.obj3d.is_visible = True

    def release_capture(self) -> None:
        """Finalize placement: split the bundle or attach to an endpoint.
        """
        if self._finalized:
            return

        if self._captured_position is None:
            return

        bundle = self._snapped_bundle
        if bundle is None:
            return

        self._snapped_bundle.identify(None)
        self._snapped_bundle = None

        mouse_pos = self._captured_position
        raw_pos, is_at_endpoint, endpoint = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)

        diameter = bundle.obj3d._diameter

        self.obj.delete()
        self.obj = None
        self._finalized = True

        if is_at_endpoint:
            return _create_bundle_layout_at_endpoint(
                self.mainframe.project, bundle, endpoint, diameter)

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        return _create_bundle_layout_on_bundle(
            self.mainframe.project, bundle, raw_pos, diameter)

    def cancel(self):
        """Cancel placement and clean up the preview."""
        if self._snapped_bundle is not None:
            self._snapped_bundle.identify(None)
            self._snapped_bundle = None

        if self.obj is not None:
            self.obj.delete()
            self.obj = None
