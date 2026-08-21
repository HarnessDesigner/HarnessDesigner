# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import build123d
import numpy as np

from . import base_pegboard as _base_pegboard
from ...geometry import point as _point
from ...gl import materials as _materials
from ... import utils as _utils
from ...shapes import text as _text
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


Config = _config.Config.editor_pegboard


class Note(_base_pegboard.BasePegboard):
    """Peg-board representation of a note -- mirrors
    ``objects.objects_3d.note.Note`` exactly (same ``Text``-label-only
    approach, same alignment-offset trick, same OBB/AABB derivation),
    adapted for the peg-board's own DB columns
    (``position_pegboard``/``angle_pegboard``/``size_pegboard``/
    ``h_align_pegboard``/``style_pegboard``) and built with its own
    independent material (never borrowed from ``obj3d`` -- see
    ``base_pegboard.BasePegboard.__init__``'s own docstring on why).
    """
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    @_check_types.do
    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        """Initialise the :class:`Note` instance.

        :param parent: Parent object.
        :type parent: :class:`_note.Note`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """
        self.db_obj = db_obj
        angle = db_obj.angle_pegboard
        position = db_obj.position_pegboard
        color = db_obj.color.ui
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Plastic(color)

        with parent.mainframe.editor_pegboard.context:
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
        db_obj fields -- see objects_3d.note.Note._build_label's own
        docstring for the two real behavior changes from the old
        create()/create_vbo() API (fixed 1.0-unit depth, no built-in
        alignment) that apply here identically.
        """
        return _text.Text(
            self.db_obj.notes, self.db_obj.size_pegboard,
            build123d.FontStyle(self.db_obj.style_pegboard))

    @_check_types.do
    def _alignment_offset(self) -> _point.Point:
        """Local-space anchor offset for this note's current alignment.

        Horizontal follows ``h_align_pegboard`` (LEFT/CENTER/RIGHT);
        vertical is unconditionally CENTER -- mirrors
        objects_3d.note.Note._alignment_offset exactly.
        """
        h_align = build123d.TextAlign(self.db_obj.h_align_pegboard)

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
        BaseVar.render()'s own uniform-resolution pattern (this class
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
        self.db_obj.size_pegboard = size

        with self.pegboard.context:
            self._rebuild()
        self.pegboard.Refresh()

    @_check_types.do
    def set_style(self, style):
        self.db_obj.style_pegboard = style

        with self.pegboard.context:
            self._rebuild()
        self.pegboard.Refresh()

    @_check_types.do
    def set_alignment(self, alignment):
        self.db_obj.h_align_pegboard = alignment

        with self.pegboard.context:
            self._rebuild()
        self.pegboard.Refresh()

    @_check_types.do
    def set_text(self, text: str):
        """Set the note text and rebuild the peg-board geometry."""
        self.db_obj.notes = text

        with self.pegboard.context:
            self._rebuild()
        self.pegboard.Refresh()
