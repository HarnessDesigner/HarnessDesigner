from typing import TYPE_CHECKING

from .objects3d import wire_marker as _wire_marker_3d
from .objects2d import wire_marker as _wire_marker_2d

if TYPE_CHECKING:
    from ..database.project_db import pjt_wire_marker as _wire_marker
    from ..ui import mainframe as _mainframe


class WireMarker:

    def __init__(self, main_frame: "_mainframe.MainFrame",
                 db_obj: "_wire_marker.PJTWireMarker"):

        self.main_frame = main_frame

        self.obj_2d = _wire_marker_2d.WireMarker(main_frame.editor2d, db_obj)
        self.obj_3d = _wire_marker_3d.WireMarker(main_frame.editor3d, db_obj)

    def select_2d(self, evt):
        pass

    def select_3d(self, evt):
        pass
