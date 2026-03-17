import wx

from ... import utils as _utils
from ...geometry.decimal import Decimal as _d


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

        hsizer.Add(self.st, 1, wx.ALL, 5)
        hsizer.Add(self.ctrl, 1, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        if slider:
            slider_max = 100
            s_inc = inc
            while s_inc < 0:
                s_inc *= 10
                slider_max *= 10

            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            self.slider = wx.Slider(parent, wx.ID_ANY, value=slider_max, minValue=0,
                                    maxValue=slider_max, style=wx.SL_HORIZONTAL)

            self.__s_max = slider_max

            hsizer.Add(self.slider, 1, wx.ALL | wx.EXPAND, 5)
            vsizer.Add(hsizer, 1, wx.EXPAND)

            self.slider.Bind(wx.EVT_SCROLL_CHANGED, self._on_slider_scroll)

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
            spin_value = _utils.remap(spin_value, self.__min_val, self.__max_val,
                                      0, self.__s_max)

            self.slider.SetValue(int(spin_value))

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

    def SetValue(self, value: float):
        inc = self.__increment
        precision = 0

        while inc < 1:
            precision += 1
            inc *= 10.0

        value = round(value, precision)
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

    def GetValue(self) -> float:
        return self.ctrl.GetValue()

