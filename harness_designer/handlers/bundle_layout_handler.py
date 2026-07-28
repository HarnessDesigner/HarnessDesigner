# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding bundle layout points.
"""

import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import bundle_layout as _bundle_layout
from ..objects import bundle as _bundle
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors

_SNAP_THRESHOLD = 5.0


def _bundle_segments(bundle: _bundle.Bundle):
    """Every (p1, p2) sub-segment of *bundle*'s current 3D path, as numpy
    arrays -- start, through each interior waypoint in idx order, to
    stop. Mirrors handlers.wire_layout_handler's own _wire_segments."""
    points = [bundle.obj3d.start_position.as_numpy]

    for waypoint in bundle.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)

    points.append(bundle.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


def _find_bundle(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project
) -> _bundle.Bundle | None:
    """
    Return the bundle under the mouse, or the closest one within the snap threshold.
    """

    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _bundle.Bundle):
        return selected

    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    best_bundle = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for bndl in project.bundles:
        if not bndl.is_in_3dview:
            continue

        for p1, p2 in _bundle_segments(bndl):
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


def _find_insertion_index(bundle: _bundle.Bundle, position: np.ndarray) -> int:
    """Return which sub-segment of *bundle*'s current path *position*
    falls closest to -- equivalently, how many of its existing interior
    waypoints come before a new one inserted there. Mirrors
    handlers.wire_layout_handler._find_insertion_index."""
    best_idx = 0
    best_dist = None

    for i, (p1, p2) in enumerate(_bundle_segments(bundle)):
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-12:
            continue

        t = max(0.0, min(1.0, float(np.dot(position - p1, seg)) / seg_len_sq))
        closest = p1 + t * seg
        dist = float(np.sum((position - closest) ** 2))

        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


def _create_bundle_layout_at_endpoint(
    project,
    bundle: _bundle.Bundle,
    endpoint: str,
    diameter: float
) -> _bundle_layout.BundleLayout:

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
    bundle: _bundle.Bundle,
    position: _point.Point,
    diameter: float,
    insert_idx: int | None = None,
) -> _bundle_layout.BundleLayout:
    """Insert a new interior waypoint into *bundle*'s own path at
    *position* and mark it with a BundleLayout.

    No new ``pjt_bundles`` row is created -- an ordinary bend is just a
    tagged waypoint (``bundle_id``/``idx``) on the same bundle, shifting
    every existing waypoint at or past the insertion point up by one
    index. Mirrors handlers.wire_layout_handler._create_wire_layout_on_wire.

    *insert_idx* should be the segment index
    ``bundle.obj3d.get_closest_point`` already found *position* on --
    only computed here (via _find_insertion_index) when the caller
    doesn't have one on hand, e.g. the bundle's own midpoint, when no
    click was captured.
    """
    ptables = project.ptables

    if insert_idx is None:
        insert_idx = _find_insertion_index(bundle, position.as_numpy)

    existing = bundle.db_obj.waypoints3d
    for waypoint in reversed(existing[insert_idx:]):
        waypoint.idx = waypoint.idx + 1

    pos_db = ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z),
        bundle_id=bundle.db_obj.db_id, idx=insert_idx)

    db_obj = ptables.pjt_bundle_layouts_table.insert(pos_db.db_id, diameter)
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)
    project.add_bundle_layout(layout_obj)

    bundle.obj3d.refresh_waypoints()

    return layout_obj


class AddBundleLayoutHandler(_handler_base.HandlerBase):
    """
    Handle interactive placement of bundle layout points along existing bundles.
    """

    obj: _bundle_layout.BundleLayout = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialize the handler and create the placement preview.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """

        super().__init__(mainframe, None)

        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.bundle_highlight))

        self._snapped_bundle: _bundle.Bundle | None = None

        pos_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        layout_db = self.ptables.pjt_bundle_layouts_table.insert(
            pos_db.db_id, 10.0)

        self.obj = _bundle_layout.BundleLayout(mainframe, layout_db)
        self.obj.obj3d.is_visible = False

    def hover(self, mouse_pos: _point.Point):
        """
        Snap the preview to the nearest bundle and update its diameter and color.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """

        bundle = _find_bundle(mouse_pos, self.camera, self.mainframe.project)

        if bundle is None:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None

            self.obj.obj3d.is_visible = False

            return

        raw_pos, _, _ = bundle.obj3d.get_closest_endpoint(mouse_pos)

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.obj.obj3d.position
        pos += raw_pos - pos

        if bundle is not self._snapped_bundle:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)

            bundle.identify(self._highlight_material)

            diameter = bundle.obj3d.diameter
            scale = self.obj.obj3d.scale
            scale += _point.Point(diameter, diameter, diameter) - scale

            color = bundle.db_obj.part.color.ui
            material = _materials.Rubber(color)
            self.obj.obj3d._material = material
            self.obj.obj3d._unselected_material = material

            self._snapped_bundle = bundle

        self.obj.obj3d.is_visible = True

    def release_capture(self) -> None:
        """Finalize placement: insert a waypoint or attach to an endpoint.
        """
        if self._finalized or self._captured_position is None:
            return

        bundle = self._snapped_bundle
        if bundle is None:
            return

        self._snapped_bundle.identify(None)
        self._snapped_bundle = None

        mouse_pos = self._captured_position
        raw_pos, is_at_endpoint, endpoint = bundle.obj3d.get_closest_endpoint(mouse_pos)

        diameter = bundle.obj3d.diameter
        self._finalized = True

        if is_at_endpoint:
            if endpoint == 'start':
                bundle.obj3d.start_position.attach(self.obj.obj3d.position)
            else:
                bundle.obj3d.stop_position.attach(self.obj.obj3d.position)

            # .attach() only makes the delegator (this layout's own preview
            # point) track the bundle endpoint live, in-memory, for this
            # session -- the layout's own DB row still stores its original
            # throwaway point's id. Repoint it to the bundle endpoint's real
            # id (now what self.obj.obj3d.position.db_id reports, since a
            # delegator forwards db_id to its root) so the sharing survives
            # a reload instead of only existing as a live delegation.
            self.obj.db_obj.position3d_id = int(self.obj.obj3d.position.db_id[:-2])

            self.obj.db_obj.diameter = diameter
            self.obj.obj3d.is_visible = True
            self.mainframe.project.add_bundle_layout(self.obj)
        else:
            # Discard the throwaway preview point/layout row created in
            # __init__ -- _create_bundle_layout_on_bundle makes the real
            # one at the correct waypoint position/index, on the bundle's
            # own row (no split), and registers it with the project itself.
            preview_position = _point.Point(*self.obj.obj3d.position.as_float)
            self.obj.delete()
            self.obj = _create_bundle_layout_on_bundle(
                self.mainframe.project, bundle, preview_position, diameter)

            self.obj.obj3d.is_visible = True

        self.obj = None

    def cancel(self):
        """Cancel placement and clean up the preview."""
        if self._snapped_bundle is not None:
            self._snapped_bundle.identify(None)
            self._snapped_bundle = None

        if self.obj is not None:
            self.obj.delete()
            self.obj = None
