# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Interactive handler logic for placing seals on compatible objects.

Five placement modes depending on the arguments supplied:

Mode 1a – *housing* only (for_cavity=False)
    MAT seal placed on the housing immediately via the pre-defined seal slot.
    Invoke via :func:`run_attached_handler`.

Mode 1b – *housing* only with for_cavity=True
    Plug/dummy-pin preview snaps interactively to this housing's empty cavities.
    Invoke via :func:`start_handler`.

Mode 2 – *terminal* only
    SWS seal placed at the midpoint of the terminal's cavity immediately.
    Invoke via :func:`run_attached_handler`.

Mode 3 – *cavity* only
    Plug or dummy-pin placed on the cavity immediately.  Dummy pins use the
    same entry/midpoint logic as terminal pins.
    Invoke via :func:`run_attached_handler`.

Mode 4 – no arguments
    Editor selection is tried first; a part-search dialog opens otherwise.
    The preview snaps to housings, terminals, or empty cavities depending on
    the chosen seal type.  Invoke via :func:`start_handler`.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING

import numpy as np

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..objects import housing as _housing
from ..objects import terminal as _terminal
from ..objects import cavity as _cavity
from ..objects import seal as _seal
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color
from .. import utils as _utils

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.global_db import seal as _db_seal


Config = _config.Config.colors


