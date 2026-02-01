from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import note as _note_2d
from .objects3d import note as _note_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_note as _pjt_note


class Note(_ObjectBase):

    def __init__(
        self, mainframe: "_ui.MainFrame",
        db_obj: "_pjt_note.PJTNote"
    ):
        super().__init__(mainframe)

        self.db_obj = db_obj

        self.obj2d = _note_2d.Note(self, db_obj)
        self.obj3d = _note_3d.Note(self, db_obj)

