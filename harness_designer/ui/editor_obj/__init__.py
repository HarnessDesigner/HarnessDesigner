
import wx
from ...widgets import foldpanelbar
from ...wrappers.decimal import Decimal as _decimal
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


class FloatCtrl(wx.BoxSizer):

    def __init__(self, parent, label, min_val, max_val):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.SpinCtrlDouble(parent, wx.ID_ANY, value=str(min_val), initial=min_val, min=min_val, max=max_val, inc=0.1)

        self.Add(st, 0, wx.ALL, 5)
        self.Add(self.ctrl, 0, wx.ALL, 5)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: _decimal):
        self.ctrl.SetValue(float(value))

    def GetValue(self) -> _decimal:
        return _decimal(self.ctrl.GetValue())

