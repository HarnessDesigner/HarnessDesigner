# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


Config = _config.Config.editor3d


class Boot(_base3d.Base3D):
    """Represent a boot in :mod:`harness_designer.objects.objects3d.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_boot.Boot" = None
    db_obj: "_pjt_boot.PJTBoot" = None

    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        """Initialise the :class:`Boot` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_boot.Boot`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_boot.PJTBoot`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d

        vbo = _sphere.create_vbo()
        vbo.acquire()

        scale = _point.Point(3.0, 3.0, 3.0)
        material = _materials.Rubber(self._part.color.ui)
        angle = db_obj.angle3d

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d,
                                scale, material)

        parent.mainframe.editor3d.context.release()

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @property
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_boots

        return smooth

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return BootMenu(self.mainframe.editor3d.editor, self)


class BootMenu(QMenu):
    """Represent a boot menu in :mod:`harness_designer.objects.objects3d.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`BootMenu` instance.

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
        """Make this boot the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this boot as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this boot from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_boot)

    def on_properties(self):
        """Show this boot's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
