import wx

from . import prop_base as _prop_base


class BoolProperty(_prop_base.Property):

    def __init__(self, parent, label, value=False):
        _prop_base.Property.__init__(self, parent, label)
        self._value = value

        self._st = wx.StaticText(self, wx.ID_ANY, label=label + ':')
        self._ctrl = wx.CheckBox(self, wx.ID_ANY, label='')

        self._ctrl.Bind(wx.EVT_CHECKBOX, self._on_change)

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        hsizer.Add(self._ctrl, 0, wx.ALL, 5)

        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def _on_change(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str, value)

    def SetValue(self, value: bool):
        self._ctrl.SetValue(value)

    def GetValue(self) -> bool:
        return self._ctrl.GetValue()
