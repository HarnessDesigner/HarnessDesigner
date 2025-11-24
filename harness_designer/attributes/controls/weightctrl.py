import wx
from ... import utils


class WeightCtrl(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, min=0.0, max=999.90, inc=0.1, size=(100, -1))

        sizer = utils.HSizer(self, 'Weight:', self.ctrl, 'g')
        self.SetSizer(sizer)

    def SetValue(self, value: float) -> None:
        self.ctrl.SetValue(value)

    def GetValue(self) -> float:
        return self.ctrl.GetValue()
