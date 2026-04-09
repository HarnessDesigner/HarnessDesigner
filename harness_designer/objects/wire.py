from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import wire as _wire_2d
from .objects3d import wire as _wire_3d

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire


class Wire(_ObjectBase):
    obj2d: _wire_2d.Wire = None
    obj3d: _wire_3d.Wire = None
    db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire.PJTWire"):

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _wire_2d.Wire(self, db_obj)
        self.obj3d = _wire_3d.Wire(self, db_obj)
