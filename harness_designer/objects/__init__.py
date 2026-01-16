from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui


class ObjectBase:

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe: "_ui.MainFrame" = mainframe
        self.obj2d = None
        self.obj3d = None

    def delete(self):
        if self.obj2d is not None:
            self.obj2d.delete()

        if self.obj3d is not None:
            self.obj3d.delete()

    def close(self):
        raise NotImplementedError
