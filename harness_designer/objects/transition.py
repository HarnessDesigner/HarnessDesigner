from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import transition as _transition_2d
from .objects3d import transition as _transition_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_transition as _pjt_transition


class Transition(_ObjectBase):
    obj2d: _transition_2d.Transition = None
    obj3d: _transition_3d.Transition = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_transition.PJTTransition"):

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _transition_2d.Transition(self, db_obj)
        self.obj3d = _transition_3d.Transition(self, db_obj)
