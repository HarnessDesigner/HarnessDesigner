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
    """Represent a note in :mod:`harness_designer.objects.objects2d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        """Initialise the :class:`Note` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_note.Note`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """

        position = db_obj.position2d
        angle = db_obj.angle2d

        _base2d.Base2D.__init__(self, parent, db_obj, position=position, angle=angle)

    def set_size(self, size):
        self.db_obj.size2d = size

        self.editor2d.context.acquire()
        self._vbo.update(*self._build())
        self.editor2d.context.release()
        self.editor2d.Refresh()

    def set_style(self, style):
        self.db_obj.style2d = style

        self.editor2d.context.acquire()
        self._vbo.update(*self._build())
        self.editor2d.context.release()
        self.editor2d.Refresh()

    def set_alignment(self, alignment):
        self.db_obj.h_align2d = alignment

        self.editor2d.context.acquire()
        self._vbo.update(*self._build())
        self.editor2d.context.release()
        self.editor2d.Refresh()

    def set_text(self, text: str):
        """Set the note text and rebuild the 3d geometry."""
        self.db_obj.notes = text

        self.editor2d.context.acquire()
        self._vbo.update(*self._build())
        self.editor2d.context.release()
        self.editor2d.Refresh()


class NoteMenu(QMenu):
    """Represent a note menu in :mod:`harness_designer.objects.objects2d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`NoteMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
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
        """Handle the set text event.

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
