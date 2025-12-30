from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import cover as _cover


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cover as _pjt_cover


class Cover(_ObjectBase):
    obj_3d: _cover.Cover = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cover.PJTCover"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _cover.Cover(mainframe.editor3d, db_obj)
