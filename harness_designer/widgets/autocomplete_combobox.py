
import wx


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


class AutoCompleteComboBox(wx.ComboBox):

    def __init__(
        self, parent, id=wx.ID_ANY, choices=[], pos=wx.DefaultPosition,
        size=wx.DefaultSize, style=0, validator=wx.DefaultValidator,
        name=wx.ComboBoxNameStr
    ):
        wx.ComboBox.__init__(self, parent, id, pos=pos, size=size, style=style,
                             validator=validator, name=name, choices=choices)

        self._ac = AutoCompleter(choices[:])
        self.AutoComplete(self._ac)

    def Clear(self):
        wx.ComboBox.Clear(self)
        self._ac.SetChoices([])

    def Delete(self, n: int):
        wx.ComboBox.Delete(self, n)
        self._ac.RemoveChoice(n)

    def Insert(self, item: str, pos: int, clientData):
        wx.ComboBox.Insert(self, item, pos, clientData)
        self._ac.InsertChoice(item, pos)

    def Set(self, items):
        self.SetItems(items)

    def SetItems(self, items: list[str]):
        wx.ComboBox.SetItems(self, items)
        self._ac.SetChoices(items)
