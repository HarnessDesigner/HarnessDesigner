from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui


class ObjectBase:

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe: "_ui.MainFrame" = mainframe
        self.obj_2d = None
        self.obj_3d = None

    def delete(self):
        if self.obj_2d is not None:
            self.obj_2d.delete()

        if self.obj_3d is not None:
            self.obj_3d.delete()


    def close(self):
        raise NotImplementedError
