# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import uuid as _uuid_module
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
from ...shapes import text as _text


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


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
        material = _materials.Plastic(color)

        # This note's own id into shapes.text's VBO registry -- generated
        # and owned here (not by shapes/text.py, which has no single "unit"
        # text shape to cache), exactly like a catalog part's Model3D.uuid
        # keys its own PooledVBOHandler (see Base3D._set_model).
        self._text_uuid = str(_uuid_module.uuid4())

        parent.mainframe.editor3d.context.acquire()
        vbo, _width, _height = self._build()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)
        parent.mainframe.editor3d.context.release()

    def _mesh_args(self) -> dict:
        """Current ``shapes.text.create``/``create_vbo`` args, from this
        note's live db_obj fields. ``depth=0.25`` extrudes the text
        upright (real 3D thickness) -- unlike the 2D schematic editor's
        flat labels, a note needs to be visible from any angle in the 3D
        scene.
        """
        return dict(
            text=self.db_obj.notes,
            font_size=self.db_obj.size3d,
            depth=0.25,
            font_style=build123d.FontStyle(self.db_obj.style3d),
            text_align=[build123d.TextAlign(self.db_obj.h_align3d), build123d.TextAlign.CENTER],
        )

    def _build(self):
        """Build this note's VBO (construction time only -- see
        :meth:`_rebuild` for in-place content updates).

        :returns: ``(vbo, width, height)``.
        """
        return _text.create_vbo(self._text_uuid, **self._mesh_args())

    def _rebuild(self):
        """Rebuild this note's mesh in place from its current db_obj
        fields and upload it to the existing VBO -- called by every
        ``set_*`` method below.
        """
        vertices, faces, _width, _height = _text.create(**self._mesh_args())
        packed, count = _utils.compute_normals(vertices, faces)
        self._vbo.update(packed, count)

    def set_size(self, size):
        self.db_obj.size3d = size

        self.editor3d.context.acquire()
        self._rebuild()
        self.editor3d.context.release()
        self.editor3d.Refresh()

    def set_style(self, style):
        self.db_obj.style3d = style

        self.editor3d.context.acquire()
        self._rebuild()
        self.editor3d.context.release()
        self.editor3d.Refresh()

    def set_alignment(self, alignment):
        self.db_obj.h_align3d = alignment

        self.editor3d.context.acquire()
        self._rebuild()
        self.editor3d.context.release()
        self.editor3d.Refresh()

    def set_text(self, text: str):
        """Set the note text and rebuild the 3d geometry."""
        self.db_obj.notes = text

        self.editor3d.context.acquire()
        self._rebuild()
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
        _menu_ops.delete_object(self.selected)

    def on_properties(self):
        """Show this note's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
