# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import build123d

from ...geometry import point as _point
from . import base_schematic as _base_schematic
from ...ui.widgets import context_menus as _context_menus
from ...gl import materials as _materials
from ...shapes import text as _text
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


Config = _config.Config.editor_schematic


class Note(_base_schematic.BaseSchematic):
    """Represent a note in the 2D schematic editor -- mirrors
    ``objects.objects_3d.note.Note``/``objects.objects_pegboard.note.Note``
    exactly (same ``Text``-as-``_vbo`` approach -- see shapes/text.py's
    own "VBOHandlerBase-compatible interface" docstring -- so this
    class needs no ``render()``/``_compute_obb``/``_compute_aabb``
    override of its own, the generic ``BaseVar`` pipeline handles all
    of it), adapted for the schematic's own ``position2d``/``angle2d``
    columns (and this view's own fixed ``shapes.text.TOP_DOWN_TILT``).
    ``size``/``h_align``/``style`` are shared by every view (see
    ``pjt_note.PJTNotesTable.insert()``'s own docstring) -- this Note
    stays in sync with changes made from any other view via the
    ``bind()`` calls at the end of __init__.
    """
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    # Narrower than BaseVar's own generic `_vbo.VBOHandlerBase | None`
    # -- this object's only visible content is the Text label it owns
    # (see __init__), never a real mesh VBO.
    _vbo: "_text.Text | None" = None

    @_check_types.do
    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        """Initialise the :class:`Note` instance.

        :param parent: Parent object.
        :type parent: :class:`_note.Note`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """
        self.db_obj = db_obj

        with parent.mainframe.editor2d.context:
            # A note belongs to exactly one view -- point2d_id is only
            # ever set if this note was actually placed/configured for
            # the 2D view (see PJTNotesTable.insert()'s own docstring;
            # PJTNote.position2d_id never lazily creates one just
            # because it's read). Nothing real to build otherwise --
            # construct as a fully inert placeholder (None straight
            # through, matching a vbo-less object with no position/
            # angle/scale/material at all) and mark it not-visible so
            # render() skips it. Sets the in-memory flag directly (NOT
            # the ``is_visible`` property) purely to avoid a pointless
            # DB write for a placeholder that's never read again --
            # is_visible2d is this view's own real, independent column
            # (see PJTNote's own class docstring).
            if db_obj.position2d_id is None:
                super().__init__(parent, db_obj, None, None, None, None, None)
                self._is_visible = False
                return

            angle = db_obj.angle2d
            position = db_obj.position2d
            color = db_obj.color.ui
            scale = _point.Point(1.0, 1.0, 1.0)
            material = _materials.Plastic(color)

            # No vbo of its own (None) -- this object's only visible
            # content is the Text label it owns, built/positioned below.
            vbo = self._build_label()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        # notes/size/h_align/style are shared by every view -- rebuild
        # this label whenever any of them changes, regardless of which
        # view's own set_text/set_size/set_style/set_alignment actually
        # wrote it.
        for tag in ('notes', 'size', 'h_align', 'style'):
            db_obj.bind(self._on_label_changed, tag)

    @_check_types.do
    def _on_label_changed(self, *_, **__):
        with self.editor2d.context:
            self._rebuild()
        self.editor2d.Refresh()

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
        docstring for the one real behavior change from the old
        create()/create_vbo() API (fixed 1.0-unit depth) that applies
        here identically. h_align is passed straight through to
        ``Text`` itself -- it handles per-line LEFT/CENTER/RIGHT
        alignment natively (relevant only once ``notes`` has more than
        one line; a single line always renders the same regardless).
        ``local_tilt=_text.TOP_DOWN_TILT`` -- see that constant's own
        docstring for why the schematic view specifically needs it.
        ``center_anchor=True`` so this note's own stored position (what
        a drag actually moves) is the label's own center, not its
        bottom-left corner -- the anchor a mouse dragging it around
        actually expects to be holding, regardless of how many lines/
        how long the text is.
        """
        return _text.Text(
            self.db_obj.notes, self.db_obj.size,
            build123d.FontStyle(self.db_obj.style),
            build123d.TextAlign(self.db_obj.h_align),
            local_tilt=_text.TOP_DOWN_TILT, center_anchor=True)

    @_check_types.do
    def _rebuild(self):
        """Rebuild this note's label from its current db_obj fields and
        re-derive its OBB/AABB -- called by every ``set_*`` method below.
        """
        self._vbo = self._build_label()
        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def set_size(self, size):
        """Set this note's (shared) font size -- rebuild/refresh happens
        via the bound callback from __init__, for every view, not just
        this one.
        """
        self.db_obj.size = size

    @_check_types.do
    def set_style(self, style):
        """Set this note's (shared) font style -- see :meth:`set_size`."""
        self.db_obj.style = style

    @_check_types.do
    def set_alignment(self, alignment):
        """Set this note's (shared) horizontal alignment -- see
        :meth:`set_size`."""
        self.db_obj.h_align = alignment

    @_check_types.do
    def set_text(self, text: str):
        """Set this note's (shared) text -- see :meth:`set_size`."""
        self.db_obj.notes = text


class NoteMenu(QMenu):
    """Represent a note menu in :mod:`harness_designer.objects.objects_schematic.note`.

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
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
