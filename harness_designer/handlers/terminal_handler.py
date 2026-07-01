# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for placing terminals into cavities.

Three placement modes are supported depending on which arguments are supplied:

Mode 1 – both *housing* and *cavity* are given (wrapper objects)
    The terminal is placed immediately into the specified cavity.  No mouse
    interaction is required.  Invoke via :func:`run_attached_handler`.

Mode 2 – only *housing* is given
    A terminal preview is created and snaps to cavities that belong to the
    specified housing.  Invoke via :func:`start_handler`.

Mode 3 – neither argument is given
    The currently selected terminal in the database editor is used (if any),
    otherwise a part search dialog opens.  The preview snaps to any cavity
    whose compat list, blade size, or dimensions match the chosen terminal.
    Invoke via :func:`start_handler`.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING

import numpy as np

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import terminal as _terminal
from ..objects import cavity as _cavity
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color
from .. import utils as _utils


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import housing as _housing
    from ..database.global_db import terminal as _db_terminal


Config = _config.Config.colors


class AddTerminalHandler(_handler_base.HandlerBase):
    """
    Handle interactive placement of terminals into cavities.
    """

    obj: _terminal.Terminal = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 housing: "_housing.Housing" = None,
                 cavity: "_cavity.Cavity" = None):
        """
        Initialise the handler.

        :param mainframe: Main application frame.
        :param housing: Housing wrapper object (optional).
        :param cavity:  Cavity wrapper object (only when *housing* is also given).
        """

        self._housing = housing
        self._cavity = cavity
        self.mainframe = mainframe

        if housing is not None and cavity is not None:
            compat_ids = self._get_cavity_compat_pns(housing, cavity)
        elif housing is not None:
            compat_ids = self._get_housing_compat_pns(housing)
        else:
            compat_ids = []

        # Mode 3 checks the editor DB first; modes 1 & 2 always open the dialog.
        if housing is None:
            part_id = mainframe.editor_db.editor.terminals.GetSelection()
        else:
            part_id = None

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.TerminalsPage, title='Add Terminal',
                table=mainframe.global_db.terminals_table,
                initial_results=compat_ids)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.housing_highlight))
        self._compat_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight))

        self.project_cavities: list[_cavity.Cavity] = []
        self._snapped: _cavity.Cavity = None
        self._is_male: bool = False
        self.part: "_db_terminal.Terminal" = None

        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

            if self._cavity is not None:
                self.release_capture()
                self._finalized = True

    @staticmethod
    def _cavity_midpoint(pjt_cavity):
        """
        Return world-space midpoint of *pjt_cavity* along its insertion axis.
        """

        cpos_np = pjt_cavity.position3d.as_numpy.astype(np.float64)
        cav_ang = pjt_cavity.angle3d
        length = float(pjt_cavity.part.length)

        ref_local = np.array([[0.0, 0.0, length]], dtype=np.float64)
        ref_world = np.asarray(ref_local @ cav_ang, dtype=np.float64)[
                        0] + cpos_np
        mid = (cpos_np + ref_world) / 2.0
        return float(mid[0]), float(mid[1]), float(mid[2])

    def _get_cavity_compat_pns(self, housing, cavity):
        """
        Return terminal part numbers compatible with *cavity* / *housing* (Mode 1).

        Priority:
        1. cavity.compat_terminals (blade-size filtered list on the global cavity)
        2. cavity.terminal_sizes matched to terminal blade_sizes, gender-filtered
        3. max(cavity.width, height) ≥ terminal blade_size, gender-filtered
        """

        g_cavity = cavity.db_obj.part
        g_housing = housing.db_obj.part

        compat = g_cavity.compat_terminals
        if compat:
            return [t.part_number for t in compat]

        housing_gender_id = g_housing.gender_id
        table = self.mainframe.global_db.terminals_table

        terminal_sizes = g_cavity.terminal_sizes
        if terminal_sizes:
            pns = []
            for size in terminal_sizes:
                table.execute(
                    'SELECT part_number FROM terminals WHERE blade_size=? AND gender_id=?;',
                    (size, housing_gender_id))
                pns.extend(row[0] for row in table.fetchall())
            if pns:
                return list(set(pns))

        max_dim = max(g_cavity.width or 0.0, g_cavity.height or 0.0)
        if max_dim > 0.0:
            table.execute(
                'SELECT part_number FROM terminals WHERE blade_size<=? AND gender_id=?;',
                (max_dim, housing_gender_id))
            return list(set(row[0] for row in table.fetchall()))

        return []

    def _get_housing_compat_pns(self, housing):
        """
        Return terminal part numbers compatible with *housing* (Mode 2).

        Priority:
        1. global housing compat_terminals list
        2. Aggregate terminal_sizes from all global housing cavities, gender-filtered
        3. max(width, height) across all project cavities for this housing
        """

        g_housing = housing.db_obj.part
        housing_gender_id = g_housing.gender_id
        table = self.mainframe.global_db.terminals_table

        compat = g_housing.compat_terminals
        if compat:
            return [t.part_number for t in compat]

        all_sizes = set()
        for g_cav in g_housing.cavities:
            all_sizes.update(g_cav.terminal_sizes)

        if all_sizes:
            pns = []
            for size in all_sizes:
                table.execute(
                    'SELECT part_number FROM terminals '
                    'WHERE blade_size=? '
                    'AND gender_id=?;',
                    (size, housing_gender_id))
                pns.extend(row[0] for row in table.fetchall())
            if pns:
                return list(set(pns))

        max_dim = 0.0
        for pjt_cav in housing.db_obj.cavities:
            g_cav = pjt_cav.part
            max_dim = max(max_dim, g_cav.width or 0.0, g_cav.height or 0.0)

        if max_dim > 0.0:
            table.execute(
                'SELECT part_number FROM terminals '
                'WHERE blade_size<=? '
                'AND gender_id=?;',
                (max_dim, housing_gender_id))
            return list(set(row[0] for row in table.fetchall()))

        return []

    # ------------------------------------------------------------------
    # set_part – creates the terminal object for all three modes
    # ------------------------------------------------------------------

    def set_part(self, part_id: int):
        if self.obj is not None:
            self.obj.delete()

        self.part = self.ptables.global_db.terminals_table[part_id]

        name = f'{self.part.manufacturer.name} {self.part.part_number}'
        self._is_male = self.part.gender.name.lower() == 'male'

        if self._cavity is not None:
            # Mode 1: place terminal directly at the cavity's insertion point.
            pjt_cavity = self._cavity.db_obj

            if self._is_male:
                tx, ty, tz = [float(str(item)) for item in pjt_cavity.obb[:4].mean(axis=0).tolist()]
            else:
                tx, ty, tz = pjt_cavity.position3d.as_float

            point = _point.Point(tx, ty, tz)
            pos = pjt_cavity.terminal_position3d
            delta = point - pos
            pos += delta

            db_obj = self.ptables.pjt_terminals_table.insert(
                part_id, name, None, int(pos.db_id[:-2]), pjt_cavity.db_id)

        elif self._housing is not None:
            # Mode 2: floating preview, snaps only to this housing's cavities.
            housing_db = self._housing.db_obj

            for cavity in self._housing.cavities:
                if cavity.db_obj.terminal is not None:
                    continue

                cavity.identify(self._compat_highlight_material)
                self.project_cavities.append(cavity)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = self.ptables.pjt_terminals_table.insert(
                part_id, name, None, pos_obj.db_id, None)

        else:
            # Mode 3: floating preview, snaps to any compatible cavity.
            part_number = self.part.part_number
            blade_size = self.part.blade_size
            part_gender_id = self.part.gender_id

            for cavity in self.mainframe.project.cavities:
                if cavity.db_obj.terminal is not None:
                    continue

                g_cavity = cavity.db_obj.part
                g_housing = cavity.db_obj.housing.part

                compat = g_cavity.compat_terminals
                if any(t.part_number == part_number for t in compat):
                    cavity.identify(self._compat_highlight_material)
                    self.project_cavities.append(cavity)
                    continue

                gender_match = (g_housing.gender_id == part_gender_id)
                terminal_sizes = g_cavity.terminal_sizes

                if (terminal_sizes and blade_size
                        and blade_size in terminal_sizes and gender_match):
                    cavity.identify(self._compat_highlight_material)
                    self.project_cavities.append(cavity)
                    continue

                if not terminal_sizes and gender_match and blade_size:
                    max_dim = max(g_cavity.width or 0.0, g_cavity.height or 0.0)
                    if max_dim > 0.0 and blade_size <= max_dim:
                        cavity.identify(self._compat_highlight_material)
                        self.project_cavities.append(cavity)
                        continue

                cavity.identify(self._highlight_material)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = self.ptables.pjt_terminals_table.insert(
                part_id, name, None, pos_obj.db_id, None)

        self.obj = _terminal.Terminal(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)

        if self._cavity is not None:
            self.set_angle_from_cavity(self.obj, self._cavity.db_obj)

    @property
    def snap_pool(self):
        objects = []
        positions = []

        for cavity in self.project_cavities:
            if not cavity.is_in_3dview:
                continue

            if self._is_male:
                positions.append(cavity.db_obj.position3d)
            else:
                x, y, z = self._cavity_midpoint(cavity.db_obj)
                positions.append(_point.Point(x, y, z))

            objects.append(cavity)

        return _utils.SnapPool(objects, positions)

    def hover(self, mouse_pos: _point.Point):
        """
        Snap the preview terminal to the nearest compatible cavity.
        """

        if self._finalized or self._cavity is not None:
            return

        snap_pool = self.snap_pool
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        snapped = snap_pool.query(world_pos)

        prev_snapped = self._snapped

        if snapped is None:
            point = world_pos
            self._snapped = None
            if prev_snapped is not None:
                self.reset_angle(self.obj)
        else:
            if self._is_male:
                point = snapped.db_obj.position3d
            else:
                x, y, z = self._cavity_midpoint(snapped.db_obj)
                point = _point.Point(x, y, z)

            self._snapped = snapped
            if prev_snapped is not snapped:
                self.set_angle_from_cavity(self.obj, snapped.db_obj)

        position = self.obj.db_obj.position3d
        delta = point - position
        position += delta

    def release_capture(self) -> None:
        """
        Finalise terminal placement.
        """

        if self._finalized:
            return

        if self._captured_position is None:
            return

        if self._cavity is None:
            # Modes 2 & 3 – must be snapped to a cavity.
            if self._snapped is None:
                return

            for cavity in self.mainframe.project.cavities:
                cavity.identify(None)

            self.obj.db_obj.cavity_id = self._snapped.db_obj.db_id
            self.set_angle_from_cavity(self.obj, self._snapped.db_obj)
            obj = self.obj
        else:
            # Mode 1 – terminal was already positioned in set_part.
            obj = self.obj

        self._finalized = True
        self.mainframe.project.add_terminal(obj)
        self.obj = None
