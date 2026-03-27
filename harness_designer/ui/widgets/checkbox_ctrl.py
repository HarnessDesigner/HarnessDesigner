import wx


class CheckboxCtrl(wx.BoxSizer):

    def __init__(self, parent, label):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.CheckBox(parent, wx.ID_ANY, label='')

        self.Add(self.st, 1, wx.RIGHT, 5)
        self.Add(self.ctrl, 1, wx.LEFT, 5)

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.st.Enable(flag)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTipString(text)
        self.st.SetToolTipString(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: bool):
        self.ctrl.SetValue(value)

    def GetValue(self) -> bool:
        return self.ctrl.GetValue()
