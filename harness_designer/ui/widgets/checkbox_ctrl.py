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

    def SetToolTip(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: bool):
        self.ctrl.SetValue(value)

    def GetValue(self) -> bool:
        return self.ctrl.GetValue()


if __name__ == '__main__':
    app = wx.App()

    frame = wx.Frame(None, wx.ID_ANY, size=(600, 300))
    panel = wx.Panel(frame, wx.ID_ANY, style=wx.BORDER_NONE)
    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    hsizer.Add(panel, 1, wx.EXPAND)

    vsizer = wx.BoxSizer(wx.VERTICAL)
    vsizer.Add(hsizer, 1, wx.EXPAND)

    frame.SetSizer(vsizer)

    sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Static Box")
    sb = sz.GetStaticBox()

    ctrl = CheckboxCtrl(sb, 'This is a test:')

    sz.Add(ctrl, 1, wx.ALL, 5)

    sizer = wx.BoxSizer(wx.VERTICAL)

    sizer.Add(sz, 1, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(sizer)

    frame.Show()

    app.MainLoop()

