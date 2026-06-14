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
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock


Config = _config.Config.editor3d


class TPALock(_base3d.Base3D):
    """Represent a TPA lock in :mod:`harness_designer.objects.objects3d.tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_tpa_lock.TPALock" = None
    db_obj: "_pjt_tpa_lock.PJTTPALock" = None

    def __init__(self, parent: "_tpa_lock.TPALock", db_obj: "_pjt_tpa_lock.PJTTPALock"):
        """Initialise the :class:`TPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_tpa_lock.TPALock`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_tpa_lock.PJTTPALock`
        """

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d

        vbo = _sphere.create_vbo()

        scale = _point.Point(3.0, 3.0, 3.0)
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
        return TPALockMenu(self.mainframe.editor3d.editor, self)


class TPALockMenu(QMenu):
    """Represent a TPA lock menu in :mod:`harness_designer.objects.objects3d.tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`TPALockMenu` instance.

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
        """Make this TPA lock the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this TPA lock as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this TPA lock from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_tpa_lock)

    def on_properties(self):
        """Show this TPA lock's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
