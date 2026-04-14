import wx

from . import prop_base as _prop_base


from ....widgets import autocomplete_combobox as _autocomplete_combobox


class ComboBoxProperty(_prop_base.Property):

    def __init__(self, parent, label, value, choices=[], units=None):
        _prop_base.Property.__init__(self, parent, label)
        self._choices = choices
        self._value = value

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(
            self, wx.ID_ANY, choices=self._choices, style=wx.CB_SORT | wx.TE_PROCESS_ENTER | wx.CB_DROPDOWN)

        self._ctrl.SetValue(value)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_change)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self._on_change)

        if units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=units)

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self._ctrl, 0, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(vsizer, 1)

        if self._units_st is not None:
            hsizer.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def _on_change(self, _):
        value = self._ctrl.GetValue()

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(str, value)

    def SetValue(self, value: str):
        if value in self._choices:
            self._ctrl.SetStringSelection(value)
        else:
            self._ctrl.ChangeValue(value)

    def GetValue(self) -> str:
        return self._value

    def Clear(self):  # NOQA
        self._choices = []
        self._ctrl.Clear()

    def GetItems(self) -> list[str]:
        return self._choices

    def SetItems(self, items: list[str]):
        self._choices = items
        self._ctrl.SetItems(items)
