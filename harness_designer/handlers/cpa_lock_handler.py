# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for attaching CPA locks to housings.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import cpa_lock as _cpa_lock
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color
from .. import utils as _utils


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import housing as _housing
    from ..database.global_db import cpa_lock as _db_cpa_lock


Config = _config.Config.colors


class AddCPALockHandler(_handler_base.HandlerBase):
    """
    Handle interactive placement of cpa locks onto compatible housings.
    """
    obj: _cpa_lock.CPALock = None

    def __init__(self, mainframe: "_ui.MainFrame", housing: "_housing.Housing" = None):
        """
        Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """

        self._housing = housing

        if housing is None:
            compat_cpa_locks = []
        else:
            compat_cpa_locks = housing.db_obj.part.compat_cpas_array

        part_id = mainframe.editor_db.editor.cpa_locks.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.CoversPage, title='Add CPA Lock',
                table=mainframe.global_db.cpa_locks_table, initial_results=compat_cpa_locks)

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
        self.part: "_db_cpa_lock.CPALock" = None

        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

    def set_part(self, part_id):
        if self.obj is not None:
            self.obj.delete()

        self.part = self.ptables.global_db.cpa_locks_table[part_id]
        part_number = self.part.part_number

        if self._housing is None:

            compat_housings = self.ptables.global_db.housings_table.get_compat(
                cpa_lock=part_number)

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

            db_obj = self.ptables.pjt_cpa_locks_table.insert(
                part_id, pos_id, None)
        else:
            pos_id = self._housing.db_obj.cpa_lock_position3d_id

            db_obj = self.ptables.pjt_cpa_locks_table.insert(
                part_id, pos_id, self._housing.db_obj.db_id)

        self.obj = _cpa_lock.CPALock(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)

        if self._housing is not None:
            self.set_angle_from_housing(self.obj, self._housing)

    @property
    def snap_pool(self):
        housing_cpa_positions = []
        housings = []

        for housing in self.project_housings:
            if not housing.is_in_3dview:
                continue

            housing_cpa_positions.append(housing.db_obj.cpa_lock_position3d)
            housings.append(housing)

        return _utils.SnapPool(housings, housing_cpa_positions, threshold=10.0)

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
                self.reset_angle(self.obj)
        else:
            point = housing.db_obj.cpa_lock_position3d
            self._snapped = housing
            if prev_snapped is not housing:
                self.set_angle_from_housing(self.obj, housing)

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

            self._snapped.db_obj.cpa_lock_position3d.attach(
                self.obj.db_obj.position3d)

            self.obj.db_obj.housing_id = self._snapped.db_obj.db_id
            self.set_angle_from_housing(self.obj, self._snapped)
            obj = self.obj
        else:
            obj = self.obj

        self._finalized = True

        self.mainframe.project.add_cpa_lock(obj)

        self.obj = None
