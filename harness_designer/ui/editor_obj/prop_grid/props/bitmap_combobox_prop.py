import wx

from . import prop_base as _prop_base


from ....widgets import bitmap_autocomplete_combobox as _bitmap_autocomplete_combobox


class BitmapComboBoxProperty(_prop_base.Property):

    def __init__(self, label, name='', value='', choices=[], units=None):
        self._choices = choices
        _prop_base.Property.__init__(self, label, name, value, units)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')
        self._ctrl = _bitmap_autocomplete_combobox.BitmapAutoCompleteComboBox(
            self, wx.ID_ANY, choices=self._choices, style=wx.CB_SORT | wx.CB_DROPDOWN)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_change)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self._on_change)

        hsizer2.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        hsizer2.Add(self._ctrl, 1, wx.ALL, 5)

        if self._units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=self._units)
            hsizer2.Add(self._units_st, 0, wx.ALL, 5)

        vsizer.Add(hsizer2, 0, wx.EXPAND)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

        hsizer1.Add(vsizer, 1)

        self.SetSizer(hsizer1)

    def _on_change(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str)

    def SetValue(self, value: str):
        items = [item[0] for item in self.choices]
        if value in items:
            self.ctrl.SetStringSelection(value)
        else:
            self.ctrl.ChangeValue(value)

    def GetValue(self) -> str:
        return self._ctrl.GetValue()

    def Clear(self):  # NOQA
        self._ctrl.Clear()

    def GetItems(self) -> list[str]:
        return list(self.ctrl.GetItems())[:]

    def SetItems(self, items: list[str]):
        self.ctrl.SetItems(items)
