from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import seal as _seal


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_seal as _pjt_seal


class Seal(_ObjectBase):
    obj_3d: _seal.Seal = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_seal.PJTSeal"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _seal.Seal(mainframe.editor3d, db_obj)
