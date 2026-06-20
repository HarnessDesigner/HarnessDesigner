# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import numpy as np

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...ui.dialogs import housing_editor as _housing_editor
from ...ui.widgets import float_ctrl as _float_ctrl
from ...ui.dialogs import error as _error_dialog
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from . import housing_cavity_picker as _housing_cavity_picker
from ...shapes import box as _box
from ...gl import materials as _materials
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor3d


class Housing(_base3d.Base3D):
    """Represent a housing in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d

        vbo = _box.create_vbo()

        width = self._part.width
        height = self._part.height
        length = self._part.length

        if 0.0 in (length, width, height):
            length_ctrl = _float_ctrl.FloatCtrl(
                None, 'Length', 0.00, 500.0, 0.01)

            width_ctrl = _float_ctrl.FloatCtrl(
                None, 'Width', 0.00, 500.0, 0.01)

            height_ctrl = _float_ctrl.FloatCtrl(
                None, 'Height', 0.00, 500.0, 0.01)

            length_ctrl.SetValue(length)
            width_ctrl.SetValue(width)
            height_ctrl.SetValue(height)

            dlg = _error_dialog.ErrorDialog(
                parent.mainframe,
                'Dimensions are not valid.\n\nPlease set correct dimensions.',
                'Dimension Error', length_ctrl, width_ctrl, height_ctrl)

            while 0.0 in (length, width, height):
                dlg.exec()
                length = length_ctrl.GetValue()
                width = width_ctrl.GetValue()
                height = height_ctrl.GetValue()

            db_obj.length = length
            db_obj.width = width
            db_obj.height = height

        scale = _point.Point(width, height, length)
        material = _materials.Plastic(self._part.color.ui)
        angle = db_obj.angle3d

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, db_obj.position3d,
            scale, material)

        parent.mainframe.editor3d.context.release()

        # Cavity picking is always active — no prior housing selection needed.
        # Created after context.release() so no GL context is current while
        # the overlay QWidget and event-filter QObject are constructed.
        self._cavity_picker = _housing_cavity_picker.HousingCavityPicker(self)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    def _set_model(self, model):
        super()._set_model(model)

        for cavity in self._part.cavities:
            if cavity is not None:
                break
        else:
            from ...ui.dialogs import housing_editor

            dlg = housing_editor.HousingEditorDialog(self.parent.mainframe)
            dlg.SetValue(self._part)
            dlg.exec()
            dlg.deleteLater()

        # Rebuild the picker's surface data with the real mesh geometry now
        # that the 3D model has loaded (replaces the placeholder box surfaces).
        self._cavity_picker.update_vbo()

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.seal_position3d

    def try_pick_cavity(self, x: int, y: int):
        """Ray-cast at pixel (x, y) and return (global_cavity, surf_idx).

        Returns (None, -1) when no surface or no matching cavity is found.
        Does not modify overlay state — callers decide whether to show or clear.
        """
        if self._cavity_picker is None:
            return None, None, -1

        picker = self._cavity_picker
        origin, direction = picker.compute_ray(x, y)

        if origin is None:
            return None, None, -1

        idx, hit_point = picker.pick_surface_at_ray(origin, direction)
        if idx < 0:
            return None, None, -1

        global_cavity = picker.match_cavity(origin, direction)

        for cavity in self.db_obj.cavities:
            if cavity.part_id == global_cavity.db_id:
                break
        else:
            raise RuntimeError('sanity check (this should not happen)')

        return cavity, global_cavity, idx

    def show_cavity_overlay(self, surf_idx: int, global_cavity=None) -> None:
        """Highlight the cavity plane at surf_idx and record global_cavity."""

        self._cavity_picker.selected_surf_idx = surf_idx
        self._cavity_picker.selected_cavity = global_cavity

        if global_cavity is not None:
            self._cavity_picker.set_active()

        if self._cavity_picker.overlay is not None:
            self._cavity_picker.overlay.update()

    def clear_cavity_overlay(self) -> None:
        """Hide any active cavity-plane highlight for this housing."""
        if self._cavity_picker is not None:
            self._cavity_picker.clear_selection()

    def delete(self):
        """Clean up the cavity picker before delegating to Base3D."""
        self._cavity_picker.cleanup()
        self._cavity_picker = None
        super().delete()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return HousingMenu(self.mainframe, self)


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_ui.MainFrame", obj: Housing):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param obj: Object instance to operate on.
        :type obj: :class:`Housing`
        """
        QMenu.__init__(self)
        self.mainframe = mainframe
        self.canvas = mainframe.editor3d.editor
        self.obj = obj

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(self.canvas, obj.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(self.canvas, obj.parent)
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

        action = self.addAction('Housing Editor')
        action.triggered.connect(self.on_housing_editor)

    def on_housing_editor(self):
        """Handle the housing editor event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: UNKNOWN
            """
            dlg = _housing_editor.HousingEditorDialog(self.mainframe)

            QTimer.singleShot(0, lambda: dlg.SetValue(housing))

            dlg.exec()

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj.part))

    def on_add_seal(self):
        """Attach a seal to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(self.mainframe, housing))

    def on_add_terminal(self):
        """Add a terminal to this housing."""
        def _do():
            from .. import terminal as _terminal_obj

            part_id = _menu_ops.get_part_id(
                self.mainframe, 'terminals',
                self.mainframe.global_db.terminals_table, 'Add Terminal')

            if part_id is None:
                return

            position = self.obj.db_obj.position3d
            ptables = self.mainframe.project.ptables

            p3d = ptables.pjt_points3d_table.insert(*position.as_float)

            terminal_db = ptables.pjt_terminals_table.insert(
                part_id, None, p3d.db_id, None)

            terminal = _terminal_obj.Terminal(self.mainframe, terminal_db)
            self.mainframe.project.add_terminal(terminal)

        QTimer.singleShot(0, _do)

    def on_add_cpa_lock(self):
        """Attach a CPA lock to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddCPALockHandler(self.mainframe, housing))

    def on_add_tpa_lock(self):
        """Attach a TPA lock to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddTPALockHandler(self.mainframe, housing))

    def on_add_cover(self):
        """Attach a cover to this housing."""
        from ... import handlers as _handlers

        housing = self.obj.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddCoverHandler(self.mainframe, housing))

    def on_add_boot(self):
        """Attach a boot to this housing."""
        def _do():
            from .. import boot as _boot_obj

            housing = self.obj.db_obj

            try:
                compat_boots = housing.part.compat_boots_array
            except AttributeError:
                compat_boots = []

            part_id = _menu_ops.get_part_id(
                self.mainframe, 'boots',
                self.mainframe.global_db.boots_table, 'Add Boot',
                initial_results=compat_boots)

            if part_id is None:
                return

            db_obj = self.mainframe.project.ptables.pjt_boots_table.insert(
                part_id, housing.boot_position3d_id, housing.db_id)

            from ...handlers import handler_base as _handler_base
            _handler_base.set_angle_from_housing(db_obj, housing)

            boot = _boot_obj.Boot(self.mainframe, db_obj)
            self.mainframe.project.add_boot(boot)

        QTimer.singleShot(0, _do)

    def on_select(self):
        """Make this housing the active selection."""
        _menu_ops.select_object(self.obj)

    def on_clone(self):
        """Arm clone mode using this housing as the template."""
        _menu_ops.clone_object(self.obj)

    def on_delete(self):
        """Delete this housing from the project."""
        _menu_ops.delete_object(
            self.obj, self.mainframe.project.delete_housing)

    def on_properties(self):
        """Show this housing's properties in the object editor."""
        _menu_ops.show_properties(self.obj)
