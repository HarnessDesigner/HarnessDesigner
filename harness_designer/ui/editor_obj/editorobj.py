from typing import TYPE_CHECKING

import wx
from wx import aui

from . import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorObj(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = EditorObjPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('editor_obj')
        self.CaptionVisible()
        self.Floatable()
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CloseButton(False)
        self.PaneBorder()
        self.Caption('Object Editor')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        self.Show()
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()

    def set_selected(self, obj):
        self.editor.set_selected(obj)


class EditorObjPanel(wx.Panel):

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent

        self.prop_grid = _prop_grid.PropertyGrid(self)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.prop_grid, 1, wx.EXPAND | wx.ALL, 10)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)
        self._selected = None

    def set_selected(self, obj):
        self.prop_grid.Clear()

        if obj is not None:
            groups = obj.propgrid

            for group in groups:
                self.prop_grid.Append(group)

        self._selected = obj
