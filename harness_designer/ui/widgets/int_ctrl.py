import wx


class IntCtrl(wx.BoxSizer):

    def __init__(self, parent, label, min_val, max_val, slider=True):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.SpinCtrl(parent, wx.ID_ANY, value=str(max_val),
                                initial=max_val, min=min_val, max=max_val)

        self.__min_val = min_val
        self.__max_val = max_val

        hsizer.Add(self.st, 1, wx.ALL, 5)
        hsizer.Add(self.ctrl, 1, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        if slider:
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            self.slider = wx.Slider(parent, wx.ID_ANY, value=max_val, minValue=min_val,
                                    maxValue=max_val, style=wx.SL_HORIZONTAL)

            hsizer.Add(self.slider, 1, wx.ALL | wx.EXPAND, 5)
            vsizer.Add(hsizer, 1, wx.EXPAND)

            self.slider.Bind(wx.EVT_SCROLL_CHANGED, self._on_slider_scroll)

        else:
            self.slider: wx.Slider = None

        self.Add(vsizer, 1)

    def _on_slider_scroll(self, evt):
        spin_value = self.slider.GetValue()

        self.ctrl.SetValue(spin_value)

        event = wx.SpinEvent(wx.wxEVT_SPINCTRL)
        event.SetPosition(spin_value)
        event.SetEventObject(self.ctrl)
        event.SetId(self.ctrl.GetId())
        self.ctrl.GetEventHandler().ProcessEvent(event)

        evt.Skip()

    def _on_spin_changed(self, evt: wx.SpinDoubleEvent):
        if self.slider is not None:
            slider_value = self.ctrl.GetValue()
            self.slider.SetValue(slider_value)

        evt.Skip()

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.st.Enable(flag)
        if self.slider is not None:
            self.slider.Enable(flag)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTipString(text)
        self.st.SetToolTipString(text)

        if self.slider is not None:
            self.slider.SetToolTipString(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: int):
        self.ctrl.SetValue(value)

    def GetValue(self) -> int:
        return self.ctrl.GetValue()
