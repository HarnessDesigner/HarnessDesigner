# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding bundle layout points.
"""

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


def _create_bundle_layout_at_endpoint(
    project,
    position: _point.Point
) -> _bundle_layout.BundleLayout:

    # Extract the actual database ID from the Point's db_id
    # Point.db_id format is "1233d" or "1232d"
    # We need to strip the suffix and convert to int
    """Create a bundle layout object that reuses an existing bundle endpoint point.

    :param project: Project object that owns the project tables and runtime objects.
    :type project: object
    :param position: 3D point used for placement or geometric calculations.
    :type position: _point.Point
    :returns: The created bundle layout object.
    :rtype: BundleLayout
    """
    point_db_id = int(position.db_id[:-2])  # Remove '3d' or '2d' suffix

    # Create bundle layout in database, referencing the EXISTING point
    # This means the layout will share callbacks with the bundle endpoint
    db_obj = project.ptables.pjt_bundle_layouts_table.insert(point_id=point_db_id)

    # Create bundle layout object
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)

    project.add_bundle_layout(layout_obj)
    return layout_obj


def _create_bundle_layout_on_bundle(
    project,
    bundle: _bundle.Bundle,
    position: _point.Point
) -> _bundle_layout.BundleLayout:

    # Create NEW position point in database (3D)
    # This point will be shared by the layout and both bundle segments
    """Create a bundle layout object on a bundle segment and split the bundle at that location.

    :param project: Project object that owns the project tables and runtime objects.
    :type project: object
    :param bundle: Value for the ``bundle`` parameter. UNKNOWN semantics.
    :type bundle: _bundle.Bundle
    :param position: 3D point used for placement or geometric calculations.
    :type position: _point.Point
    :returns: The created bundle layout object.
    :rtype: BundleLayout
    """
    position_p3d = project.ptables.pjt_points3d_table.insert(
        position.x, position.y, position.z
    )

    # Get the actual Point instance from the database
    # This ensures we're using the same Point object everywhere
    shared_point = position_p3d.point

    # Extract database ID for creating the layout
    # Point.db_id is like "4563d", we need just the integer
    point_db_id = int(position_p3d.db_id)

    # Create bundle layout in database, referencing this point
    db_obj = project.ptables.pjt_bundle_layouts_table.insert(point_id=point_db_id)

    # Create bundle layout object
    layout_obj = _bundle_layout.BundleLayout(project.mainframe, db_obj)

    project.add_bundle_layout(layout_obj)

    # Now split the original bundle at the layout point
    # The two new bundles will share the same Point instance as the layout
    _split_bundle_at_layout(project, bundle, shared_point)

    return layout_obj


def _split_bundle_at_layout(
    project,
    original_bundle: _bundle.Bundle,
    position: _point.Point
):

    # Get original bundle data
    """Replace one bundle with two bundle segments that share the supplied layout point.

    :param project: Project object that owns the project tables and runtime objects.
    :type project: object
    :param original_bundle: Value for the ``original_bundle`` parameter. UNKNOWN semantics.
    :type original_bundle: _bundle.Bundle
    :param position: 3D point used for placement or geometric calculations.
    :type position: _point.Point
    """
    original_start_point = original_bundle.obj3d.start_position
    original_stop_point = original_bundle.obj3d.stop_position
    part_id = original_bundle.db_obj.part_id

    # Get database IDs for the points
    # Remember: Point.db_id is "1233d" or "1232d", need to extract integer
    start_point_db_id = int(original_start_point.db_id[:-2])
    stop_point_db_id = int(original_stop_point.db_id[:-2])
    shared_point_db_id = int(position.db_id[:-2])

    # Create first bundle segment: original start -> shared_point
    bundle1_db = project.ptables.pjt_bundles_table.insert(
        part_id=part_id,
        start_point3d_id=start_point_db_id,
        stop_point3d_id=shared_point_db_id,  # Shares same point as layout
    )

    # Create second bundle segment: shared_point -> original stop
    bundle2_db = project.ptables.pjt_bundles_table.insert(
        part_id=part_id,
        start_point3d_id=shared_point_db_id,  # Shares same point as layout
        stop_point3d_id=stop_point_db_id
    )

    bundle1_obj = _bundle.Bundle(project.mainframe, bundle1_db)
    bundle2_obj = _bundle.Bundle(project.mainframe, bundle2_db)

    project.add_bundle(bundle1_obj)
    project.add_bundle(bundle2_obj)

    original_bundle.delete()


def _get_bundle_at_mouse(mouse_pos: _point.Point, camera: "_camera.Camera"):

    """
    Check if mouse is over a bundle object.

    Returns:
        Bundle object if found, None otherwise
    """
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _bundle.Bundle):
        return selected

    return None


class AddBundleLayoutHandler(_handler_base.HandlerBase):
    """Handle interactive placement of bundle layout points along existing bundles.
    """
    obj: _bundle_layout.BundleLayout = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """
        super().__init__(mainframe, None)
        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.bundle_highlight))

        self.bundle: _bundle.Bundle = None

    def release_capture(self) -> None:
        """Handle release of the captured position and complete any deferred placement work.

        :raises NotImplementedError: Raised by handlers that require a subclass implementation.
        """
        raise NotImplementedError

    def hover(self, mouse_pos: _point.Point):
        """Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        bundle = _get_bundle_at_mouse(mouse_pos, self.camera)

        if bundle is None:
            if self.bundle is not None:
                self.bundle.identify(None)
                self.bundle = None

            self.obj.obj3d.is_visible = False
        else:
            new_position = _utils.get_closest_point_on_wire_endpoint(
                mouse_pos, self.camera, bundle)[0]

            position = self.obj.obj3d.position
            delta = new_position - position
            position += delta

            if bundle != self.bundle:
                bundle.identify([0.3, 1.0, 0.3, 0.5])
                self.obj.obj3d.diameter = bundle.db_obj.part.max_dia
                self.obj.obj3d.is_visible = True

                if self.bundle is not None:
                    self.bundle.identify(None)

                self.bundle = bundle

    def start(self, mouse_pos: _point.Point):
        """Start the handler operation for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        if self.is_active:
            return

        position = _utils.get_position_on_focal_plane(mouse_pos, self.camera)
        position = self.mainframe.project.ptables.pjt_points3d_table.insert(
            position.x, position.y, position.z)

        position_id = position.db_id

        self.obj = self.ptables.pjt_bundle_layouts_table.insert(position_id, 10)

        self.is_active = True

    def finalize(self, mouse_pos: _point.Point):
        """Finalize the active operation using the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        if not self.is_active:
            return

        bundle = _get_bundle_at_mouse(
            mouse_pos, self.camera)

        self.obj.delete()

        if self.bundle is not None:
            self.bundle.identify(None)

        if bundle is None:
            return

        position, is_at_endpoint = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)

        if is_at_endpoint:
            # Placing at existing endpoint
            # position is already the Point instance from the bundle endpoint
            # Just create layout, no bundle split needed
            layout = _create_bundle_layout_at_endpoint(
                self.mainframe.project, position)
        else:
            # Placing in middle
            # position contains coordinates for creating a NEW Point
            # Split bundle and create layout sharing the new Point
            layout = _create_bundle_layout_on_bundle(
                self.mainframe.project, bundle, position)

        return layout
