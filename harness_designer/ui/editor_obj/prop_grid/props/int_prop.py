import wx

from . import prop_base as _prop_base


class IntProperty(_prop_base.Property):

    def __init__(self, parent, label, min_value: int, max_value: int, units=None):

        _prop_base.Property.__init__(self, parent, label)

        self._min_val = min_value
        self._max_val = max_value
        self._value = min_value

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.SpinCtrl(self, wx.ID_ANY, value=str(self._value),
                                 initial=self._value, min=self._min_val,
                                 max=self._max_val)

        if units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=units)

        self._slider = wx.Slider(self, wx.ID_ANY, value=self._value,
                                 minValue=self._min_val, maxValue=self._max_val,
                                 style=wx.SL_HORIZONTAL)

        self._slider.Bind(wx.EVT_SLIDER, self._on_slider_scroll)
        self._ctrl.Bind(wx.EVT_SPINCTRL, self._on_spin_changed)

    def SetValue(self, value: float):
        if value > self._max_val:
            value = self._max_val
        if value < self._min_val:
            value = self._min_val

        self._value = value

        self._ctrl.SetValue(value)

        self._slider.SetValue(value)

    def GetValue(self) -> float:
        return self._value

    def Realize(self):
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer1.Add(self._st, 0, wx.TOP, 5)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.Add(self._ctrl, 1, wx.ALL, 5)

        if self._units_st is not None:
            hsizer2.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        vsizer2.Add(hsizer2, 0, wx.EXPAND)

        vsizer2.Add(self._slider, 0, wx.EXPAND)

        hsizer1.Add(vsizer1, 0, wx.ALL, 5)
        hsizer1.Add(vsizer2, 1)

        self._sizer.Add(hsizer1, 0, wx.EXPAND)

    def _on_slider_scroll(self, _):
        value = self._slider.GetValue()
        self._value = value

        self._ctrl.SetValue(value)
        self._send_changed_event(int, value)

    def _on_spin_changed(self, _):
        value = self._ctrl.GetValue()

        self._value = value

        self._slider.SetValue(value)
        self._send_changed_event(int, value)
