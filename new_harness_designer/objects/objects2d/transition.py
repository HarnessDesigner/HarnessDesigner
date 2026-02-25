from typing import TYPE_CHECKING

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition


class Transition(_base2d.Base2D):
    _parent: "_transition.Transition" = None
    db_obj: "_pjt_transition.PJTTransition"

    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):

        _base2d.Base2D.__init__(self, parent, db_obj)
