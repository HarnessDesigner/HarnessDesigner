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
        self.CloseButton(True)
        self.PaneBorder()
        self.Caption('Object Editor')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        aui.AuiPaneInfo.Show(self)
        self.manager.Update()

        self.manager.Bind(aui.EVT_AUI_PANE_CLOSE, self._on_pane_close)

    def _on_pane_close(self, evt: aui.AuiManagerEvent):
        pane = evt.GetPane()

        print(pane)

        if pane == self:
            self.Show(False)
        else:
            evt.Skip()

    def Show(self, show=True):
        if show:
            self.set_selected(self.mainframe.get_selected())
        else:
            self.set_selected(None)

        aui.AuiPaneInfo.Show(self, show)
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()

    def set_selected(self, obj):
        if self.IsShown():
            self.editor.set_selected(obj)


class EditorObjPanel(wx.Panel):

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent
        self.control = None

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.sizer = hsizer
        self.SetSizer(vsizer)
        self._selected = None

    def set_selected(self, obj):
        if obj is None:
            if self.control is not None:
                self.control.Show(False)
                self.sizer.Detach(self.control)
                self.control.Reparent(self.mainframe)
                self.control = None
        else:
            control = obj.db_obj.table.control
            control.set_obj(obj.db_obj)
            control.Reparent(self)

            if self.control is not None:
                self.control.Show(False)
                self.sizer.Detach(self.control)
                self.control.Reparent(self.mainframe)

            self.sizer.Add(control, 1, wx.EXPAND | wx.ALL, 10)
            self.control = control
            control.Show()

        self.Layout()
        self.Refresh(False)

        self._selected = obj
