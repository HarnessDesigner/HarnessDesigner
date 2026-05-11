# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


class Note(_base2d.Base2D):
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        _base2d.Base2D.__init__(self, parent, db_obj)

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle2d

        self._color = db_obj.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)


class NoteMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
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
