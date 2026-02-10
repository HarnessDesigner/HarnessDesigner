from typing import TYPE_CHECKING

from ...objects import wire as _wire
from ...objects import housing as _housing
from ...objects import cpa_lock as _cpa_lock
from ...objects import tpa_lock as _tpa_lock
from ...objects import bundle_layout as _bundle_layout
from ...objects import bundle as _bundle
from ...objects import wire_marker as _wire_marker
from ...objects import wire_service_loop as _wire_service_loop
from ...objects import wire3d_layout as _wire3d_layout
from ...objects import boot as _boot
from ...objects import cover as _cover
from ...objects import seal as _seal
from ...objects import splice as _splice
from ...objects import terminal as _terminal
from ...objects import transition as _transition

if TYPE_CHECKING:
    from . import canvas as _canvas


class SnapHandler:

    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas
        self.mainframe = canvas.mainframe

    def highlight_snap_points(self, obj):
        if isinstance(obj, _wire):
            pass

        elif isinstance(obj, _wire3d_layout):
            pass

        elif isinstance(obj, _cpa_lock):
            pass

        elif isinstance(obj, _housing):
            pass

        elif isinstance(obj, _tpa_lock):
            pass

        elif isinstance(obj, _bundle_layout):
            pass

        elif isinstance(obj, _bundle):
            pass

        elif isinstance(obj, _wire_marker):
            pass

        elif isinstance(obj, _wire_service_loop):
            pass

        elif isinstance(obj, _boot):
            pass

        elif isinstance(obj, _cover):
            pass

        elif isinstance(obj, _seal):
            pass

        elif isinstance(obj, _splice):
            pass

        elif isinstance(obj, _terminal):
            pass

        elif isinstance(obj, _transition):
            pass



