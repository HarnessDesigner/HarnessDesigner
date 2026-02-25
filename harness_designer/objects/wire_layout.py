from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_layout as _wire3d_layout
from .objects2d import wire_layout as _wire2d_layout

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_layout as _pjt_wire_layout


class WireLayout(_ObjectBase):
    obj2d: _wire2d_layout.WireLayout = None
    obj3d: _wire3d_layout.WireLayout = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _wire2d_layout.WireLayout(self, db_obj)
        self.obj3d = _wire3d_layout.WireLayout(self, db_obj)

