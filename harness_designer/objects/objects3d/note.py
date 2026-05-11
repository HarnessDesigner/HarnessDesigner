# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QMenu
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...ui.widgets import context_menus as _context_menus
from . import base3d as _base3d
from ...gl import materials as _materials
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


class Note(_base3d.Base3D):
    parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote" = None

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        self.db_obj = db_obj
        self.angle = db_obj.angle3d
        self.position = db_obj.position3d
        color = db_obj.color.ui
        scale = _point.Point(0.0, 0.0, 0.0)
        data = self._build()

        material = _materials.Plastic(color)
        # db_obj.h_align3d
        # db_obj.v_align3d

        _base3d.Base3D.__init__(self, parent, db_obj, None, self.angle,
                                self.position, scale, material, data)

    def _build(self):
        model = build123d.Text(self.db_obj.note, font_size=self.db_obj.size3d, font_style=self.db_obj.style3d)
        model = build123d.extrude(model, 0.25)
        vertices, faces = _utils.convert_model_to_mesh(model)
        vertices, normals, count = _utils.compute_vertex_normals(vertices, faces)

        vertices @= self.angle
        normals @= self.angle
        vertices += self.position

        return vertices, normals, count

    def get_context_menu(self):
        return NoteMenu(self.mainframe.editor3d.editor, self)


class NoteMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        action = self.addAction('Set Text')
        action.triggered.connect(self.on_set_text)

        self.addSeparator()

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_set_text(self):
        pass

    def on_clone(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
