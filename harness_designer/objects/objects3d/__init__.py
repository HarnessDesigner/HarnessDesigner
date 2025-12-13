from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d


class Base3D:

    def __init__(self, editor3d: "_editor_3d.Editor3D"):
        self.editor3d = editor3d

        self._is_selected = False

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value
