import wx
from ... import utils


class GenericIntCtrl(wx.Panel):

    def __init__(self, parent, label, suffix=None):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.ctrl = wx.SpinCtrl(self, wx.ID_ANY, value='0', initial=0, min=0, max=999, size=(100, -1))

        if suffix is None:
            sizer = utils.HSizer(self, label, self.ctrl)
        else:
            sizer = utils.HSizer(self, label, self.ctrl, suffix)

        self.SetSizer(sizer)

    def SetValue(self, value: int) -> None:
        self.ctrl.SetValue(value)

    def GetValue(self) -> int:
        return self.ctrl.GetValue()
