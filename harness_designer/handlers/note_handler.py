# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for attaching TPA locks to housings.
"""

from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import note as _note
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import add_note as _add_note
from .. import color as _color


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors


class AddNoteHandler(_handler_base.HandlerBase):
    """
    Handle interactive placement of a note.
    """
    obj: _note.Note = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """

        super().__init__(mainframe, None)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        dlg = _add_note.AddNoteDialog(mainframe)
        dlg.exec()
        note, align, style, color_id, size = dlg.GetValue()
        dlg.deleteLater()

        position = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        db_obj = self.ptables.pjt_notes_table.insert(
            position.db_id, None, note, size, align, style, color_id)

        self.obj = _note.Note(mainframe, db_obj)
        self.obj.identify(self._preview_material)

    def hover(self, mouse_pos: _point.Point):
        """
        Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """

        if self._finalized:
            return

        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)

        position = self.obj.db_obj.position3d

        delta = world_pos - position
        position += delta

    def release_capture(self) -> None:
        """
        Handle release of the captured position and complete any
        deferred placement work.
        """

        if self._finalized:
            return

        if self._captured_position is None:
            return

        obj = self.obj

        self._finalized = True

        self.mainframe.project.add_note(obj)
        obj.identify(None)

        self.obj = None