class AddSealHandler(_handler_base.HandlerBase):
    """
    Handle interactive placement of seals.
    """

    obj: _seal.Seal = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 housing: "_housing.Housing" = None,
                 terminal: "_terminal.Terminal" = None,
                 cavity: "_cavity.Cavity" = None,
                 for_cavity: bool = False):

        self._housing = housing
        self._terminal = terminal
        self._cavity = cavity
        self._for_cavity = for_cavity
        self.mainframe = mainframe

        # Compute pre-filter part numbers before opening the dialog.
        if housing is not None and not for_cavity:
            compat_pns = housing.db_obj.part.compat_seals_array

        elif terminal is not None:
            compat_pns = [s.part_number for s in terminal.db_obj.part.compat_seals]

        elif cavity is not None:
            g_cav = cavity.db_obj.part
            max_dim = max(g_cav.width or 0.0, g_cav.height or 0.0)
            compat_pns = self._cavity_plug_pns(max_dim)

        elif housing is not None and for_cavity:
            max_dim = 0.0
            for g_cav in housing.db_obj.part.cavities:
                max_dim = max(max_dim, g_cav.width or 0.0, g_cav.height or 0.0)

            compat_pns = self._cavity_plug_pns(max_dim)

        else:
            compat_pns = []

        # Free mode (no target given) can pick up the editor's current selection.
        if housing is None and terminal is None and cavity is None:
            part_id = mainframe.editor_db.editor.seals.GetSelection()
        else:
            part_id = None

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SealsPage, title='Add Seal',
                table=mainframe.global_db.seals_table,
                initial_results=compat_pns)

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

        self._snap_targets: list = []
        self._snapped = None
        self._is_dummy_pin: bool = False
        self.part: "_db_seal.Seal" = None

        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

    @staticmethod
    def _cavity_midpoint(pjt_cavity):
        """
        Return world-space midpoint of *pjt_cavity* along its insertion axis.
        """

        cpos_np = pjt_cavity.position3d.as_numpy.astype(np.float64)
        cav_ang = pjt_cavity.angle3d
        length = float(pjt_cavity.part.length)
        ref_local = np.array([[0.0, 0.0, length]], dtype=np.float64)
        ref_world = np.asarray(ref_local @ cav_ang, dtype=np.float64)[0] + cpos_np
        mid = (cpos_np + ref_world) / 2.0

        return float(mid[0]), float(mid[1]), float(mid[2])

    def _cavity_plug_pns(self, max_dim):
        """
        Return PLUG and dummy-pin seal part numbers whose dimensions fit max_dim.
        """

        if max_dim <= 0.0:
            return []

        self.mainframe.global_db.seals_table.execute(
            'SELECT DISTINCT s.part_number FROM seals s '
            'JOIN seal_types st ON s.type_id = st.id '
            'WHERE (UPPER(st.name) = "PLUG" OR UPPER(st.name) = "DUMMY PIN") '
            'AND (s.width <= ? OR s.o_dia <= ?);',
            (max_dim, max_dim))

        return [row[0] for row in self.mainframe.global_db.seals_table.fetchall()]

    def set_part(self, part_id: int):
        if self.obj is not None:
            self.obj.delete()

        self.part = self.ptables.global_db.seals_table[part_id]
        name = f'{self.part.manufacturer.name} {self.part.part_number}'
        type_name = self.part.type.name.lower()
        self._is_dummy_pin = 'dummy' in type_name

        if self._housing is not None and not self._for_cavity:
            # Mode 1a: MAT seal on housing – instant attach at the seal slot.
            pos_id = self._housing.db_obj.seal_position3d_id

            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, name, pos_id, self._housing.db_obj.db_id,
                None, None)

        elif self._terminal is not None:
            # Mode 2: SWS on terminal – instant at cavity midpoint.
            pjt_cavity = self._terminal.db_obj.cavity
            if pjt_cavity is not None:
                tx, ty, tz = self._cavity_midpoint(pjt_cavity)
            else:
                tx, ty, tz = self._terminal.db_obj.position3d.as_float

            p3d = self.ptables.pjt_points3d_table.insert(tx, ty, tz)

            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, name, p3d.db_id, None,
                self._terminal.db_obj.db_id, None)

        elif self._cavity is not None:
            # Mode 3: PLUG or dummy pin on cavity – instant.
            pjt_cavity = self._cavity.db_obj
            if self._is_dummy_pin:
                gender = pjt_cavity.housing.part.gender.name.lower()
                if gender == 'male':
                    tx, ty, tz = pjt_cavity.position3d.as_float
                else:
                    tx, ty, tz = self._cavity_midpoint(pjt_cavity)
            else:
                tx, ty, tz = self._cavity_midpoint(pjt_cavity)

            p3d = self.ptables.pjt_points3d_table.insert(tx, ty, tz)

            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, name, p3d.db_id, None,
                None, pjt_cavity.db_id)

        elif self._housing is not None and self._for_cavity:
            # Mode 1b: interactive preview locked to this housing's cavities.
            housing_db_id = self._housing.db_obj.db_id
            for cav in self.mainframe.project.cavities:
                if cav.db_obj.housing.db_id != housing_db_id:
                    continue

                if cav.db_obj.terminal is not None:
                    continue

                cav.identify(self._compat_highlight_material)
                self._snap_targets.append(cav)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)

            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, name, pos_obj.db_id, None,
                None, None)

        else:
            # Mode 4: free interactive – target type depends on seal type.
            compat_pns_h = set(self.part.compat_housings_array)
            compat_pns_t = set(self.part.compat_terminals_array)
            is_sws = type_name in ('sws', 'single wire seal')
            is_mat = type_name == 'mat'

            if is_sws:
                for t in self.mainframe.project.terminals:
                    if not t.db_obj.part.sealing:
                        continue

                    if t.db_obj.part.part_number in compat_pns_t:
                        t.identify(self._compat_highlight_material)
                    else:
                        t.identify(self._highlight_material)

                    self._snap_targets.append(t)

            elif is_mat:
                for h in self.mainframe.project.housings:
                    if not h.db_obj.part.sealing:
                        continue

                    if h.db_obj.part.part_number in compat_pns_h:
                        h.identify(self._compat_highlight_material)
                    else:
                        h.identify(self._highlight_material)

                    self._snap_targets.append(h)

            else:  # PLUG or dummy pin
                for cav in self.mainframe.project.cavities:
                    if cav.db_obj.terminal is not None:
                        continue

                    if cav.db_obj.housing.part.part_number in compat_pns_h:
                        cav.identify(self._compat_highlight_material)
                    else:
                        cav.identify(self._highlight_material)

                    self._snap_targets.append(cav)

            pos_obj = self.ptables.pjt_points3d_table.insert(0, 0, 0)

            db_obj = self.ptables.pjt_seals_table.insert(
                part_id, name, pos_obj.db_id, None,
                None, None)

        self.obj = _seal.Seal(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)

        if self._housing is not None and not self._for_cavity:
            self.set_angle_from_housing(self.obj, self._housing)
        elif self._terminal is not None:
            pjt_cavity = self._terminal.db_obj.cavity
            if pjt_cavity is not None:
                self.set_angle_from_cavity(self.obj, pjt_cavity)
        elif self._cavity is not None:
            self.set_angle_from_cavity(self.obj, self._cavity.db_obj)

    @property
    def snap_pool(self):
        objects = []
        positions = []
        for target in self._snap_targets:
            if not target.is_in_3dview:
                continue

            if isinstance(target, _housing.Housing):
                positions.append(target.db_obj.seal_position3d)
            elif isinstance(target, _terminal.Terminal):
                pjt_cav = target.db_obj.cavity
                if pjt_cav is not None:
                    x, y, z = self._cavity_midpoint(pjt_cav)
                    positions.append(_point.Point(x, y, z))
                else:
                    positions.append(target.db_obj.position3d)

            else:  # Cavity
                pjt_cav = target.db_obj
                if self._is_dummy_pin:
                    gender = pjt_cav.housing.part.gender.name.lower()

                    if gender == 'male':
                        x, y, z = pjt_cav.position3d.as_float
                    else:
                        x, y, z = self._cavity_midpoint(pjt_cav)
                else:
                    x, y, z = self._cavity_midpoint(pjt_cav)

                positions.append(_point.Point(x, y, z))

            objects.append(target)

        return _utils.SnapPool(objects, positions)

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        # Instant-attach modes have no hover interaction.
        is_interactive = (
            self._for_cavity or
            (self._housing is None and self._terminal is None
             and self._cavity is None)
        )

        if not is_interactive:
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
            if isinstance(snapped, _housing.Housing):
                point = snapped.db_obj.seal_position3d
                if prev_snapped is not snapped:
                    self.set_angle_from_housing(self.obj, snapped)

            elif isinstance(snapped, _terminal.Terminal):
                pjt_cav = snapped.db_obj.cavity
                if pjt_cav is not None:
                    x, y, z = self._cavity_midpoint(pjt_cav)
                    point = _point.Point(x, y, z)
                    if prev_snapped is not snapped:
                        self.set_angle_from_cavity(self.obj, pjt_cav)
                else:
                    point = snapped.db_obj.position3d
                    if prev_snapped is not snapped:
                        self.reset_angle(self.obj)

            else:  # Cavity
                pjt_cav = snapped.db_obj
                if self._is_dummy_pin:
                    gender = pjt_cav.housing.part.gender.name.lower()

                    if gender == 'male':
                        x, y, z = pjt_cav.position3d.as_float
                    else:
                        x, y, z = self._cavity_midpoint(pjt_cav)
                else:
                    x, y, z = self._cavity_midpoint(pjt_cav)

                point = _point.Point(x, y, z)

                if prev_snapped is not snapped:
                    self.set_angle_from_cavity(self.obj, pjt_cav)

            self._snapped = snapped

        position = self.obj.db_obj.position3d
        delta = point - position
        position += delta

    def release_capture(self) -> None:
        if self._finalized:
            return

        if self._captured_position is None:
            return

        # Instant-attach modes: set_part already created the DB record at the
        # correct position; just register the seal with the project.
        is_instant = (
            (self._housing is not None and not self._for_cavity)
            or self._terminal is not None
            or self._cavity is not None
        )

        if not is_instant:
            if self._snapped is None:
                return

            if isinstance(self._snapped, _housing.Housing):
                for h in self.mainframe.project.housings:
                    h.identify(None)

                # Attach the preview position to the housing's seal slot so
                # the seal follows any future housing transforms.
                self._snapped.db_obj.seal_position3d.attach(
                    self.obj.db_obj.position3d)

                self.obj.db_obj.housing_id = self._snapped.db_obj.db_id
                self.set_angle_from_housing(self.obj, self._snapped)

            elif isinstance(self._snapped, _terminal.Terminal):
                for t in self.mainframe.project.terminals:
                    t.identify(None)

                pjt_cav = self._snapped.db_obj.cavity
                if pjt_cav is not None:
                    self.set_angle_from_cavity(self.obj, pjt_cav)

                self.obj.db_obj.terminal_id = self._snapped.db_obj.db_id

            else:  # Cavity
                for cav in self.mainframe.project.cavities:
                    cav.identify(None)

                self.set_angle_from_cavity(self.obj, self._snapped.db_obj)
                self.obj.db_obj.cavity_id = self._snapped.db_obj.db_id

        self._finalized = True
        self.mainframe.project.add_seal(self.obj)
        self.obj = None
