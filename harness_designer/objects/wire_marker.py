from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_marker as _wire_marker_3d
from .objects2d import wire_marker as _wire_marker_2d

if TYPE_CHECKING:
    from ..database.project_db import pjt_wire_marker as _wire_marker
    from ..ui import mainframe as _mainframe


class WireMarker(_ObjectBase):

    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_wire_marker.PJTWireMarker"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _wire_marker_2d.WireMarker(self, db_obj)
        self.obj3d = _wire_marker_3d.WireMarker(self, db_obj)

    def select2d(self, evt):
        pass

    def select3d(self, evt):
        pass

