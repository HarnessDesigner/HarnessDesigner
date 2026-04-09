import wx

from . import prop_base as _prop_base

from ..... import utils as _utils
from .....geometry.decimal import Decimal as _d


class FloatProperty(_prop_base.Property):

    def __init__(self, label, name='', value=0.0, min_value=0.0, max_value=100.0, increment=0.1, units=None):
        self._min_val = min_value
        self._max_val = max_value
        self._inc = increment
        self._slider = None

        precision = 0
        inc = _d(increment)

        while inc < 1:
            precision += 1
            inc *= _d(10.0)

        self._precision = precision

        s_inc = _d(10) * _d(precision)
        slider_max = _d(100) * s_inc

        self._s_max = int(slider_max)

        _prop_base.Property.__init__(self, label, name, value, units)

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

        self._ctrl.SetValue(float(value))

        slider_value = _utils.remap(value, self._min_val, self._max_val,
                                    0, self._s_max)

        self._slider.SetValue(int(slider_value))

    def Show(self):
        self._slider.Show()
        _prop_base.Property.Show(self)

    def Hide(self):
        self._slider.Hide()
        _prop_base.Property.Hide(self)

    def GetValue(self) -> float:
        return self._ctrl.GetValue()

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.SpinCtrlDouble(parent, wx.ID_ANY, value=str(self._value),
                                       initial=self._value, min=self._min_val,
                                       max=self._max_val, inc=self._inc)

        vsizer1.Add(self._st, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._ctrl, 1, wx.ALL, 5)

        if self._units is not None:
            self._units_st = wx.StaticText(parent, wx.ID_ANY, label=self._units)
            hsizer.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        vsizer2.Add(hsizer, 0, wx.EXPAND)

        slider_value = _utils.remap(self._value, self._min_val, self._max_val, 0, self._s_max)

        self._slider = wx.Slider(parent, wx.ID_ANY, value=int(slider_value),
                                 minValue=0, maxValue=self._s_max,
                                 style=wx.SL_HORIZONTAL)

        vsizer2.Add(self._slider, 0, wx.EXPAND)

        self._slider.Bind(wx.EVT_SLIDER, self._on_slider_scroll)
        self._ctrl.Bind(wx.EVT_SPINCTRL, self._on_spin_changed)

        # vsizer1.AddStretchSpacer(1)
        self.Add(vsizer1, 0, wx.ALL, 5)
        self.Add(vsizer2, 1)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._slider.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

    def _on_slider_scroll(self, _):
        slider_value = self._slider.GetValue()
        spin_value = _utils.remap(slider_value, 0, self._s_max,
                                  self._min_val, self._max_val)

        inc = _d(self._inc)
        remaining = spin_value % inc

        if remaining:
            spin_value += inc - remaining

        self._ctrl.SetValue(float(spin_value))
        self._send_changed_event(float)

    def _on_spin_changed(self, _):
        spin_value = self._ctrl.GetValue()
        slider_value = _utils.remap(spin_value, self._min_val, self._max_val,
                                    0, self._s_max)

        self._slider.SetValue(int(slider_value))
        self._send_changed_event(float)
