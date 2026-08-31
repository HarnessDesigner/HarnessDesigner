# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import box as _box
from ...ui.widgets import float_ctrl as _float_ctrl
from ...ui.dialogs import error as _error_dialog
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cover as _pjt_cover
    from .. import cover as _cover
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor_3d


class Cover(_base_3d.Base3D):
    """Represent a cover in :mod:`harness_designer.objects.objects_3d.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_cover.Cover" = None
    db_obj: "_pjt_cover.PJTCover" = None

    @_check_types.do
    def __init__(self, parent: "_cover.Cover", db_obj: "_pjt_cover.PJTCover"):
        """Initialise the :class:`Cover` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cover.Cover`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cover.PJTCover`
        """
        with parent.mainframe.editor3d.context:
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

            super().__init__(parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", housing: "_housing.Housing | None" = None
    ) -> "_cover.Cover | None":
        """Ported from handlers.cover_handler.AddCoverHandler -- always
        interactive (even the housing-given case waits for a confirming
        click, it just has nothing to move -- see
        add_handlers.editor_3d.cover.Cover).
        """
        from ...handlers import handler_base as _handler_base
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_3d import cover as _add_cover
        from .. import cover as _cover_facade
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor3d.editor

        compat_covers = [] if housing is None else housing.db_obj.part.compat_covers_array

        part_id = mainframe.editor_db.editor.covers.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.CoversPage, title='Add Cover',
                table=mainframe.global_db.covers_table, initial_results=compat_covers)
            part_id = dlg.GetValue() if dlg.exec() == QDialog.DialogCode.Accepted else None
            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.covers_table[part_id]

        from ...ui.dialogs.dimensions_dialog import ensure_dimensions
        if not ensure_dimensions(mainframe, part, part.part_number):
            return None

        name = f'{part.manufacturer.name} {part.part_number}'

        preview_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.housing_highlight))
        compat_highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.splice_highlight))

        project_housings = []

        if housing is None:
            compat_housings = ptables.global_db.housings_table.get_compat(
                cover=part.part_number)
            compat_housings.extend(part.compat_housings)
            compat_housings = list(set(compat_housings))

            for h in mainframe.project.housings:
                if h.db_obj.cover is not None:
                    continue

                if h.db_obj.part.part_number in compat_housings:
                    h.identify(compat_highlight_material)
                else:
                    h.identify(highlight_material)

                project_housings.append(h)

            pos_obj = ptables.pjt_points3d_table.insert(0, 0, 0)
            db_obj = ptables.pjt_covers_table.insert(part_id, name, pos_obj.db_id, None)
        else:
            pos_id = housing.db_obj.cover_position3d_id
            db_obj = ptables.pjt_covers_table.insert(
                part_id, name, pos_id, housing.db_obj.db_id)

        facade = _cover_facade.Cover(mainframe, db_obj)
        facade.identify(preview_material)

        if housing is not None:
            _handler_base.HandlerBase.set_angle_from_housing(facade, housing)

        handler = _add_cover.Cover(canvas, facade, housing, project_housings)
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
        from ...add_handlers.editor_3d import cover as _add_cover  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_cover.Cover):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_covers

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return CoverMenu(self.mainframe.editor3d.editor, self)


class CoverMenu(QMenu):
    """Represent a cover menu in :mod:`harness_designer.objects.objects_3d.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`CoverMenu` instance.

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
        """Make this cover the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this cover as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this cover from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this cover's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
