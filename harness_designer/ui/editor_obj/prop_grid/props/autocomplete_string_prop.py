import wx

from . import prop_base as _prop_base
from ....widgets import autocomplete_textctrl as _autocomplete_textctrl


class AutocompleteStringProperty(_prop_base.Property):

    def __init__(self, parent, label, value='', style=0, choices=[], units=None):
        style |= wx.TE_LEFT | wx.TE_PROCESS_ENTER
        self._choices = choices
        self._value = value

        _prop_base.Property.__init__(self, parent, label)

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')

        self._ctrl = _autocomplete_textctrl.AutoCompleteTextCtrl(
            self, wx.ID_ANY, style=style, choices=self._choices)

        self._ctrl.SetValue(value)

        if units is not None:
            self._units_st = wx.StaticText(self, wx.ID_ANY, label=units)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self._ctrl, 0, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(vsizer, 1)

        if self._units_st is not None:
            hsizer.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.ChangeValue(value)

    def SetItems(self, items: list[str]) -> None:
        if self._ctrl is not None:
            self._ctrl.SetItems(items)

        self._choices = items

    def _on_enter(self, _):
        index = self._ctrl.GetInsertionPoint()
        start_text = self._ctrl.GetRange(0, index)
        all_text = self._ctrl.GetValue()
        all_text = all_text.replace(start_text, '')
        all_text = f'{start_text}\n{all_text}'

        self._ctrl.ChangeValue(all_text)
        self._ctrl.SetInsertionPoint(index + 1)

        if all_text.endswith('\n\n') and self._value.endswith('\n'):
            self._value = all_text.rstrip()

            self._choices.append(self._value)
            self._ctrl.SetItems(self._choices)
            self._ctrl.ChangeValue(self._value)
            self._ctrl.SetInsertionPoint(self._ctrl.GetLastPosition())

            self._send_changed_event(str, self._value)
        else:
            self._value = all_text
