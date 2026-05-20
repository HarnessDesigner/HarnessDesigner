# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import terminal as _terminal
from ..objects import splice as _splice
from ..objects import wire as _wire
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


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
    obj: _wire.Wire

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._terminal_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.terminal_highlight))
        self._wire_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))
        self._splice_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight))
        self.start_position: _point.Point = None
        self.stop_position: _point.Point = None

    def release_capture(self) -> None:
        if self._finalized:
            return

        mouse_pos = self._captured_position

        position = _get_world_position_for_wire_endpoint(mouse_pos, self.camera)

        if self.start_position is None:
            self.start_position = position
            self.stop_position = position.copy()

            if self.start_position.db_id is None:
                obj = self.ptables.pjt_points3d_table.insert(*self.start_position.as_float)
                start_position = obj.point
            else:
                start_position = self.start_position

            start_position_id = start_position.db_id[:-2]
            stop_position_id = self.stop_position.db_id[:-2]

            wire_db = self.ptables.pjt_wires_table.insert(
                self.part_id, None, start_position_id, stop_position_id,  # No circuit yet
            )

            self.obj = _wire.Wire(self.mainframe, wire_db)
            self.obj.identify(self._preview_material)

        raise NotImplementedError

    def hover(self, mouse_pos: _point.Point):
        """Update preview wire as mouse moves"""
        if self._finalized:
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
            self.ptables.pjt_wires_table.delete(
                self.obj.db_obj.db_id)

            self.obj = None

        self.is_active = False
