from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_cpa_lock as _pjt_cpa_lock
    from .. import cpa_lock as _cpa_lock


class CPALock(_base2d.Base2D):
    _parent: "_cpa_lock.CPALock"
    db_obj: "_pjt_cpa_lock.PJTCPALock"

    def __init__(self, parent: "_cpa_lock.CPALock",
                 db_obj: "_pjt_cpa_lock.PJTCPALock"):

        _base2d.Base2D.__init__(self, parent, db_obj)
