from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import terminal as _terminal_2d
from .objects3d import terminal as _terminal_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_terminal as _pjt_terminal


class Terminal(_ObjectBase):
    obj2d: _terminal_2d.Terminal = None
    obj3d: _terminal_3d.Terminal = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _terminal_2d.Terminal(self, db_obj)
        self.obj3d = _terminal_3d.Terminal(self, db_obj)
