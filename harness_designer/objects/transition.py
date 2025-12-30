from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import transition as _transition


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_transition as _pjt_transition


class Transition(_ObjectBase):
    obj_3d: _transition.Transition = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_transition.PJTTransition"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _transition.Transition(mainframe.editor3d, db_obj)
