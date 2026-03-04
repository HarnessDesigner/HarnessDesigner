from typing import TYPE_CHECKING

import wx

from wx import aui


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

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent

        self._objects = []
        self._selected = None

    def set_selected(self, obj):
        self._selected = obj

    def add_object(self, obj):
        self._objects.append(obj)

    def remove_object(self, obj):
        try:
            self._objects.remove(obj)
        except ValueError:
            pass

