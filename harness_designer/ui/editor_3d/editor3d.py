# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ... import config as _config
from ...gl import canvas3d as _canvas3d


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor3d


class Editor3D:

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = Editor3DPanel(mainframe)
        self.mainframe = mainframe

        mainframe._make_dock(
            title='3D Editor',
            name='editor_3d',
            widget=self.editor,
            area=Qt.DockWidgetArea.AllDockWidgetAreas,  # centre pane — set as central widget directly
        )

    @property
    def context(self):
        return self.editor.context

    @property
    def camera(self):
        return self.editor.camera

    @property
    def config(self) -> _config.Config.editor3d:
        return self.editor.config

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

    def connect(self, signal_name, handler):
        getattr(self.editor, signal_name).connect(handler)

    def set_clone_obj(self, obj):
        self.editor.set_clone_obj(obj)


class Editor3DPanel(_canvas3d.Canvas3D):

    def __init__(self, parent: "_mainframe.MainFrame"):
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

        super().__init__(parent, Config, size, True)
