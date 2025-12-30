from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_service_loop as _wire_service_loop

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop


class WireServiceLoop(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _wire_service_loop.WireServiceLoop(mainframe.editor3d, db_obj)






