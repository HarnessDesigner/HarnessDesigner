from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


class Boot(_base2d.Base2D):
    _parent: "_boot.Boot" = None

    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_boot.PJTBoot" = db_obj
