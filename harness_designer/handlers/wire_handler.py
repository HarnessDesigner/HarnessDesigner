from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import terminal as _terminal
from ..objects import splice as _splice
from ..objects import wire as _wire

from .. import utils as _utils

if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


def _can_accept_wire_endpoint(obj) -> bool:
    return isinstance(
        obj, (_wire_layout.WireLayout, _splice.Splice, _terminal.Terminal))


def _get_world_position_for_wire_endpoint(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _point.Point:

    # First, check if user clicked on an existing object
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)

    if selected and _can_accept_wire_endpoint(selected):
        # User clicked on an object that can accept wires
        return _get_position_on_object(selected)
    else:
        # User clicked on empty space - use focal plane
        return _utils.get_position_on_focal_plane(mouse_pos, camera)


def _get_position_on_object(
    obj: _wire_layout.WireLayout | _splice.Splice | _terminal.Terminal
) -> _point.Point:

    return obj.obj3d.wire_position


class AddWireHandler(_handler_base.HandlerBase):
    """
    Manages interactive wire placement in 3D editor.

    Handles two-click wire placement with real-time preview:
    - First click: Set start point
    - Mouse move: Update preview wire
    - Second click: Finalize wire
    """
    obj: _wire.Wire

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

    def start(self, mouse_pos: _point.Point):
        """Start wire placement with first click"""

        start_point = _get_world_position_for_wire_endpoint(mouse_pos, self.camera)

        if start_point:
            self.is_active = True

            # Create points in DB
            p1_db = self.mainframe.ptables.pjt_points3d_table.insert(
                start_point.x, start_point.y, start_point.z)

            p2_db = self.mainframe.ptables.pjt_points3d_table.insert(
                start_point.x, start_point.y, start_point.z)

            # Create temporary wire DB object
            wire_db = self.mainframe.ptables.pjt_wires_table.insert(
                self.part_id, p1_db.db_id, p2_db.db_id, None  # No circuit yet
            )

            self.obj = _wire.Wire(self.mainframe, wire_db)

            # Mark as preview (semi-transparent)
            self.obj.obj3d.material.alpha = 0.5

            # Add to editors (but not to project's wire dict yet)
            self.mainframe.add_object(self.obj)

    def hover(self, mouse_pos: _point.Point):
        """Update preview wire as mouse moves"""
        if not self.is_active:
            return

        end_point = _get_world_position_for_wire_endpoint(mouse_pos, self.camera)

        if end_point:
            position = self.obj.obj3d.stop_position
            delta = end_point - position
            position += delta

    def finalize(self, mouse_pos: _point.Point):
        """Finalize wire placement with second click"""
        if not self.is_active:
            return None

        end_point = _get_world_position_for_wire_endpoint(mouse_pos, self.camera)

        if end_point:
            position = self.obj.obj3d.stop_position
            delta = end_point - position
            position += delta

            # Reset state
            self.is_active = False
            self.mainframe.project.add_wire(self.obj)

    def cancel(self):
        """Cancel wire placement"""
        if self.obj:
            # Remove from editors
            self.mainframe.remove_object(self.obj)

            # Delete from DB
            self.mainframe.ptables.pjt_wires_table.delete(
                self.obj.db_obj.db_id)

            self.obj = None

        self.is_active = False
