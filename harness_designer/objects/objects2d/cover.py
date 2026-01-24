from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_cover as _pjt_cover
    from .. import cover as _cover


class Cover(_base2d.Base2D):
    _parent: "_cover.Cover" = None

    def __init__(self, parent: "_cover.Cover", db_obj: "_pjt_cover.PJTCover"):
        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_cover.PJTCover" = db_obj
