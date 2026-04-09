import wx

from . import prop_base as _prop_base


class StringProperty(_prop_base.Property):

    def __init__(self, label, name='', value='', style=0, units=None):
        self._style = style
        _prop_base.Property.__init__(self, label, name, value, units)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        if self._ctrl is not None:
            self._ctrl.ChangeValue(value)
            self._value = value

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        style = self._style | wx.TE_LEFT | wx.TE_PROCESS_ENTER

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=self._value, style=style)

        self.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(self._ctrl, 0, wx.ALL | wx.EXPAND, 5)
        self.Add(vsizer, 1)

        if self._units is not None:
            self._units_st = wx.StaticText(parent, wx.ID_ANY, label=self._units)
            self.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

    def _on_enter(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value

        self._send_changed_event(str)
