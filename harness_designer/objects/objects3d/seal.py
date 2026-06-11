# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
import build123d

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


Config = _config.Config.editor3d


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
    i_length = round(length * 1.10, 6)
    move_dist = round((i_length - length) / 2.0, 6)

    model = build123d.Cylinder(o_radius, length)
    hole = build123d.Cylinder(i_radius, i_length)
    hole = hole.move(build123d.Location())
    hole.position -= (0.0, 0.0, -move_dist)
    model -= hole

    vertices, faces = _utils.convert_model_to_mesh(model)
    return vertices, faces


class Seal(_base3d.Base3D):
    """Represent a seal in :mod:`harness_designer.objects.objects3d.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_seal.Seal" = None
    db_obj: "_pjt_seal.PJTSeal" = None

    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        """Initialise the :class:`Seal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_seal.Seal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_seal.PJTSeal`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        model = self._part.model3d
        type_ = self._part.type.name

        if type_.lower() in ('sws', 'single wire seal'):
            vbo_id = self._part.manufacturer.name
            vbo_id += ':' + self._part.part_number

            length = self._part.length
            o_dia = self._part.o_dia
            scale = _point.Point(o_dia, o_dia, length)

            if vbo_id in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(vbo_id)
            else:
                i_dia = self._part.i_dia
                vertices, faces = _build_sws(length, o_dia, i_dia)

                packed, count = _utils.compute_normals(vertices, faces)

                vbo = _vbo.VBOHandler(vbo_id, packed, count)
        elif type_.lower() == 'plug':
            vbo = _cylinder.create_vbo()
            length = self._part.length
            o_dia = self._part.o_dia
            scale = _point.Point(o_dia, o_dia, length)
        else:
            vbo = _box.create_vbo()
            scale = _point.Point(self._part.width, self._part.height, self._part.length)

        vbo.acquire()

        material = _materials.Rubber(self._part.color.ui)
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
        return SealMenu(self.mainframe.editor3d.editor, self)


class SealMenu(QMenu):
    """Represent a seal menu in :mod:`harness_designer.objects.objects3d.seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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
