# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
from OpenGL import GL
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import build123d
import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...ui.widgets import context_menus as _context_menus
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...gl import materials as _materials
from ... import utils as _utils
from ...shapes import text as _text
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


Config = _config.Config.editor_3d


class Note(_base_3d.Base3D):
    """Represent a note in :mod:`harness_designer.objects.objects_3d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote" = None

    @_check_types.do
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

        with parent.mainframe.editor3d.context:
            # No vbo of its own (None) -- this object's only visible
            # content is the Text label it owns, built/positioned below.
            super().__init__(parent, db_obj, None, angle, position, scale, material)
            self._label = self._build_label()
            self._compute_obb()
            self._compute_aabb()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_notes

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def _build_label(self) -> "_text.Text":
        """Build this note's own text label, from this note's live
        db_obj fields.

        Two real behavior changes from the old ``create()``/
        ``create_vbo()`` API, both because ``shapes.text.Text`` has no
        per-instance control over either:

        - Depth: every glyph is pre-extruded at a fixed 1.0 world unit
          (see ``shapes/text.py``'s ``build_chars()``), not the old
          ``depth=0.25`` -- notes now render thicker than they used to.
          A real per-instance depth knob would need a change to
          ``shapes/text.py`` itself, out of scope here.
        - Alignment: ``Text`` always lays out left-to-right from local
          x=0 with the baseline at local z=0, no alignment option of
          its own -- ``h_align3d``/the always-CENTER vertical alignment
          are instead applied fresh every :meth:`render` call (see
          :meth:`_alignment_offset`), same trick every other migrated
          text-owning object in this session uses.
        """
        return _text.Text(
            self.db_obj.notes, self.db_obj.size3d,
            build123d.FontStyle(self.db_obj.style3d))

    @_check_types.do
    def _alignment_offset(self) -> _point.Point:
        """Local-space anchor offset for this note's current alignment.

        Horizontal follows ``h_align3d`` (LEFT/CENTER/RIGHT); vertical
        is unconditionally CENTER -- the old ``_mesh_args()`` always
        passed ``build123d.TextAlign.CENTER`` for it, there's no
        per-note column to read instead.
        """
        h_align = build123d.TextAlign(self.db_obj.h_align3d)

        if h_align == build123d.TextAlign.CENTER:
            x = -self._label.width / 2.0
        elif h_align == build123d.TextAlign.RIGHT:
            x = -self._label.width
        else:
            x = 0.0

        z = -self._label.height / 2.0

        return _point.Point(x, 0.0, z)

    @_check_types.do
    def _compute_obb(self):
        """Derive this object's OBB from the label's own measured
        width/height -- this object has no VBO of its own (see
        __init__), just the label it owns.
        """
        if not hasattr(self, '_label'):
            return

        offset = self._alignment_offset()
        x0, x1 = offset.x, offset.x + self._label.width
        z0, z1 = offset.z, offset.z + self._label.height

        local = np.array([
            [x0, 0.0, z0], [x0, 0.0, z1],
            [x1, 0.0, z0], [x1, 0.0, z1],
        ], dtype=np.float32)

        local @= self._angle
        self._obb = local + self._position

    @_check_types.do
    def _compute_aabb(self):
        """Same shape as :meth:`_compute_obb` -- see its docstring."""
        if not hasattr(self, '_label'):
            return

        offset = self._alignment_offset()
        x0, x1 = offset.x, offset.x + self._label.width
        z0, z1 = offset.z, offset.z + self._label.height

        corners = np.array([
            [x0, 0.0, z0], [x0, 0.0, z1],
            [x1, 0.0, z0], [x1, 0.0, z1],
        ], dtype=np.float32)

        corners @= self._angle
        corners += self._position.as_numpy

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    @_check_types.do
    def render(self, faces_program, edges_program, vertices_program):
        """Render this note's own text label -- this object has no VBO
        of its own (see __init__), just the label it owns. Matches
        Base3D.render()'s own uniform-resolution pattern (this class
        overrides it entirely rather than relying on the inherited
        VBO-draw path, which would no-op with vbo=None anyway).
        """
        if not self.is_visible:
            return

        GL.glUseProgram(faces_program)
        self.material.set(faces_program)

        pos_loc = GL.glGetUniformLocation(faces_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(faces_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(faces_program, "objectScale")
        normal_loc = GL.glGetUniformLocation(faces_program, "normalMode")

        offset = self._alignment_offset() @ self._angle
        self._label.set_transform(self._position + offset, self._angle)
        self._label.render(faces_program, pos_loc, rot_loc, scale_loc, normal_loc)

    @_check_types.do
    def _rebuild(self):
        """Rebuild this note's label from its current db_obj fields and
        re-derive its OBB/AABB -- called by every ``set_*`` method below.
        """
        self._label = self._build_label()
        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def set_size(self, size):
        self.db_obj.size3d = size

        with self.editor3d.context:
            self._rebuild()
        self.editor3d.Refresh()

    @_check_types.do
    def set_style(self, style):
        self.db_obj.style3d = style

        with self.editor3d.context:
            self._rebuild()
        self.editor3d.Refresh()

    @_check_types.do
    def set_alignment(self, alignment):
        self.db_obj.h_align3d = alignment

        with self.editor3d.context:
            self._rebuild()
        self.editor3d.Refresh()

    @_check_types.do
    def set_text(self, text: str):
        """Set the note text and rebuild the 3d geometry."""
        self.db_obj.notes = text

        with self.editor3d.context:
            self._rebuild()
        self.editor3d.Refresh()

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return NoteMenu(self.mainframe.editor3d.editor, self)


class NoteMenu(QMenu):
    """Represent a note menu in :mod:`harness_designer.objects.objects_3d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
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

    @_check_types.do
    def on_set_text(self):
        """Edit the note text."""
        @_check_types.do
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

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this note as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this note from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this note's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
