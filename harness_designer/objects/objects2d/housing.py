from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base2d.Base2D):
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):

        _base2d.Base2D.__init__(self, parent, db_obj)
