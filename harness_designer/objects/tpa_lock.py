from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import tpa_lock as _tpa_lock


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_tpa_lock as _pjt_tpa_lock


class TPALock(_ObjectBase):
    obj_3d: _tpa_lock.TPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _tpa_lock.TPALock(mainframe.editor3d, db_obj)