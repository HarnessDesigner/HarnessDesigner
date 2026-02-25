from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


class Seal(_base2d.Base2D):
    _parent: "_seal.Seal" = None
    db_obj: "_pjt_seal.PJTSeal"

    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        _base2d.Base2D.__init__(self, parent, db_obj)
