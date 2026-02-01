from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import housing as _housing_2d
from .objects3d import housing as _housing_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing


class Housing(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_housing.PJTHousing"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _housing_2d.Housing(self, db_obj)
        self.obj3d = _housing_3d.Housing(self, db_obj)

