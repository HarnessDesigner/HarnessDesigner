from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


class Splice(_base2d.Base2D):
    _parent: "_splice.Splice"

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_splice.PJTSplice" = db_obj
