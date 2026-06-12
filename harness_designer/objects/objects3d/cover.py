# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import box as _box
from ...ui.widgets import float_ctrl as _float_ctrl
from ...ui.dialogs import error as _error_dialog
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_cover as _pjt_cover
    from .. import cover as _cover


Config = _config.Config.editor3d


class Cover(_base3d.Base3D):
    """Represent a cover in :mod:`harness_designer.objects.objects3d.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_cover.Cover" = None
    db_obj: "_pjt_cover.PJTCover" = None

    def __init__(self, parent: "_cover.Cover", db_obj: "_pjt_cover.PJTCover"):
        """Initialise the :class:`Cover` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cover.Cover`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cover.PJTCover`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d

        vbo = _box.create_vbo()
        vbo.acquire()

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

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return CoverMenu(self.mainframe.editor3d.editor, self)


class CoverMenu(QMenu):
    """Represent a cover menu in :mod:`harness_designer.objects.objects3d.cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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

    def on_select(self):
        """Make this cover the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this cover as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this cover from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_cover)

    def on_properties(self):
        """Show this cover's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
