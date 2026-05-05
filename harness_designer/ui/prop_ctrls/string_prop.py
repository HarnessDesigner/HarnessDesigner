import wx

from . import prop_base as _prop_base


class StringProperty(_prop_base.Property):

    def __init__(self, parent, label, style=0, units=None):

        _prop_base.Property.__init__(self, parent, label)

        self._value = ''

        style |= wx.TE_LEFT | wx.TE_PROCESS_ENTER

        self._st = wx.StaticText(self, wx.ID_ANY, label=label + ':')
        self._ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', style=style)

        if units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=units)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._ctrl.ChangeValue(value)
        self._value = value

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(self._ctrl, 0, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(vsizer, 1)

        if self._units_st is not None:
            hsizer.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def _on_enter(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str, value)
