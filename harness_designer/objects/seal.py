from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import seal as _seal_2d
from .objects3d import seal as _seal_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_seal as _pjt_seal


class Seal(_ObjectBase):
    obj2d: _seal_2d.Seal = None
    obj3d: _seal_3d.Seal = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_seal.PJTSeal"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _seal_2d.Seal(self, db_obj)
        self.obj3d = _seal_3d.Seal(self, db_obj)

