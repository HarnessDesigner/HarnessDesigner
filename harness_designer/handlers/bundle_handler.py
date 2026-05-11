# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import transition as _transition
from ..objects import bundle as _bundle
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import utils as _utils


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


def _get_compat_object_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _transition.Transition | _wire_layout.WireLayout | None:

    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, (_transition.Transition, _wire_layout.WireLayout)):
        return selected

    return None


class AddBundleHandler(_handler_base.HandlerBase):
    obj: _bundle.Bundle

    def __init__(self, mainframe: "_ui.MainFrame"):
        part_id = mainframe.editor_db.editor.bundle_covers.GetSelection()
        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.BundleCoversPage,
                title='Add Bundle Cover',
                table=mainframe.global_db.bundle_covers_table)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

        super().__init__(mainframe, part_id)
        self._preview_material = _materials.Plastic(Config.add_object.preview_color)
        self._transition_highlight_material = _materials.Plastic(Config.add_object.transition_highlight)
        self._wire_highlight_material = _materials.Plastic(Config.add_object.wire_highlight)

        self._start_position = None
        self._stop_position = None

        if part_id is None:
            self._finalized = True

    def release_capture(self) -> None:
        if self._finalized:
            return

        if self._start_position is None:
            self._start_position = self._captured_position
            return

    def start(self, mouse_pos: _point.Point):
        """Start wire placement with first click"""

        start_point = _get_world_position_for_wire_endpoint(mouse_pos, self.camera)

        if start_point:
            self.is_active = True

            # Create points in DB
            p1_db = self.ptables.pjt_points3d_table.insert(
                start_point.x, start_point.y, start_point.z)

            p2_db = self.ptables.pjt_points3d_table.insert(
                start_point.x, start_point.y, start_point.z)

            # Create temporary wire DB object
            wire_db = self.ptables.pjt_bundles_table.insert(
                self.part_id, None, p1_db.db_id, p2_db.db_id,   # No circuit yet
            )

            self.obj = _wire.Wire(self.mainframe, wire_db)

            # Mark as preview (semi-transparent)
            self.obj.obj3d.material.alpha = 0.5

            # Add to editors (but not to project's wire dict yet)
            self.mainframe.add_object(self.obj)

    def hover(self, mouse_pos: _point.Point):
        """Update preview wire as mouse moves"""

        hover_point = _get_compat_object_at_mouse(mouse_pos, self.camera)


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
