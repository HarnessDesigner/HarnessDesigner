# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Interactive handler logic for placing seals on compatible objects.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING


from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color
from .. import utils as _utils
from ..objects import housing as _housing
from ..objects import terminal as _terminal
from ..objects import cavity as _cavity
from ..objects import seal as _seal

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.global_db import seal as _db_seal


Config = _config.Config.colors


class AddSealHandler(_handler_base.HandlerBase):
    """Handle interactive placement of seals."""
    obj: _seal.Seal = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 selected: _housing.Housing | _terminal.Terminal | _cavity.Cavity = None):

        """
        Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """

        self._selected = selected

        if isinstance(selected, _housing.Housing):
            compat_seals = selected.db_obj.part.compat_seals_array

        elif isinstance(selected, _cavity.Cavity):
            self.ptables.global_db.seals_table.execute(
                'SELECT id FROM seal_types WHERE UPPER(name) = "PLUG";')
            rows = self.ptables.global_db.seals_table.fetchall()
            if rows:
                type_id = rows[0][0]

                height = selected.db_obj.part.height
                width = selected.db_obj.part.width

                self.ptables.global_db.seals_table.execute(
                    'SELECT part_number FROM seals WHERE type_id=? AND width=? AND height=?;',
                    (type_id, width, height))
                rows = self.ptables.global_db.seals_table.fetchall()
                compat_seals = [row[0] for row in rows]
            else:
                compat_seals = []

        elif isinstance(selected, _terminal.Terminal):
            compat_seals = selected.db_obj.part.compat_seals_array
        else:
            compat_seals = []

        part_id = mainframe.editor_db.editor.covers.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SealsPage, title='Add Seal',
                table=mainframe.global_db.seals_table, initial_results=compat_seals)

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

        self.compat_housings: list[str] = None
        self.project_housings: list[_housing.Housing] = None

        self.compat_terminals: list[str] = None
        self.project_terminals: list[_terminal.Terminal] = None

        self.project_cavities: dict[_cavity.Cavity, _housing.Housing] = None

        self._snapped = None
        self.part: "_db_seal.Seal" = None

        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

    def set_part(self, part_id):
        if self.obj is not None:
            self.obj.delete()

        self.part = self.ptables.global_db.seals_table[part_id]
        part_number = self.part.part_number

        if self._selected is None:
            type_name = self.part.type.name.lower()
            if type_name in ('sws', 'single wire seal'):
                compat_terminals = self.ptables.global_db.terminals_table.get_compat(seal=part_number)
                compat_terminals.extend(self.part.compat_terminals_array)

                self.compat_terminals = list(set(compat_terminals))
                self.project_terminals = []

                for terminal in self.mainframe.project.terminals:
                    if terminal.db_obj.part.part_number in self.compat_terminals:
                        terminal.identify(self._compat_highlight_material)
                    else:
                        terminal.identify(self._highlight_material)

                    self.project_terminals.append(terminal)

            elif type_name == 'plug':
                compat_housings = self.ptables.global_db.housings_table.get_compat(seal=part_number)
                compat_housings.extend(self.part.compat_housings_array)

                self.compat_housings = list(set(compat_housings))
                self.project_cavities = {}

                for cavity in self.mainframe.project.cavities:
                    housing = cavity.db_obj.housing

                    if cavity.db_obj.terminal is not None:
                        continue

                    if housing.part.part_number in self.compat_housings:
                        cavity.identify(self._compat_highlight_material)
                    else:
                        cavity.identify(self._highlight_material)

                    self.project_cavities[cavity] = housing.get_object()
            else:
                compat_housings = self.ptables.global_db.housings_table.get_compat(seal=part_number)
                compat_housings.extend(self.part.compat_housings_array)

                self.compat_housings = list(set(compat_housings))
                self.project_housings = []

                for housing in self.mainframe.project.housings:
                    if housing.db_obj.part.part_number in self.compat_housings:
                        housing.identify(self._compat_highlight_material)
                    else:
                        housing.identify(self._highlight_material)

                    self.project_housings.append(housing)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)
            pos_id = pos_obj.db_id
            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, pos_id, None, None, None)
        else:
            if isinstance(self._selected, _housing.Housing):
                pos_id = self._selected.db_obj.seal_position3d_id
                db_obj = self.ptables.pjt_seals_table.insert(
                    part_id, pos_id, self._selected.db_obj.db_id, None, None)

            elif isinstance(self._selected, _terminal.Terminal):
                pos_id = self._selected.db_obj.position3d_id
                db_obj = self.ptables.pjt_seals_table.insert(
                    part_id, pos_id, None, self._selected.db_obj.db_id, None)
            else:
                pos_id = self._selected.db_obj.terminal_position3d_id
                db_obj = self.ptables.pjt_seals_table.insert(
                    part_id, pos_id, None, None, self._selected.db_obj.db_id
                )

        self.obj = _seal.Seal(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)

    @property
    def snap_pool(self):
        positions = []
        objects = []

        if self.project_housings is not None:
            for housing in self.project_housings:
                if not housing.is_in_3dview:
                    continue

                positions.append(housing.db_obj.seal_position3d)
                objects.append(housing)

        elif self.project_terminals is not None:
            for terminal in self.project_terminals:
                if not terminal.is_in_3dview:
                    continue

                positions.append(terminal.db_obj.position3d)
                objects.append(terminal)

        elif self.project_cavities is not None:
            for cavity in self.project_cavities.keys():
                if not cavity.is_in_3dview:
                    continue

                positions.append(cavity.db_obj.terminal_position3d_id)
                objects.append(cavity)

        else:
            raise RuntimeError('sanity check')

        return _utils.SnapPool(objects, positions)

    def hover(self, mouse_pos: _point.Point):
        """
        Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """

        if self._finalized or self._selected is not None:
            return

        snap_pool = self.snap_pool
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        obj = snap_pool.query(world_pos)

        if obj is None:
            point = world_pos
            self._snapped = None
        else:
            if isinstance(obj, _housing.Housing):
                point = obj.db_obj.seal_position3d

            elif isinstance(obj, _terminal.Terminal):
                point = obj.db_obj.position3d

            elif isinstance(obj, _cavity.Cavity):
                point = obj.db_obj.terminal_position3d

            else:
                raise RuntimeError('sanity check')

            self._snapped = obj

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

        if self._selected is None:

            if self._snapped is None:
                return

            self.obj.delete()

            if isinstance(self._snapped, _housing.Housing):
                for housing in self.mainframe.project.housings:
                    housing.identify(None)

                db_obj = self.ptables.pjt_seals_table.insert(
                    self.part.db_id, self._snapped.db_obj.seal_position3d_id,
                    self._snapped.db_obj.db_id, None, None)

            elif isinstance(self._snapped, _terminal.Terminal):
                for terminal in self.mainframe.project.terminals:
                    terminal.identify(None)

                db_obj = self.ptables.pjt_seals_table.insert(
                    self.part.db_id, self._snapped.db_obj.position3d_id,
                    None, self._snapped.db_obj.db_id, None)

            elif isinstance(self._snapped, _cavity.Cavity):
                for cavity in self.mainframe.project.cavities:
                    cavity.identify(None)

                db_obj = self.ptables.pjt_seals_table.insert(
                    self.part.db_id, self._snapped.db_obj.terminal_position3d_id,
                    None, None, self._snapped.db_obj.db_id)

            else:
                raise RuntimeError('sanity check')

            obj = _seal.Seal(self.mainframe, db_obj)

        else:
            obj = self.obj

        self._finalized = True

        self.mainframe.project.add_seal(obj)

        self.obj = None
