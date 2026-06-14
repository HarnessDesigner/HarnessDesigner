# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...ui.widgets import context_menus as _context_menus
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...gl import materials as _materials
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


_ALIGN_MAPPING = {
    build123d.TextAlign.LEFT.value: build123d.TextAlign.LEFT,
    build123d.TextAlign.CENTER.value: build123d.TextAlign.CENTER,
    build123d.TextAlign.RIGHT.value: build123d.TextAlign.RIGHT,
}


class Note(_base3d.Base3D):
    """Represent a note in :mod:`harness_designer.objects.objects3d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote" = None

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        """Initialise the :class:`Note` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_note.Note`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """
        self.db_obj = db_obj
        angle = db_obj.angle3d
        position = db_obj.position3d
        color = db_obj.color.ui
        scale = _point.Point(1.0, 1.0, 1.0)
        data = self._build()

        material = _materials.Plastic(color)

        _base3d.Base3D.__init__(self, parent, db_obj, None, angle,
                                position, scale, material, data)

    def _build(self):
        """Execute the build operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        model = build123d.Text(
            self.db_obj.notes, font_size=self.db_obj.size3d,
            font_style=build123d.FontStyle(self.db_obj.style3d),
            text_align=[build123d.TextAlign(self.db_obj.h_align3d), build123d.TextAlign.CENTER])

        model = build123d.extrude(model, 0.25)
        vertices, faces = _utils.convert_model_to_mesh(model)
        packed, count = _utils.compute_normals(vertices, faces)

        return packed, count

    def set_text(self, text: str):
        """Set the note text and rebuild the 3d geometry."""
        self.db_obj.notes = text

        self.editor3d.context.acquire()

        self._gl_buf.update(*self._build())

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.context.release()
        self.editor3d.Refresh()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return NoteMenu(self.mainframe.editor3d.editor, self)


class NoteMenu(QMenu):
    """Represent a note menu in :mod:`harness_designer.objects.objects3d.note`.

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

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
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
        """Edit the note text."""
        def _do():
            from PySide6.QtWidgets import QInputDialog

            mainframe = self.selected.mainframe
            current = self.selected.db_obj.notes

            text, ok = QInputDialog.getMultiLineText(
                mainframe, 'Set Text', 'Note:', current)

            if not ok or not text or text == current:
                return

            self.selected.set_text(text)

        QTimer.singleShot(0, _do)

    def on_clone(self):
        """Arm clone mode using this note as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this note from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_note)

    def on_properties(self):
        """Show this note's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
