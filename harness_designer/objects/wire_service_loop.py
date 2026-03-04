from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_service_loop as _wire_service_loop_3d
from .objects2d import wire_service_loop as _wire_service_loop_2d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop


class WireServiceLoop(_ObjectBase):
    obj2d: _wire_service_loop_2d.WireServiceLoop = None
    obj3d: _wire_service_loop_3d.WireServiceLoop = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        db_obj.set_object(self)

        self.obj2d = _wire_service_loop_2d.WireServiceLoop(self, db_obj)
        self.obj3d = _wire_service_loop_3d.WireServiceLoop(self, db_obj)

