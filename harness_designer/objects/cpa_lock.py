from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import cpa_lock as _cpa_lock


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cpa_lock as _pjt_cpa_lock


class CPALock(_ObjectBase):
    obj_3d: _cpa_lock.CPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cpa_lock.PJTCPALock"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _cpa_lock.CPALock(mainframe.editor3d, db_obj)