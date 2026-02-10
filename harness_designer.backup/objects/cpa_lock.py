from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cpa_lock as _cpa_lock_2d
from .objects3d import cpa_lock as _cpa_lock_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cpa_lock as _pjt_cpa_lock


class CPALock(_ObjectBase):
    obj2d: _cpa_lock_2d.CPALock = None
    obj3d: _cpa_lock_3d.CPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cpa_lock.PJTCPALock"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _cpa_lock_2d.CPALock(self, db_obj)
        self.obj3d = _cpa_lock_3d.CPALock(self, db_obj)

