from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


class Bundle(_base2d.Base2D):
    _parent: "_bundle.Bundle" = None

    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_bundle.PJTBundle" = db_obj
