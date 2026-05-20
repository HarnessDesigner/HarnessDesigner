# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import cover as _cover
from ..objects import housing as _housing
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


def _get_compat_object_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _housing.Housing | None:

    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _housing.Housing):
        return selected

    return None


class AddCoverHandler(_handler_base.HandlerBase):
    obj: _cover.Cover = None

    def __init__(self, mainframe: "_ui.MainFrame"):

        part_id = mainframe.editor_db.editor.covers.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.CoversPage, title='Add Cover',
                table=mainframe.global_db.covers_table)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.housing_highlight))

        if part_id is None:
            self._finalized = True
            return

        self.part = mainframe.project.gtables.covers_table[part_id]
        part_number = self.part.part_number

        compat_housings = mainframe.global_db.housings_table.get_compat(cover=part_number)
        compat_housings.extend(self.part.compat_housings)

        self.compat_housings = list(set(compat_housings))

        for housing in mainframe.project.housings:
            if housing.db_obj.cover is not None:
                continue

            if housing.db_obj.part.part_number in self.compat_housings:
                housing.identify(self._highlight_material)
            else:
                housing.identify(self._preview_material)

    def hover(self, mouse_pos: _point.Point):
        pass

    def release_capture(self) -> None:
        if self._finalized:
            return

        self._finalized = True
        for housing in self.mainframe.project.housings:
            housing.identify(None)

        mouse_pos = self._captured_position

        selected = _get_compat_object_at_mouse(mouse_pos, self.camera)
        if selected is None:
            return

        if selected.db_obj.cover is not None:
            return

        position3d_id = selected.db_obj.cover_position3d_id
        housing_id = selected.db_obj.db_id

        db_obj = self.ptables.pjt_covers_table.insert(
            self.part_id, position3d_id, housing_id)

        obj = _cover.Cover(self.mainframe, db_obj)
        self.mainframe.project.add_cover(obj)
