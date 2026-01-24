from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock


class TPALock(_base2d.Base2D):
    _parent: "_tpa_lock.TPALock" = None

    def __init__(self, parent: "_tpa_lock.TPALock",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_tpa_lock.PJTTPALock" = db_obj
