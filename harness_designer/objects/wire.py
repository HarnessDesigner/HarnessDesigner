from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import wire as _wire2d
from .objects3d import wire as _wire3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire


class Wire(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire.PJTWire"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_2d = _wire2d.Wire(mainframe.editor2d, db_obj)
        self.obj_3d = _wire3d.Wire(mainframe.editor3d, db_obj)
