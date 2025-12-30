from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import wire2d_layout as _wire2d_layout


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire2d_layout as _pjt_wire2d_layout


class Wire2DLayout(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire2d_layout.PJTWire2DLayout"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_2d = _wire2d_layout.Wire2DLayout(mainframe.editor3d, db_obj)
