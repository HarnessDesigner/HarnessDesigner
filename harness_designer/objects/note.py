# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import note as _note_2d
from .objects3d import note as _note_3d
from .objectspeg import note as _note_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_note as _pjt_note


class Note(_ObjectBase):
    """Represent a note in :mod:`harness_designer.objects.note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _note_2d.Note = None
    obj3d: _note_3d.Note = None
    objpeg: _note_peg.Note = None
    db_obj: "_pjt_note.PJTNote" = None

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

        self.obj2d = _note_2d.Note(self, db_obj)
        self.obj3d = _note_3d.Note(self, db_obj)
        self.objpeg = _note_peg.Note(self, db_obj)
        self.mainframe.add_object(self)
