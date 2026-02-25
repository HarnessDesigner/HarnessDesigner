from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase

from .objects3d import generic as _generic3d
from .objects2d import generic as _generic2d

if TYPE_CHECKING:
    from .. import ui as _ui


Generic2D = _generic2d.Generic
Generic3D = _generic3d.Generic


class Generic(_ObjectBase):
    obj2d: Generic2D
    obj3d: Generic3D

    def __init__(self, mainframe: "_ui.MainFrame"):

        super().__init__(mainframe)

        self.db_obj = None

        self.obj2d = None
        self.obj3d = None
