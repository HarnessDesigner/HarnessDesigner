
from typing import TYPE_CHECKING

from ..geometry import point as _point

if TYPE_CHECKING:
    from .. import ui as _ui


class HandlerBase:
    """
    Base class for the 3d handlers
    """

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        self.mainframe = mainframe
        self.part_id = part_id
        self.obj = None
        self.is_active = False
        self.camera = self.mainframe.editor3d
        self.ptables = mainframe.project.ptables

    def finalize(self, mouse_pos: _point.Point):
        raise NotImplementedError

    def start(self, mouse_pos: _point.Point):
        raise NotImplementedError

    def hover(self, mouse_pos: _point.Point):
        pass
