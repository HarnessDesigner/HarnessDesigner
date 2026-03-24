from typing import TYPE_CHECKING

import wx
from wx import aui

from ... import config as _config
from ...gl import canvas3d as _canvas3d


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor3d


class Editor3D(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = Editor3DPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('editor_3d')
        self.CaptionVisible()
        self.Floatable(False)
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CenterPane()
        self.CloseButton(False)
        self.PaneBorder()
        self.Caption('3D Editor')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        self.Show()
        self.manager.Update()

    @property
    def context(self):
        return self.editor.context

    @property
    def camera(self):
        return self.editor.camera

    def set_selected(self, obj):
        self.editor.set_selected(obj)

    def add_object(self, obj):
        self.editor.add_object(obj)

    def remove_object(self, obj):
        self.editor.remove_object(obj)

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()

    def Bind(self, *args, **kwargs):
        self.editor.Bind(*args, **kwargs)


class Editor3DPanel(_canvas3d.Canvas3D):

    def __init__(self, parent: "_mainframe.MainFrame"):
        if not Config.virtual_canvas.width or not Config.virtual_canvas.height:
            max_x = 0
            max_y = 0
            min_x = 0
            min_y = 0
            displays = (wx.Display(i) for i in range(wx.Display.GetCount()))
            for display in displays:
                geometry = display.GetGeometry()
                x, y = geometry.GetPosition()
                w, h = geometry.GetSize()
                max_x = max(x + w, max_x)
                max_y = max(y + h, max_y)
                min_x = min(x, min_x)
                min_y = min(y, min_y)

            # we want to keep a 16:9 aspect ratio so the rendered
            # canvas doesn't get distorted. This is the reason why we are using
            # a "virtual" size. The canvas in most cases will actually be
            # larger than what is being viewed. The window clips what is being
            # seen. This allows th window size to be changed without causing
            # the contents of the window to change size. It actually expands the
            # field of view instead of altering the size of what is ebing seen.
            # this virtual size is able to be adjusted in the settings.
            width = max_x - min_x
            height = int(width / 1.777777)

            Config.virtual_canvas.width = width
            Config.virtual_canvas.height = height

        size = (Config.virtual_canvas.width,
                Config.virtual_canvas.height)

        super().__init__(parent, Config, size, True)
