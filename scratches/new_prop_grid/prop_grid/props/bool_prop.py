import wx

from . import prop_base as _prop_base


class BoolProperty(_prop_base.Property):

    def __init__(self, label, name='', value=False):
        _prop_base.Property.__init__(self, label, name, value, None)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.CheckBox(parent, wx.ID_ANY, label='')

        self.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.Add(self._ctrl, 0, wx.ALL, 5)

        self._ctrl.Bind(wx.EVT_CHECKBOX, self._on_change)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

    def _on_change(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str)

    def SetValue(self, value: bool):
        self._ctrl.SetValue(value)

    def GetValue(self) -> bool:
        return self._ctrl.GetValue()

