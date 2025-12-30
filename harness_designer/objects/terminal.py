from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import terminal as _terminal2d
from .objects3d import terminal as _terminal3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_terminal as _pjt_terminal


class Terminal(_ObjectBase):
    obj_2d: _terminal2d.Terminal = None
    obj_3d: _terminal3d.Terminal = None

    def __init__(
        self, mainframe: "_ui.MainFrame",
        db_obj: "_pjt_terminal.PJTTerminal"
    ):
        super().__init__(mainframe)

        self.db_obj = db_obj

        self.obj_2d = _terminal2d.Terminal(mainframe.editor2d, db_obj)
        self.obj_3d = _terminal3d.Terminal(mainframe.editor3d, db_obj)
