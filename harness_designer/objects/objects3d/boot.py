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
        if model is not None:
            uuid = model.uuid
            scale = self._part.scale
            color = self._part.color.ui
            material = _materials.Rubber(color)
            angle = db_obj.angle3d

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_boots:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            vbo = _sphere.create_vbo()
            scale = _point.Point(3.0, 3.0, 3.0)
            angle = _angle.Angle()

            material = _materials.Metallic(_color.Color(0.6, 0.2, 0.2, 1.0))

        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

        parent.mainframe.editor3d.context.release()

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
