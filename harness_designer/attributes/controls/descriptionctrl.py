import wx
from wx.lib import expando as _expando

from ... import utils


class DescriptionCtrl(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.ctrl = _expando.ExpandoTextCtrl(self, wx.ID_ANY, size=(250, -1), value='')
        self.ctrl.Bind(_expando.EVT_ETC_LAYOUT_NEEDED, self.on_layout)

        sizer = utils.HSizer(self, 'Description:', self.ctrl)
        self.SetSizer(sizer)

    def SetValue(self, value: str):
        self.ctrl.SetValue(value)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()

    def on_layout(self, evt):
        self.Fit()
        self.GetParent().Fit()
        evt.Skip()



