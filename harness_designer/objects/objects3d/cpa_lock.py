# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_cpa_lock as _pjt_cpa_lock
    from .. import cpa_lock as _cpa_lock


Config = _config.Config.editor3d


class CPALock(_base3d.Base3D):
    """Represent a CPA lock in :mod:`harness_designer.objects.objects3d.cpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_cpa_lock.CPALock" = None
    db_obj: "_pjt_cpa_lock.PJTCPALock" = None

    def __init__(self, parent: "_cpa_lock.CPALock", db_obj: "_pjt_cpa_lock.PJTCPALock"):
        """Initialise the :class:`CPALock` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cpa_lock.CPALock`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cpa_lock.PJTCPALock`
        """
        parent.mainframe.editor3d.context.acquire()
        self._part = db_obj.part

        model = self._part.model3d
        vbo = None
        if model is not None:
            scale = _point.Point(1.0, 1.0, 1.0)
            color = self._part.color.ui
            material = _materials.Plastic(color)
            angle = db_obj.angle3d

            vbo = _vbo.create_model_vbo(model)

        if vbo is None:
            vbo = _sphere.create_vbo()
            scale = _point.Point(3.0, 3.0, 3.0)
            angle = _angle.Angle()

            material = _materials.Metallic([0.2, 0.6, 0.6, 1.0])

        vbo.acquire()
        normal_mode = 0 if Config.renderer.smooth_cpa_locks else 1
        _base3d.Base3D.__init__(
            self,
            parent,
            db_obj,
            vbo,
            angle,
            db_obj.position3d,
            scale,
            material,
            normal_mode=normal_mode
        )
        parent.mainframe.editor3d.context.release()


    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return CPALockMenu(self.mainframe.editor3d.editor, self)


class CPALockMenu(QMenu):
    """Represent a CPA lock menu in :mod:`harness_designer.objects.objects3d.cpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`CPALockMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
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
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
