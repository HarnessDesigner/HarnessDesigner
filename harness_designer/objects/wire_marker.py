from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase

from .objects3d import wire_marker as _wire_marker3d
from .objects2d import wire_marker as _wire_marker2d

if TYPE_CHECKING:
    from ..database.project_db import pjt_wire_marker as _wire_marker
    from ..ui import mainframe as _mainframe


class WireMarker(_ObjectBase):

    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_wire_marker.PJTWireMarker"):

        super().__init__(mainframe)

        self.obj2d = _wire_marker2d.WireMarker(mainframe.editor2d, db_obj)
        self.obj3d = _wire_marker3d.WireMarker(mainframe.editor3d, db_obj)

    def select2d(self, evt):
        pass

    def select3d(self, evt):
        pass
