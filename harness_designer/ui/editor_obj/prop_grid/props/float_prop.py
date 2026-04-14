import wx

from . import prop_base as _prop_base

from ..... import utils as _utils
from .....geometry.decimal import Decimal as _d


class FloatProperty(_prop_base.Property):

    def __init__(self, parent, label, value: float, min_value: float, max_value: float, increment: float, units=None):

        _prop_base.Property.__init__(self, parent, label)

        self._min_val = min_value
        self._max_val = max_value
        self._value = value
        self._inc = increment

        precision = 0
        inc = _d(increment)

        while inc < 1:
            precision += 1
            inc *= _d(10.0)

        self._precision = precision

        s_inc = _d(10) * _d(precision)
        slider_max = _d(100) * s_inc

        self._s_max = int(slider_max)

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(self._value),
                                       initial=self._value, min=self._min_val,
                                       max=self._max_val, inc=self._inc)

        if units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=units)

        slider_value = _utils.remap(self._value, self._min_val, self._max_val, 0, self._s_max)

        self._slider = wx.Slider(self, wx.ID_ANY, value=int(slider_value),
                                 minValue=0, maxValue=self._s_max,
                                 style=wx.SL_HORIZONTAL)

        self._slider.Bind(wx.EVT_SLIDER, self._on_slider_scroll)
        self._ctrl.Bind(wx.EVT_SPINCTRL, self._on_spin_changed)

    def SetValue(self, value: float):
        value = round(value, self._precision)
        value = _d(value)
        inc = _d(self._inc)

        remaining = value % inc

        if remaining:
            value += inc - remaining

        if value > self._max_val:
            value = self._max_val
        if value < self._min_val:
            value = self._min_val

        self._value = float(value)

        self._ctrl.SetValue(self._value)

        slider_value = _utils.remap(value, self._min_val, self._max_val,
                                    0, self._s_max)

        self._slider.SetValue(int(slider_value))

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
        slider_value = self._slider.GetValue()
        spin_value = _utils.remap(slider_value, 0, self._s_max,
                                  self._min_val, self._max_val)

        inc = _d(self._inc)
        remaining = spin_value % inc

        if remaining:
            spin_value += inc - remaining

        self._value = float(spin_value)

        self._ctrl.SetValue(self._value)
        self._send_changed_event(float, self._value)

    def _on_spin_changed(self, _):
        spin_value = self._ctrl.GetValue()
        slider_value = _utils.remap(spin_value, self._min_val, self._max_val,
                                    0, self._s_max)

        self._value = spin_value

        self._slider.SetValue(int(slider_value))
        self._send_changed_event(float, spin_value)
