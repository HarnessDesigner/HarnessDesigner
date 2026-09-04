# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtWidgets import QMenu
import build123d

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal
    from .. import housing as _housing_facade
    from .. import terminal as _terminal_facade
    from .. import cavity as _cavity_facade
    from ... import ui as _ui


Config = _config.Config.editor_3d


@_check_types.do
def _build_sws(length, o_dia, i_dia):
    """Build the sws.

    UNKNOWN details are inferred from the callable name and signature.

    :param length: Value for ``length``.
    :type length: UNKNOWN
    :param o_dia: Value for ``o_dia``.
    :type o_dia: UNKNOWN
    :param i_dia: Value for ``i_dia``.
    :type i_dia: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    o_radius = round(o_dia / 2.0, 6)
    i_radius = round(i_dia / 2.0, 6)

    model1 = build123d.Cylinder(o_radius, length)
    hole1 = build123d.Cylinder(i_radius, length)
    model1 -= hole1

    hole_radius = o_radius * 0.66
    length *= 0.33

    model2 = build123d.Cylinder(o_radius, length)
    hole2 = build123d.Cylinder(hole_radius, length)
    model2 -= hole2

    model1 -= model2
    vertices, faces = _utils.convert_model_to_mesh(model1)
    return vertices, faces


class Seal(_base_3d.Base3D):
    """Represent a seal in :mod:`harness_designer.objects.objects_3d.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_seal.Seal" = None
    db_obj: "_pjt_seal.PJTSeal" = None

    # PooledVBOHandler's own lookup id for the SWS mesh built below (``None``
    # for Plug/box types, which use a plain shared unit primitive instead) --
    # exposed so objects_pegboard.seal.Seal can re-resolve the exact same
    # pooled VBO via PooledVBOHandler(vbo_id) rather than aliasing self._vbo
    # directly, giving it its own properly ref-counted handle on the pool.
    _vbo_id: str | None = None

    @_check_types.do
    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        """Initialise the :class:`Seal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_seal.Seal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_seal.PJTSeal`
        """
        with parent.mainframe.editor3d.context:
            self._part = db_obj.part

            model = self._part.model3d
            category = self._part.type.category

            if category == 'SWS':
                vbo_id = self._part.manufacturer.name
                vbo_id += ':' + self._part.part_number
                vbo_id += ':3d'
                self._vbo_id = vbo_id

                length = self._part.length
                o_dia = self._part.o_dia
                scale = _point.Point(1.0, 1.0, 1.0)

                if vbo_id in _vbo.PooledVBOHandler:
                    vbo = _vbo.PooledVBOHandler(vbo_id)
                else:
                    i_dia = self._part.i_dia
                    vertices, faces = _build_sws(length, o_dia, i_dia)

                    packed, count = _utils.compute_normals(vertices, faces)
                    vertices = packed[:count * 3].reshape(-1, 3)

                    aabb1, aabb2 = _utils.compute_aabb(vertices)
                    obb = _utils.compute_obb(aabb1, aabb2)
                    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)

                    vbo = _vbo.PooledVBOHandler(vbo_id, packed, count, aabb=aabb, obb=obb)

            elif category == 'PLUG':
                self._vbo_id = None
                vbo = _cylinder.create_vbo()
                length = self._part.length
                o_dia = self._part.o_dia
                scale = _point.Point(o_dia, o_dia, length)
            else:
                self._vbo_id = None
                vbo = _box.create_vbo()
                scale = _point.Point(self._part.width, self._part.height, self._part.length)

            material = _materials.Rubber(self._part.color.ui)
            angle = db_obj.angle3d

            super().__init__(parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_seals

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", housing: "_housing_facade.Housing | None" = None,
        terminal: "_terminal_facade.Terminal | None" = None,
        cavity: "_cavity_facade.Cavity | None" = None
    ) -> "_seal.Seal | None":
        """Four placement modes -- see add_handlers.editor_3d.seal's own
        module docstring; ported from handlers.seal_handler.AddSealHandler.

        *housing* alone no longer branches on a separate ``for_cavity``
        flag decided before the user even picks a part -- what the user
        actually selects in the search dialog now decides the session
        (MAT/ACC -> instant; PLUG -> this housing's own empty cavities;
        SWS -> this housing's own seated terminals), matching the
        housing "Seal" toolbar button's own design (see TODO.md's own
        "Seal placement design spec" entry for the full spec this was
        built against).
        """
        from ...handlers import handler_base as _handler_base
        from ...handlers import seal_handler as _seal_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_3d import seal as _add_seal
        from ...database.create_database import seal_types as _seal_types
        from .. import seal as _seal_facade
        from .. import housing as _housing_obj
        from .. import terminal as _terminal_obj
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor3d.editor

        if housing is not None:
            # Filtered, not the raw array -- an unset compat_seals column
            # parses to [''] (one blank entry), not [] (see
            # CompatSealsMixin.compat_seals_array's own split(', ')), and
            # an unfiltered [''] passed to SearchParameters.from_part_numbers
            # would seed an exact `part_number = ''` search (matches
            # nothing) instead of from_part_numbers correctly recognizing
            # an empty list and falling back to "show everything".
            compat_pns = [pn for pn in housing.db_obj.part.compat_seals_array if pn]
        elif terminal is not None:
            compat_pns = _seal_handler._get_terminal_seal_pns(mainframe, terminal)  # NOQA
        elif cavity is not None:
            # Housing's own compat_seals takes priority over the
            # size-based fallback (Terminals and housings alike carry
            # compat_seals; a bare cavity has none of its own).
            g_housing = cavity.db_obj.housing.part
            compat_pns = [pn for pn in g_housing.compat_seals_array if pn]

            if not compat_pns:
                g_cav = cavity.db_obj.part
                max_dim = max(g_cav.width or 0.0, g_cav.height or 0.0)
                compat_pns = _add_seal.cavity_plug_pns(mainframe, max_dim)
        else:
            compat_pns = []

        if housing is None and terminal is None and cavity is None:
            part_id = mainframe.editor_db.editor.seals.GetSelection()
        else:
            part_id = None

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SealsPage, mainframe.global_db.seals_table, 'Add Seal',
                initial_params=_part_search.SearchParameters.from_part_numbers(compat_pns))

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.seals_table[part_id]

        from ...ui.dialogs.dimensions_dialog import ensure_dimensions
        if not ensure_dimensions(mainframe, part, part.part_number):
            return None

        name = f'{part.manufacturer.name} {part.part_number}'
        type_name = part.type.name.lower()
        category = part.type.category
        is_dummy_pin = 'dummy' in type_name

        preview_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.housing_highlight))
        compat_highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.splice_highlight))
        mismatch_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.seal_size_mismatch_highlight))

        snap_targets = []

        if housing is not None and category == _seal_types.CATEGORY_PLUG:
            # This housing's own empty cavities -- one already occupied
            # by a terminal is not a valid snap target.
            for cav in housing.cavities:
                if cav.db_obj.terminal is not None:
                    continue

                cav.identify(compat_highlight_material)
                snap_targets.append(cav)

            pos_obj = ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, pos_obj.db_id, None, None, None)

        elif housing is not None and category == _seal_types.CATEGORY_SWS:
            # This housing's own terminals that are actually seated in a
            # cavity -- never a bare cavity. Flag (not block) a wire
            # size that doesn't fit this seal's own opening.
            for cav in housing.cavities:
                pjt_terminal = cav.db_obj.terminal
                if pjt_terminal is None:
                    continue

                term_obj = pjt_terminal.get_object()
                if term_obj is None:
                    continue

                if _seal_handler.wire_seal_fit_ok(mainframe, term_obj, part):
                    term_obj.identify(highlight_material)
                else:
                    term_obj.identify(mismatch_material)

                snap_targets.append(term_obj)

            pos_obj = ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, pos_obj.db_id, None, None, None)

        elif housing is not None:
            # MAT (or anything else not PLUG/SWS -- e.g. ACC) -- instant,
            # shares the housing's own seal slot point from the start.
            pos_id = housing.db_obj.seal_position3d_id
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, pos_id, housing.db_obj.db_id, None, None)

        elif terminal is not None:
            # Mode 2: SWS on terminal -- independent point seeded at the
            # terminal's current back-point coordinates (see
            # handlers.seal_handler's own set_part docstring for why this
            # is never attached/merged to the terminal's own point).
            wire_pos = terminal.db_obj.wire_position3d
            p3d = ptables.pjt_points3d_table.insert(
                float(wire_pos.x), float(wire_pos.y), float(wire_pos.z))
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, p3d.db_id, None, terminal.db_obj.db_id, None)

        elif cavity is not None:
            # Mode 3: PLUG or dummy pin on cavity.
            pjt_cavity = cavity.db_obj
            if is_dummy_pin:
                gender = pjt_cavity.housing.part.gender.name.lower()
                if gender == 'male':
                    tx, ty, tz = pjt_cavity.position3d.as_float
                else:
                    tx, ty, tz = _add_seal.cavity_midpoint(pjt_cavity)
            else:
                tx, ty, tz = _add_seal.cavity_midpoint(pjt_cavity)

            p3d = ptables.pjt_points3d_table.insert(tx, ty, tz)
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, p3d.db_id, None, None, pjt_cavity.db_id)

        else:
            # Mode 4: free interactive -- target type depends on category.
            compat_pns_h = set(part.compat_housings_array)
            compat_pns_t = set(part.compat_terminals_array)
            is_sws = category == _seal_types.CATEGORY_SWS
            is_mat = category == _seal_types.CATEGORY_MAT

            if is_sws:
                for t in mainframe.project.terminals:
                    if not t.db_obj.part.sealing:
                        continue

                    if t.db_obj.part.part_number in compat_pns_t:
                        t.identify(compat_highlight_material)
                    else:
                        t.identify(highlight_material)

                    snap_targets.append(t)

            elif is_mat:
                for h in mainframe.project.housings:
                    if not h.db_obj.part.sealing:
                        continue

                    if h.db_obj.part.part_number in compat_pns_h:
                        h.identify(compat_highlight_material)
                    else:
                        h.identify(highlight_material)

                    snap_targets.append(h)

            else:  # PLUG or dummy pin
                for cav in mainframe.project.cavities:
                    if cav.db_obj.terminal is not None:
                        continue

                    if cav.db_obj.housing.part.part_number in compat_pns_h:
                        cav.identify(compat_highlight_material)
                    else:
                        cav.identify(highlight_material)

                    snap_targets.append(cav)

            pos_obj = ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = ptables.pjt_seals_table.insert(
                part_id, name, pos_obj.db_id, None, None, None)

        # Instant == a single already-known target (housing MAT/ACC,
        # a specific terminal, or a specific cavity) -- everything else
        # (housing PLUG/SWS, or Mode 4's free placement) needs the user
        # to hover/click a snap target first.
        is_instant = (
            (housing is not None and category not in
             (_seal_types.CATEGORY_PLUG, _seal_types.CATEGORY_SWS))
            or terminal is not None
            or cavity is not None
        )

        facade = _seal_facade.Seal(mainframe, db_obj)
        facade.identify(preview_material)

        if housing is not None and is_instant:
            _handler_base.HandlerBase.set_angle_from_housing(facade, housing)
        elif terminal is not None:
            pjt_cavity = terminal.db_obj.cavity
            if pjt_cavity is not None:
                _handler_base.HandlerBase.set_angle_from_cavity(facade, pjt_cavity)
        elif cavity is not None:
            _handler_base.HandlerBase.set_angle_from_cavity(facade, cavity.db_obj)

        handler = _add_seal.Seal(
            canvas, facade, housing, terminal, cavity, is_instant, snap_targets, is_dummy_pin)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import seal as _add_seal  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_seal.Seal):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return SealMenu(self.mainframe.editor3d.editor, self)


class SealMenu(QMenu):
    """Represent a seal menu in :mod:`harness_designer.objects.objects_3d.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`SealMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_select(self):
        """Make this seal the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this seal as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this seal from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this seal's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
