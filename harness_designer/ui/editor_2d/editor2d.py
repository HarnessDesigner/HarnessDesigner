# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets

from ...gl import canvas2d as _canvas2d
from ... import config as _config


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor2d


class Editor2D:

    def __init__(self, mainframe: "_mainframe.MainFrame"):

        self.editor = Editor2DPanel(mainframe)
        self.mainframe = mainframe

        dock = mainframe._make_dock(
            title='Schematic Editor',
            name='editor_2d',
            widget=self.editor,
            area=None,  # Right area; _make_dock uses Qt.RightDockWidgetArea by default
        )
        self._dock = dock
        dock.show()

    def Show(self, show=True):
        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def set_selected(self, obj):
        self.editor.set_selected(obj)

    def add_object(self, obj):
        self.editor.add_object(obj)

    def remove_object(self, obj):
        self.editor.remove_object(obj)

    def Refresh(self, *args, **kwargs):
        self.editor.update()

    def Destroy(self):
        self.editor.deleteLater()

    def bind(self, signal_name, handler):
        self.editor.bind(signal_name, handler)

    def set_clone_obj(self, obj):
        self.editor.set_clone_obj(obj)


class Editor2DPanel(_canvas2d.Canvas2D):

    def __init__(self, parent):
        if not Config.virtual_canvas.width or not Config.virtual_canvas.height:
            max_x = 0
            max_y = 0
            min_x = 0
            min_y = 0
            for screen in QApplication.screens():
                geo = screen.geometry()
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                max_x = max(x + w, max_x)
                max_y = max(y + h, max_y)
                min_x = min(x, min_x)
                min_y = min(y, min_y)

            width = max_x - min_x
            height = int(width / 1.777777)

            Config.virtual_canvas.width = width
            Config.virtual_canvas.height = height

        size = (Config.virtual_canvas.width,
                Config.virtual_canvas.height)

        super().__init__(parent, Config, size)
