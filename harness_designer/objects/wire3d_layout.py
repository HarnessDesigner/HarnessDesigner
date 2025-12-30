from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire3d_layout as _wire3d_layout


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


class Wire3DLayout(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire3d_layout.PJTWire3DLayout"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj_3d = _wire3d_layout.Wire3DLayout(mainframe.editor3d, db_obj)
