import wx

from . import prop_base as _prop_base

try:
    from . import autocomplete_combobox as _autocomplete_combobox
except ImportError:
    import autocomplete_combobox as _autocomplete_combobox


class ComboBoxProperty(_prop_base.Property):

    def __init__(self, label, name='', value='', choices=[], units=None):
        self._choices = choices
        _prop_base.Property.__init__(self, label, name, value, units)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(
            parent, wx.ID_ANY, choices=self._choices, style=wx.CB_SORT | wx.TE_PROCESS_ENTER | wx.CB_DROPDOWN)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_change)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self._on_change)

        self.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self._ctrl, 0, wx.ALL | wx.EXPAND, 5)
        self.Add(vsizer, 1)

        if self._units is not None:
            self._units_st = wx.StaticText(parent, wx.ID_ANY, label=self._units)
            self.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

    def _on_change(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str)

    def SetValue(self, value: str):
        items = self._ctrl.GetItems()
        if value in items:
            self._ctrl.SetStringSelection(value)
        else:
            self._ctrl.ChangeValue(value)

    def GetValue(self) -> str:
        return self._ctrl.GetValue()

    def Clear(self):  # NOQA
        self._ctrl.Clear()

    def GetItems(self) -> list[str]:
        return list(self._ctrl.GetItems())[:]

    def SetItems(self, items: list[str]):
        self._ctrl.SetItems(items)
