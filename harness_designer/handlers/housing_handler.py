# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for placing housing objects.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import housing as _housing
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color

if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors


class AddHousingHandler(_handler_base.HandlerBase):
    """Handle interactive placement of housings in the 3D editor.
    """
    obj: _housing.Housing = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """
        part_id = mainframe.editor_db.editor.housings.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.HousingsPage, title='Add Housing',
                table=mainframe.global_db.housings_table)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        if part_id is None:
            self._finalized = True
            return

        self.part = mainframe.project.gtables.housings_table[part_id]

    def hover(self, mouse_pos: _point.Point):
        """Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        pass

    def release_capture(self) -> None:
        """Handle release of the captured position and complete any deferred placement work.
        """
        if self._finalized:
            return

        self._finalized = True

        mouse_pos = self._captured_position

        position3d = _utils.get_position_on_focal_plane(mouse_pos, self.camera)

        db_obj = self.ptables.pjt_housings_table.insert(self.part_id, position3d)

        obj = _housing.Housing(self.mainframe, db_obj)
        self.mainframe.project.add_housing(obj)
