from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import note as _note2d
from .objects3d import note as _note3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_note as _pjt_note


class Note(_ObjectBase):
    obj_2d: _note2d.Note = None
    obj_3d: _note3d.Note = None

    def __init__(
        self, mainframe: "_ui.MainFrame",
        db_obj: "_pjt_note.PJTNote"
    ):
        super().__init__(mainframe)

        self.db_obj = db_obj

        self.obj_2d = _note2d.Note(mainframe.editor2d, db_obj)
        self.obj_3d = _note3d.Note(mainframe.editor3d, db_obj)
