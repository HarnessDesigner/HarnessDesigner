from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ... import editor_2d as _editor_2d
    from ...editor_2d import canvas as _canvas


class Base2D:

    def __init__(self, parent: "_ObjectBase"):
        self._parent: "_ObjectBase" = parent

        try:
            self.editor2d: "_editor_2d.Editor2D" = parent.mainframe.editor2d
        except AttributeError:
            self.editor2d: "_editor_2d.Editor2D" = parent.editor2d

        self.canvas: "_canvas.Canvas" = self.editor2d.canvas
        self.mainframe: "_ui.MainFrame" = self.canvas.mainframe

        self._is_selected = False

    def set_selected(self, flag: bool):
        self._is_selected = flag

    @property
    def is_selected(self) -> bool:
        return self._is_selected
