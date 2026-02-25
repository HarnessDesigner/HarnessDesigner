from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui
    from .objects3d import base3d as _base3d
    from .objects2d import base2d as _base2d


class ObjectBase:
    obj2d: "_base2d.Base2D" = None
    obj3d: "_base3d.Base3D" = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe: "_ui.MainFrame" = mainframe

        self._deleted = False
        self._is_selected = False
        self.mainframe.add_object(self)

    def delete(self):
        if self._deleted:
            return

        self._deleted = True
        if self.obj2d is not None:
            self.obj2d.delete()

        if self.obj3d is not None:
            self.obj3d.delete()

    def close(self):
        raise NotImplementedError

    def set_selected(self, flag):
        if self.obj2d is not None:
            self.obj2d.set_selected(flag)
        if self.obj3d is not None:
            self.obj3d.set_selected(flag)

        self._is_selected = flag

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value

        if self.obj2d.is_selected != value:
            self.obj2d.set_selected(value)

        if self.obj3d.is_selected != value:
            self.obj3d.set_selected(value)
