# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for attaching covers to housings.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import cover as _cover
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color
from .. import utils as _utils


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import housing as _housing
    from ..database.global_db import cover as _db_cover


Config = _config.Config.colors


class AddCoverHandler(_handler_base.HandlerBase):
    """Handle interactive placement of covers onto compatible housings.
    """
    obj: _cover.Cover = None

    def __init__(self, mainframe: "_ui.MainFrame", housing: "_housing.Housing" = None):

        """Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """

        self._housing = housing

        if housing is None:
            compat_covers = []
        else:
            compat_covers = housing.db_obj.part.compat_covers_array

        part_id = mainframe.editor_db.editor.covers.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.CoversPage, title='Add Cover',
                table=mainframe.global_db.covers_table, initial_results=compat_covers)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.housing_highlight))

        self._compat_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight)
        )

        self.compat_housings = []
        self.project_housings = []

        self._snapped = None
        self.part: "_db_cover.Cover" = None

        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

    def set_part(self, part_id):
        if self.obj is not None:
            self.obj.delete()

        self.part = self.ptables.global_db.covers_table[part_id]
        part_number = self.part.part_number

        if self._housing is None:

            compat_housings = self.ptables.global_db.housings_table.get_compat(cover=part_number)

            compat_housings.extend(self.part.compat_housings)

            self.compat_housings = list(set(compat_housings))
            self.project_housings = []

            for housing in self.mainframe.project.housings:
                if housing.db_obj.cover is not None:
                    continue

                if housing.db_obj.part.part_number in self.compat_housings:
                    housing.identify(self._compat_highlight_material)
                else:
                    housing.identify(self._highlight_material)

                self.project_housings.append(housing)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)
            pos_id = pos_obj.db_id
            db_obj = self.ptables.pjt_covers_table.insert(
                part_id, pos_id, None)
        else:
            pos_id = self._housing.db_obj.cover_position3d_id
            db_obj = self.ptables.pjt_covers_table.insert(
                part_id, pos_id, self._housing.db_obj.db_id)

        self.obj = _cover.Cover(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)

        if self._housing is not None:
            _handler_base.set_angle_from_housing(self.obj.db_obj, self._housing.db_obj)

    @property
    def snap_pool(self):
        housing_cover_positions = []
        housings = []

        for housing in self.project_housings:
            if not housing.is_in_3dview:
                continue

            housing_cover_positions.append(housing.db_obj.cover_position3d)
            housings.append(housing)

        return _utils.SnapPool(housings, housing_cover_positions)

    def hover(self, mouse_pos: _point.Point):
        """
        Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """

        if self._finalized or self._housing is not None:
            return

        snap_pool = self.snap_pool
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        housing = snap_pool.query(world_pos)

        prev_snapped = self._snapped

        if housing is None:
            point = world_pos
            self._snapped = None
            if prev_snapped is not None:
                _handler_base.reset_angle(self.obj.db_obj)
        else:
            point = housing.db_obj.cover_position3d
            self._snapped = housing
            if prev_snapped is not housing:
                _handler_base.set_angle_from_housing(self.obj.db_obj, housing.db_obj)

        position = self.obj.db_obj.position3d

        delta = point - position
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

        if self._housing is None:

            if self._snapped is None:
                return

            for housing in self.mainframe.project.housings:
                housing.identify(None)

            self.obj.delete()

            db_obj = self.ptables.pjt_covers_table.insert(
                self.part.db_id, self._snapped.db_obj.cover_position3d_id,
                self._snapped.db_obj.db_id)

            _handler_base.set_angle_from_housing(db_obj, self._snapped.db_obj)
            obj = _cover.Cover(self.mainframe, db_obj)
        else:
            obj = self.obj

        self._finalized = True

        self.mainframe.project.add_cover(obj)

        self.obj = None
