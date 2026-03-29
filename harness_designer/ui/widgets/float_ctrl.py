import wx

try:
    from ... import utils as _utils
    from ...geometry.decimal import Decimal as _d
except ImportError:
    pass


class FloatCtrl(wx.BoxSizer):

    def __init__(self, parent, label, min_val, max_val, inc, slider=True):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.SpinCtrlDouble(parent, wx.ID_ANY, value=str(max_val),
                                      initial=max_val, min=min_val, max=max_val, inc=inc)

        self.__min_val = min_val
        self.__max_val = max_val
        self.__increment = inc

        precision = 0
        inc = _d(self.__increment)

        while inc < 1:
            precision += 1
            inc *= _d(10.0)

        self.__precision = precision

        value_range = _d(max_val) - _d(min_val)
        middle_value = (value_range / _d(2.0)) + _d(min_val)

        inc = _d(self.__increment)

        remaining = middle_value % inc

        if remaining:
            middle_value += inc - remaining

        self.ctrl.SetValue(float(middle_value))

        hsizer.Add(self.st, 1, wx.RIGHT, 5)
        hsizer.Add(self.ctrl, 1, wx.LEFT, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        if slider:
            s_inc = _d(10) * _d(self.__precision)
            slider_max = _d(100) * s_inc

            self.__s_max = int(slider_max)
            slider_value = _utils.remap(middle_value, self.__min_val, self.__max_val, 0, self.__s_max)

            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            self.slider = wx.Slider(parent, wx.ID_ANY, value=int(slider_value), minValue=0,
                                    maxValue=int(slider_max), style=wx.SL_HORIZONTAL)

            hsizer.Add(self.slider, 1)
            vsizer.Add(hsizer, 1, wx.EXPAND)

            self.slider.Bind(wx.EVT_SLIDER, self._on_slider_scroll)
            self.ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_spin_changed)

        else:
            self.slider: wx.Slider = None

        self.Add(vsizer, 1)

    def _on_slider_scroll(self, evt):
        slider_value = self.slider.GetValue()
        spin_value = _utils.remap(slider_value, 0, self.__s_max,
                                  self.__min_val, self.__max_val)

        inc = _d(self.__increment)
        remaining = spin_value % inc

        if remaining:
            spin_value += inc - remaining

        self.ctrl.SetValue(float(spin_value))

        event = wx.SpinDoubleEvent(wx.wxEVT_SPINCTRLDOUBLE)
        event.SetValue(float(spin_value))
        event.SetEventObject(self.ctrl)
        event.SetId(self.ctrl.GetId())
        self.ctrl.GetEventHandler().ProcessEvent(event)

        evt.Skip()

    def _on_spin_changed(self, evt: wx.SpinDoubleEvent):
        if self.slider is not None:
            spin_value = self.ctrl.GetValue()
            slider_value = _utils.remap(spin_value, self.__min_val, self.__max_val,
                                        0, self.__s_max)

            self.slider.SetValue(int(slider_value))

        evt.Skip()

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.st.Enable(flag)
        if self.slider is not None:
            self.slider.Enable(flag)

    def SetToolTip(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

        if self.slider is not None:
            self.slider.SetToolTip(text)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

        if self.slider is not None:
            self.slider.SetToolTip(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: float):
        value = round(value, self.__precision)
        value = _d(value)
        inc = _d(self.__increment)

        remaining = value % inc

        if remaining:
            value += inc - remaining

        if value > self.__max_val:
            value = self.__max_val
        if value < self.__min_val:
            value = self.__min_val

        self.ctrl.SetValue(float(value))

        if self.slider is not None:
            slider_value = _utils.remap(value, self.__min_val, self.__max_val,
                                        0, self.__s_max)

            self.slider.SetValue(int(slider_value))

    def GetValue(self) -> float:
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

    ctrl = FloatCtrl(sb, 'This is a test:', min_val=0.0, max_val=99999.09, inc=0.01)

    sz.Add(ctrl, 1, wx.ALL, 5)

    sizer = wx.BoxSizer(wx.VERTICAL)

    sizer.Add(sz, 1, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(sizer)

    frame.Show()

    app.MainLoop()
