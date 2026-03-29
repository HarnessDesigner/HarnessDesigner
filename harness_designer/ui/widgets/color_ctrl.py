
import wx

from . import combobox_ctrl as _combobox_ctrl
from ... import color as _color


class ColorCtrl(wx.BoxSizer):

    def __init__(self, parent, label, table):

        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        table.execute('SELECT id, name, rgb FROM colors;')
        rows = table.fetchall()

        self._choices = sorted([row for row in rows], key=lambda x: x[1])

        self.ctrl = _combobox_ctrl.ComboBoxCtrl(parent, label, [item[1] for item in self._choices])
        self.button = wx.ColourPickerCtrl(parent, wx.ID_ANY)

        self.ctrl.Bind(wx.EVT_COMBOBOX, self._on_combobox)
        self.button.Bind(wx.EVT_COLOURPICKER_CHANGED, self._on_colour)
        self.Add(self.ctrl, 2, wx.EXPAND)
        self.Add(self.Button, 1, wx.ALL | wx.EXPAND, 5)

    def _on_colour(self, _):
        color = self.button.GetColour()
        r = color.GetRed()
        g = color.GetGreen()
        b = color.GetBlue()

        rgba = r << 24 | g << 16 | b << 8 | 0xFF

        colors = [item[2] for item in self._choices]

        if rgba in colors:
            index = colors.index(rgba)
            name = self._choices[index][1]
            self.ctrl.SetValue(name)

        event = wx.ColourPickerEvent(wx.wxEVT_COLOURPICKER_CHANGED)
        event.SetColour(color)
        event.SetEventObject(self.ctrl)
        event.SetId(self.ctrl.GetId())
        self.ctrl.GetEventHandler().ProcessEvent(event)

    def _on_combobox(self, evt):
        value = self.ctrl.GetValue()
        values = [item[1] for item in self._choices]

        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]

            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF

            color = wx.Colour(r, g, b, a)
            self.button.SetColour(color)

            event = wx.ColourPickerEvent(wx.wxEVT_COLOURPICKER_CHANGED)
            event.SetColour(color)
            event.SetEventObject(self.ctrl)
            event.SetId(self.ctrl.GetId())
            self.ctrl.GetEventHandler().ProcessEvent(event)

        evt.Skip()

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.button.Enable(flag)

    def SetToolTip(self, text):
        self.ctrl.SetToolTip(text)
        self.button.SetToolTip(text)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTip(text)
        self.button.SetToolTip(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def GetColour(self) -> _color.Color:

        color = self.button.GetColour()
        name = self.GetValue()
        if name in ('None', 'Transparent'):
            a = 0
        else:
            a = 255

        return _color.Color(color.GetRed(), color.GetGreen(), color.GetBlue(), a)

    def GetValue(self):
        return self.ctrl.GetValue()

    def SetValue(self, value):
        values = [item[1] for item in self._choices]

        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]

            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF

            color = wx.Colour(r, g, b, a)
            self.button.SetColour(color)

        self.ctrl.SetValue(value)

