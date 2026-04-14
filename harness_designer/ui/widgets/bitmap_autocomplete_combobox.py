
import wx
import wx.adv


class AutoCompleter(wx.TextCompleter):
    def __init__(self, choices):
        wx.TextCompleter.__init__(self)

        self.choices = choices
        self._last_returned = wx.NOT_FOUND
        self._prefix = ''

    def Start(self, prefix):
        self._prefix = prefix.lower()
        self._last_returned = wx.NOT_FOUND

        for item in self.choices:
            if item.lower().startswith(self._prefix):
                return True

        return False

    def AppendChoices(self, choices):
        self.choices.extend(choices[:])

    def SetChoices(self, choices):
        self.choices = choices[:]
        self._last_returned = wx.NOT_FOUND
        self._prefix = ''

    def GetChoices(self):
        return self.choices[:]

    def InsertChoice(self, item: str, pos: int):
        self.choices.insert(pos, item)

    def RemoveChoice(self, pos: int):
        self.choices.pop(pos)

    def GetNext(self):
        for i in range(self._last_returned + 1, len(self.choices)):
            if self.choices[i].lower().startswith(self._prefix):
                self._last_returned = i
                return self.choices[i]

        return ''


class BitmapAutoCompleteComboBox(wx.adv.BitmapComboBox):

    def __init__(
        self, parent, id=wx.ID_ANY, choices: list[str, wx.Bitmap, str] = [], pos=wx.DefaultPosition,
        size=wx.DefaultSize, style=0, validator=wx.DefaultValidator,
        name=wx.adv.BitmapComboBoxNameStr
    ):

        style |= wx.TE_PROCESS_ENTER

        wx.adv.BitmapComboBox.__init__(self, parent, id, value='', pos=pos, size=size, choices=[],
                                       style=style, validator=validator, name=name)

        self.choices = choices
        self._ac = AutoCompleter([choice[0] for choice in choices])
        self.AutoComplete(self._ac)

        self.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self.Bind(wx.EVT_COMBOBOX, self._on_selection)

        for item in choices:
            self.Append(*item)

    def _on_selection(self, evt):
        evt.Skip()
        selection = self.GetSelection()

        if selection != wx.NOT_FOUND:
            tooltip = self.GetClientData(selection)
            self.SetToolTip(tooltip)

    def _on_enter(self, evt):
        evt.Skip()
        selection = self.GetSelection()

        if selection != wx.NOT_FOUND:
            tooltip = self.GetClientData(selection)
            self.SetToolTip(tooltip)

    def Clear(self):
        wx.adv.BitmapComboBox.Clear(self)
        self._ac.SetChoices([])

    def Delete(self, n: int):
        wx.adv.BitmapComboBox.Delete(self, n)
        self._ac.RemoveChoice(n)

    def Insert(self, item: str, bitmap: wx.Bitmap, pos: int, clientData=None):
        wx.adv.BitmapComboBox.Insert(self, item, bitmap, pos, clientData)
        self._ac.InsertChoice(item, pos)

    def Set(self, items):
        wx.ComboBox.Set(self, items)
        self._ac.SetChoices(items)

    def SetItems(self, items: list[str]):
        wx.adv.BitmapComboBox.SetItems(self, items)

    def Append(self, item, bitmap: wx.Bitmap, clientData=None):
        res = wx.adv.BitmapComboBox.Append(self, item, bitmap, clientData)
        self._ac.AppendChoices(item)

        return res
