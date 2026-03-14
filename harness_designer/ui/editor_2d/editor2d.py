from typing import TYPE_CHECKING

import wx

from wx import aui
from ...gl.canvas2d import Canvas2D


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class Editor2D(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = Editor2DPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('editor_2d')
        self.CaptionVisible()
        self.Floatable()
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CloseButton(False)
        self.PaneBorder()
        self.Caption('Schematic Editor')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        self.Show()
        self.manager.Update()

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


class Editor2DPanel(wx.Panel):
    """
    2D Schematic Editor Panel
    
    Contains the OpenGL canvas for rendering the schematic view.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent

        # Create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create OpenGL canvas for 2D rendering
        self.canvas = Canvas2D(self, parent.config.editor3d)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        
        self.SetSizer(sizer)
        
        self._objects = []
        self._selected = None

    def set_selected(self, obj):
        self._selected = obj
        if self.canvas:
            self.canvas.set_selected(obj)

    def add_object(self, obj):
        self._objects.append(obj)
        if self.canvas:
            self.canvas.add_object(obj)

    def remove_object(self, obj):
        try:
            self._objects.remove(obj)
            if self.canvas:
                self.canvas.remove_object(obj)
        except ValueError:
            pass
    
    def Refresh(self, *args, **kwargs):
        if self.canvas:
            self.canvas.Refresh(*args, **kwargs)
        wx.Panel.Refresh(self, *args, **kwargs)


