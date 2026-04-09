import wx

from . import prop_base as _prop_base


class IntProperty(_prop_base.Property):

    def __init__(self, label, name='', value=0, min_value=0, max_value=100, units=None):
        self._min_val = min_value
        self._max_val = max_value
        self._slider = None
        _prop_base.Property.__init__(self, label, name, value, units)

    def GetValue(self) -> int:
        return self._value

    def SetValue(self, value: int):
        if self._ctrl is not None:
            self._ctrl.SetValue(value)
            self._slider.SetValue(value)
            self._value = value

    def Show(self):
        self._slider.Show()
        _prop_base.Property.Show(self)

    def Hide(self):
        self._slider.Hide()
        _prop_base.Property.Hide(self)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.SpinCtrl(
            parent, wx.ID_ANY, value=str(self._value),
            initial=self._value, min=self._min_val, max=self._max_val
            )

        vsizer1.Add(self._st, 0, wx.TOP, 5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._ctrl, 1, wx.ALL, 5)

        if self._units is not None:
            self._units_st = wx.StaticText(parent, wx.ID_ANY, label=self._units)
            hsizer.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        vsizer2.Add(hsizer, 0, wx.EXPAND)

        self._slider = wx.Slider(parent, wx.ID_ANY, value=self._value,
                                 minValue=self._min_val, maxValue=self._max_val,
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
        spin_value = self._slider.GetValue()

        self._ctrl.SetValue(spin_value)
        self._send_changed_event(int)

    def _on_spin_changed(self, _):
        slider_value = self._ctrl.GetValue()
        self._slider.SetValue(slider_value)

        self._send_changed_event(int)
