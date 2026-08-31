# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import build123d

from ...geometry import point as _point
from ...ui.widgets import context_menus as _context_menus
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ...gl import materials as _materials
from ...shapes import text as _text
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note
    from ... import ui as _ui


Config = _config.Config.editor_3d


class Note(_base_3d.Base3D):
    """Represent a note in :mod:`harness_designer.objects.objects_3d.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote" = None

    # Narrower than BaseVar's own generic `_vbo.VBOHandlerBase | None`
    # -- this object's only visible content is the Text label it owns
    # (see __init__), never a real mesh VBO.
    _vbo: "_text.Text | None" = None

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

        with parent.mainframe.editor3d.context:
            # A note belongs to exactly one view -- point3d_id is only
            # ever set if this note was actually placed/configured for
            # the 3D view (see PJTNotesTable.insert()'s own docstring;
            # PJTNote.position3d_id never lazily creates one just
            # because it's read). Nothing real to build otherwise --
            # construct as a fully inert placeholder (None straight
            # through, matching a vbo-less object with no position/
            # angle/scale/material at all) and mark it not-visible so
            # render() skips it. Sets the in-memory flag directly (NOT
            # the ``is_visible`` property) purely to avoid a pointless
            # DB write for a placeholder that's never read again --
            # is_visible3d is this view's own real, independent column
            # (see PJTNote's own class docstring).
            if db_obj.position3d_id is None:
                super().__init__(parent, db_obj, None, None, None, None, None)
                self._is_visible = False
                return

            angle = db_obj.angle3d
            position = db_obj.position3d
            color = db_obj.color.ui
            scale = _point.Point(1.0, 1.0, 1.0)
            material = _materials.Plastic(color)

            # No vbo of its own (None) -- this object's only visible
            # content is the Text label it owns, built/positioned below.

            vbo = self._build_label()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        # notes/size/h_align/style are shared by every view (see
        # pjt_note.PJTNotesTable.insert()'s own docstring) -- rebuild
        # this label whenever any of them changes, regardless of which
        # view's own set_text/set_size/set_style/set_alignment actually
        # wrote it.
        db_obj.bind(self._on_label_changed, 'notes')
        db_obj.bind(self._on_label_changed, 'size')
        db_obj.bind(self._on_label_changed, 'h_align')
        db_obj.bind(self._on_label_changed, 'style')

        # Camera tracking is NOT started here, even for an unlocked note
        # -- see objects.note.Note.__init__, which starts it right after
        # this constructor returns instead. enable_camera_tracking's own
        # refresh_canvas_registration() reads self.parent.obj3d.aabb
        # (via CanvasBase.add_object), but self.parent.obj3d is only
        # ever assigned once THIS __init__ call returns -- starting
        # tracking from in here would read that attribute while it's
        # still None, straight from the object's own constructor.

    @_check_types.do
    def _delete(self):
        """Release this note's own arena row, if it's still holding one,
        before the base teardown runs -- ``_CameraTrackingArena.update``
        would otherwise only notice this note is gone the next time the
        camera moves (it prunes dead owners lazily -- see its own
        docstring), which is harmless but leaves the row held longer
        than it needs to be.
        """
        if self._vbo is not None and self._vbo._tracking_angle is not None:  # NOQA
            self._vbo.disable_camera_tracking(self)

        super()._delete()

    @_check_types.do
    def _on_label_changed(self, *_, **__):
        with self.editor3d.context:
            self._rebuild()

        self.editor3d.Refresh()

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

        One real behavior change from the old ``create()``/
        ``create_vbo()`` API: every glyph is pre-extruded at a fixed
        1.0 world unit (see ``shapes/text.py``'s ``build_chars()``),
        not the old ``depth=0.25`` -- notes now render thicker than
        they used to. A real per-instance depth knob would need a
        change to ``shapes/text.py`` itself, out of scope here.

        ``h_align`` is passed straight through to ``Text`` itself --
        it handles per-line LEFT/CENTER/RIGHT alignment natively
        (relevant only once ``notes`` has more than one line; a single
        line always renders the same regardless). ``center_anchor=True``
        so this note's own stored position (what a drag actually moves)
        is the label's own center, not its bottom-left corner -- the
        anchor a mouse dragging it around actually expects to be
        holding, regardless of how many lines/how long the text is.
        """
        return _text.Text(
            self.db_obj.notes, self.db_obj.size,
            build123d.FontStyle(self.db_obj.style),
            build123d.TextAlign(self.db_obj.h_align),
            center_anchor=True)

    @property
    @_check_types.do
    def is_angle_locked(self) -> bool:
        """Whether this note's ``angle3d`` is user-locked rather than
        continuously re-facing the camera -- see :meth:`lock_angle`/
        :meth:`unlock_angle`.
        """
        return self.db_obj.angle3d_lock

    @_check_types.do
    def refresh_canvas_registration(self) -> None:
        """Re-capture this note's own (just-changed-identity)
        ``_obb``/``_aabb`` into the 3D canvas's own culling data.

        Duck-typed hook called by ``shapes.text.Text.
        enable_camera_tracking``/``disable_camera_tracking`` (and
        ``_CameraTrackingArena``'s own growth fixup) right after either
        reassigns this note's ``_obb``/``_aabb`` to a new array --
        ``gl.canvas_base.canvas_base.CanvasBase.add_object`` captures a
        live reference to whichever array those attributes point to
        exactly once, when the note is first added to the scene, and
        never re-reads them again, so any later identity change needs
        this to keep the canvas's own culling data from silently going
        stale. ``remove_object``/``add_object`` are each an O(N) linear
        scan over the canvas's full object list, and neither one
        triggers a repaint of its own -- acceptable cost precisely
        because this only ever runs at the rare, user-triggered lock/
        unlock toggle points (or an occasional arena growth), never on
        the frequent camera-move-driven update.
        """
        self.editor3d.editor.remove_object(self.parent)
        self.editor3d.editor.add_object(self.parent)

    @_check_types.do
    def _start_camera_tracking(self) -> None:
        """Begin (or resume) continuously re-facing the camera -- called
        once from :meth:`__init__` for a note that starts out unlocked,
        again from :meth:`unlock_angle`, and again from :meth:`_rebuild`
        for a note whose label just got rebuilt while already tracking.
        A no-op for a placeholder note (no real ``_vbo``/geometry at
        all -- see :meth:`__init__`'s own early return).
        """
        if self._vbo is None:
            return

        self._vbo.enable_camera_tracking(self)

    @_check_types.do
    def lock_angle(self) -> None:
        """Freeze this note's current camera-facing angle as its new
        real, persisted ``angle3d``, and stop tracking the camera.

        Called both from the Angle-lock property-panel checkbox (via
        the facade's own :meth:`~objects.note.Note.lock_angle`) and from
        this note's own rotation-rings session coming up (see
        ``rotation_handlers.rotation_rings.RotationRings.__init__``,
        duck-typed off exactly this method plus :attr:`is_angle_locked`/
        :meth:`unlock_angle` -- that class has no business knowing Note
        exists).
        """
        if self._vbo is not None and self._vbo._tracking_angle is not None:  # NOQA
            tracked = self._vbo._tracking_angle  # NOQA
            angle = self.db_obj.angle3d
            angle.x = tracked.x
            angle.y = tracked.y
            angle.z = tracked.z

            self._vbo.disable_camera_tracking(self)

        self.db_obj.angle3d_lock = True

    @_check_types.do
    def unlock_angle(self) -> None:
        """Clear the lock and resume tracking the camera -- see
        :meth:`lock_angle`'s own docstring for who calls this.
        """
        self.db_obj.angle3d_lock = False
        self._start_camera_tracking()

    @_check_types.do
    def _rebuild(self):
        """Rebuild this note's label from its current db_obj fields and
        re-derive its OBB/AABB -- called by every ``set_*`` method below.

        A camera-tracking note's old ``_vbo`` is releasing its own arena
        row here (see ``shapes.text.Text.disable_camera_tracking``) and
        the freshly built one is claiming a new one (immediately reused
        -- the free-list hands back exactly the row just released, since
        nothing else runs in between) rather than trying to carry the
        old row's registration over: its own local OBB/AABB are keyed to
        the old label's glyph layout, which is exactly what's changing.
        """
        was_tracking = self._vbo is not None and self._vbo._tracking_angle is not None  # NOQA
        if was_tracking:
            self._vbo.disable_camera_tracking(self)

        self._vbo = self._build_label()
        self._compute_obb()
        self._compute_aabb()

        if was_tracking:
            self._start_camera_tracking()

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

    @classmethod
    @_check_types.do
    def start_add(cls, mainframe: "_ui.MainFrame") -> "_note.Note | None":
        """Gather the note's text/formatting via the modal dialog (always
        shown -- unlike a part-search pick, there's no preselected-value
        shortcut), build the real facade at a placeholder position, and
        arm its single-click placement session -- see
        add_handlers.editor_3d.note.Note.
        """
        from ...ui.dialogs import add_note as _add_note
        from ...gl import materials as _materials_local
        from ... import color as _color
        from ... import config as _config

        dlg = _add_note.AddNoteDialog(mainframe)
        dlg.exec()
        note, align, style, color_id, size = dlg.GetValue()
        dlg.deleteLater()

        ptables = mainframe.project.ptables
        position = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        # Placed via the 3D editor -- this note belongs to the 3D view
        # only (point2d_id/point_pegboard_id both left None; see
        # PJTNotesTable.insert()'s own docstring).
        db_obj = ptables.pjt_notes_table.insert(
            position.db_id, None, None, note, size, align, style,
            color_id=color_id)

        from .. import note as _note_facade

        facade = _note_facade.Note(mainframe, db_obj)

        preview_material = _materials_local.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        facade.identify(preview_material)

        canvas = mainframe.editor3d.editor

        from ...add_handlers.editor_3d import note as _add_note_handler

        handler = _add_note_handler.Note(canvas, facade)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.

        Locking this note when its rotation rings come up (so it isn't
        dragged from a stale/still-camera-following angle) and undoing
        that lock again if the session closes without the angle ever
        actually changing both happen generically, in
        ``RotationRings.__init__``/``delete`` -- duck-typed off the
        facade's own ``is_angle_locked``/``lock_angle``/``unlock_angle``
        (see ``objects.note.Note``), not anything specific to this
        class. Nothing extra needed here.
        """
        from ...add_handlers.editor_3d import note as _add_note_handler  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_note_handler.Note):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

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
