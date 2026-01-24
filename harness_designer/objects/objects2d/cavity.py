from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base2d.Base2D):
    _parent: "_cavity.Cavity" = None

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):

        _base2d.Base2D.__init__(self, parent)
        self._db_obj: "_pjt_cavity.PJTCavity" = db_obj
