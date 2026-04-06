from typing import TYPE_CHECKING

import wx

from wx import aui

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


class EditorObjPanel(wx.Panel):

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent

'''
import wx
from ..widgets import foldpanelbar
from ...geometry.decimal import Decimal as _decimal
from ...database.project_db import pjt_boot as _pjt_boot
from ...database.project_db import pjt_bundle as _pjt_bundle


class ObjectSelectedPanel(wx.Panel):

    def __init__(self, mainframe):
        self.mainframe = mainframe
        wx.Panel.__init__(self, mainframe, wx.ID_ANY, style=wx.BORDER_NONE)
        self.fpb = foldpanelbar.FoldPanelBar(self, wx.ID_ANY, agwStyle=foldpanelbar.FPB_SINGLE_FOLD | foldpanelbar.FPB_VERTICAL)

        cbs = foldpanelbar.CaptionBarStyle()
        cbs.SetCaptionStyle(foldpanelbar.CAPTIONBAR_GRADIENT_H)
        cbs.SetFirstColour(wx.Colour(160, 0, 255, 255))
        cbs.SetSecondColour(wx.Colour(0, 0, 0, 255))
        cbs.SetCaptionColour(wx.Colour(200, 200, 200, 255))
        self.fpb.ApplyCaptionStyleAll(cbs)

    def ClearPanels(self):
        for i in range(self.fpb.GetCount() - 1, -1, -1):
            self.fpb.DeleteFoldPanel(self.fpb.GetFoldPanel(i))

'''



