from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import housing as _housing2d
from .objects3d import housing as _housing3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing


class Housing(_ObjectBase):
    obj_2d: _housing2d.Housing = None
    obj_3d: _housing3d.Housing = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_housing.PJTHousing"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_2d = _housing2d.Housing(mainframe.editor2d, db_obj)
        self.obj_3d = _housing3d.Housing(mainframe.editor3d, db_obj)
