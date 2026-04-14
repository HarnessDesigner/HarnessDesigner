import wx

from . import prop_base as _prop_base

from ....widgets import autocomplete_combobox as _autocomplete_combobox


class ColorProperty(_prop_base.Property):

    def __init__(self, parent, label, value: list[str, wx.Colour], choices=[]):
        _prop_base.Property.__init__(self, parent, label)
        self._value = value
        self._choices = choices
        self._button: wx.ColourPickerCtrl = None

        choices = [item[0] for item in self._choices]

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_SORT | wx.TE_PROCESS_ENTER | wx.CB_DROPDOWN)

        self._ctrl.ChangeValue(value[0])

        self._button = wx.ColourPickerCtrl(self, wx.ID_ANY)
        self._button.SetColour(value[1])

        self._ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_change)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self._on_change)
        self._button.Bind(wx.EVT_COLOURPICKER_CHANGED, self._on_colour)

        self._button.SetColour(value)

    def Realize(self):
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        hsizer2.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        hsizer2.Add(self._ctrl, 1, wx.ALL, 5)
        hsizer2.Add(self._button, 0, wx.ALL, 5)
        vsizer.Add(hsizer2, 0, wx.EXPAND)

        hsizer1.Add(vsizer, 1)

        self._sizer.Add(hsizer1, 0, wx.EXPAND)

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
            self._value = [name, color]
        else:
            name = self._ctrl.GetValue()
            self._value = [name, color]

        self._send_changed_event(list, self._value)

    def _on_change(self, _):
        value = self._ctrl.GetValue()
        values = [item[0] for item in self._choices]

        if value in values:
            index = values.index(value)
            rgba = self._choices[index][1]

            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF

            color = wx.Colour(r, g, b, a)
            self._button.SetColour(color)

            self._value = [value, color]
        else:
            self._value = [value, wx.BLACK]
            self._button.SetColour(wx.BLACK)

        self._send_changed_event(list, self._value)

    def SetValue(self, value: list[str, wx.Colour]):
        values = [item[0] for item in self._choices]

        if value[0] in values:
            self._ctrl.SetStringSelection(value[0])
        else:
            self._ctrl.ChangeValue(value[0])

        self._button.SetColour(value[1])

    def GetValue(self) -> list[str, wx.Colour]:
        return self._value

    def Clear(self):  # NOQA
        self._choices = []
        self._ctrl.Clear()

    def GetItems(self) -> list[list[str, int]]:
        return self._choices

    def SetItems(self, items: list[list[str, int]]):
        self._choices = items
        self._ctrl.SetItems([item[0] for item in items])
