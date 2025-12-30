from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui


class ObjectBase:

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe: "_ui.MainFrame" = mainframe

    def close(self):
        raise NotImplementedError
