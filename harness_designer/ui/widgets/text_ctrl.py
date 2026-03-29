import wx


class TextCtrl(wx.BoxSizer):
    """
    styles that can be used.
    wx.TE_READONLY
    wx.TE_MULTILINE

    This control does not word wrap and a horizontal scroll bar will be visible
    should the text exceed the controls length.

    when using multiline once again there is no text wrap and there will be a
    vertical scroll bar visible should the text exceed the controls height. The
    horizontal scroll bar will also be show as explained above.

    when using multiline pressing enter will advance to the next line in the
    control. This behavior overrides pressing the default button if the control
    is used in a dialog.

    There is an apply button so when binding to update the databse bind
    wx.EVT_BUTTON to know when you need to update the database.

    """

    def __init__(self, parent, label, size, style=0, apply_button=True, hslider=True):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        self._show_apply_button = apply_button

        # width, height = size
        # if height == -1:
        #     height = parent.GetTextExtent('W')[1]
        #
        # size = (width, int(height * 2.6))

        style |= wx.TE_LEFT | wx.TE_PROCESS_ENTER

        if hslider:
            style |= wx.HSCROLL

        self.st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.TextCtrl(parent, wx.ID_ANY, value='', size=size, style=style)
        self.apply_button = wx.Button(parent, wx.ID_ANY, label='Apply')
        self.apply_button.Enable(False)
        self.apply_button.Show(apply_button)

        self._original_text = ''

        self.ctrl.Bind(wx.EVT_TEXT, self._on_text)
        self.ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

        if style & wx.TE_MULTILINE:
            self.Add(self.st, 1, wx.ALL | wx.ALIGN_TOP, 5)
        elif hslider:
            self.Add(self.st, 1, wx.ALL, 5)
        else:
            self.Add(self.st, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        self.Add(self.ctrl, 4, wx.ALL, 5)
        self.Add(self.apply_button, 1, wx.ALL, 5)

    def SetStyle(self, start: int, end: int, style: wx.TextAttr):
        self.ctrl.SetStyle(start, end, style)

    def _on_text(self, evt: wx.CommandEvent):
        if self._show_apply_button:
            def _do():
                text = self.ctrl.GetValue()
                self.apply_button.Enable(text != self._original_text)

            wx.CallAfter(_do)

        evt.Skip()

    def _on_enter(self, _):
        index = self.ctrl.GetInsertionPoint()
        start_text = self.ctrl.GetRange(0, index)
        all_text = self.ctrl.GetValue()
        all_text = all_text.replace(start_text, '')
        all_text = f'{start_text}\n{all_text}'
        self.ctrl.ChangeValue(all_text)
        self.ctrl.SetInsertionPoint(index + 1)

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.st.Enable(flag)

        if self._show_apply_button:
            if flag:
                flag = self._original_text != self.ctrl.GetValue()
                self.apply_button.Enable(flag)
            else:
                self.apply_button.Enable(flag)

    def SetToolTip(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def Bind(self, event, handler):
        if self._show_apply_button:
            self.apply_button.Bind(event, handler)
        else:
            self.ctrl.Bind(event, handler)

    def SetValue(self, value: str):
        self._original_text = value
        self.ctrl.ChangeValue(value)

    def GetValue(self) -> str:
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

    ctrl1 = TextCtrl(sb, 'This is a test:', size=(100, -1), hslider=False)
    ctrl2 = TextCtrl(sb, 'This is a test:', size=(100, 40), hslider=True)

    sz.Add(ctrl1, 0, wx.ALL, 5)
    sz.Add(ctrl2, 1, wx.ALL, 5)

    sizer = wx.BoxSizer(wx.VERTICAL)

    sizer.Add(sz, 1, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(sizer)

    frame.Show()

    app.MainLoop()