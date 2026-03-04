from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import tpa_lock as _tpa_lock_2d
from .objects3d import tpa_lock as _tpa_lock_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_tpa_lock as _pjt_tpa_lock


class TPALock(_ObjectBase):
    obj2d: _tpa_lock_2d.TPALock = None
    obj3d: _tpa_lock_3d.TPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        db_obj.set_object(self)

        self.obj2d = _tpa_lock_2d.TPALock(self, db_obj)
        self.obj3d = _tpa_lock_3d.TPALock(self, db_obj)
