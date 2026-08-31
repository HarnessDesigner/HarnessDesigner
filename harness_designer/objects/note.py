# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_schematic import note as _note_schematic
from .objects_3d import note as _note_3d
from .objects_pegboard import note as _note_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_note as _pjt_note


class Note(_ObjectBase):
    """Represent a note in :mod:`harness_designer.objects.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _note_schematic.Note = None
    obj3d: _note_3d.Note = None
    objpegboard: _note_pegboard.Note = None
    db_obj: "_pjt_note.PJTNote" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_note.PJTNote", project_load=False):
        """Initialise the :class:`Note` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_note.PJTNote`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _note_schematic.Note(self, db_obj)
        self.obj3d = _note_3d.Note(self, db_obj)
        self.objpegboard = _note_pegboard.Note(self, db_obj)
        self.mainframe.add_object(self)

        # Deferred until this facade is fully wired up (obj3d assigned,
        # registered on every canvas above) -- see objects_3d.note.
        # Note.__init__'s own comment for why starting this any earlier
        # (from inside that constructor call) crashes: enable_camera_
        # tracking's own refresh_canvas_registration() needs self.obj3d
        # to already be this exact, real instance, not the class-level
        # None default a not-yet-returned constructor call still leaves
        # it at.
        if not db_obj.angle3d_lock:
            self.obj3d._start_camera_tracking()  # NOQA

    @_check_types.do
    def delete(self):
        super().delete()
        self.mainframe.project.delete_note(self.db_obj.db_id)
        self.db_obj.delete()

    @property
    @_check_types.do
    def is_angle_locked(self) -> bool:
        """Whether this note's angle3d is user-locked rather than
        continuously re-facing the 3D camera -- see :meth:`lock_angle`/
        :meth:`unlock_angle`. Delegates to :attr:`obj3d` -- the 3D view
        is the only one with a camera to face at all (2D/pegboard are
        both a locked top-down projection).
        """
        return self.obj3d.is_angle_locked

    @_check_types.do
    def lock_angle(self) -> None:
        """Freeze this note's current camera-facing angle as its new
        real, persisted one, and stop tracking the camera -- see
        ``objects_3d.note.Note.lock_angle``'s own docstring.
        """
        self.obj3d.lock_angle()

    @_check_types.do
    def unlock_angle(self) -> None:
        """Clear the lock and resume tracking the camera -- see
        ``objects_3d.note.Note.unlock_angle``.
        """
        self.obj3d.unlock_angle()
