from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cover as _cover_2d
from .objects3d import cover as _cover_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cover as _pjt_cover


class Cover(_ObjectBase):
    obj2d: _cover_2d.Cover = None
    obj3d: _cover_3d.Cover = None
    db_obj: "_pjt_cover.PJTCover" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cover.PJTCover"):

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _cover_2d.Cover(self, db_obj)
        self.obj3d = _cover_3d.Cover(self, db_obj)
