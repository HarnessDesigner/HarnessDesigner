import wx
from ... import utils


class GenericTextCtrl(wx.Panel):

    def __init__(self, parent, label):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(250, -1))
        sizer = utils.HSizer(self, label, self.ctrl)
        self.SetSizer(sizer)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()

    def SetValue(self, value: str):
        self.ctrl.SetValue(value)

