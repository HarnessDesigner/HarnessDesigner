import wx

from . import prop_base as _prop_base

from ....widgets import autocomplete_combobox as _autocomplete_combobox


class ColorProperty(_prop_base.Property):

    def __init__(self, label, name='', value=None, choices=[]):
        self._choices = choices
        self._button: wx.ColourPickerCtrl = None
        _prop_base.Property.__init__(self, label, name, value, None)

    def Create(self, parent):
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        choices = [item[0] for item in self.choices]

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(
            parent, wx.ID_ANY, choices=choices, style=wx.CB_SORT | wx.TE_PROCESS_ENTER | wx.CB_DROPDOWN)

        self._button = wx.ColourPickerCtrl(parent, wx.ID_ANY)

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_change)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self._on_change)
        self._button.Bind(wx.EVT_COLOURPICKER_CHANGED, self._on_colour)

        self._button.SetColour(self._value)

        hsizer.Add(self._st, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        hsizer.Add(self._ctrl, 1, wx.ALL, 5)
        hsizer.Add(self._button, 1, wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        if self._tooltip is not None:
            self._ctrl.SetToolTip(self._tooltip)
            self._st.SetToolTip(self._tooltip)

        self.Add(vsizer, 1)

    def _on_colour(self, _):
        color = self._button.GetColour()
        r = color.GetRed()
        g = color.GetGreen()
        b = color.GetBlue()

        rgba = r << 24 | g << 16 | b << 8 | 0xFF

        colors = [item[1] for item in self._choices]

        if rgba in colors:
            index = colors.index(rgba)
            name = self._choices[index][0]
            self._ctrl.SetValue(name)

            self._send_changed_event(wx.Colour)

    def _on_change(self, _):
        value = self._ctrl.GetValue()
        values = [item[0] for item in self._choices]

        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]

            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF

            color = wx.Colour(r, g, b, a)
            self._button.SetColour(color)

            self._value = color
            self._send_changed_event(wx.Colour)

    def SetValue(self, value: str):
        items = self._ctrl.GetItems()
        if value in items:
            self._ctrl.SetStringSelection(value)
        else:
            self._ctrl.ChangeValue(value)

    def GetValue(self) -> wx.Colour:
        return self._value

    def Clear(self):  # NOQA
        self._ctrl.Clear()

    def GetItems(self) -> list[list[str, int]]:
        return self._choices

    def SetItems(self, items: list[[str, int]]):
        self._choices = items
        self._ctrl.SetItems([item[0] for item in items])
