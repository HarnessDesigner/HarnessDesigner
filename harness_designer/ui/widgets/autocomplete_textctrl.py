
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


class AutoCompleteTextCtrl(wx.TextCtrl):

    def __init__(
        self, parent, id=wx.ID_ANY, choices=[], pos=wx.DefaultPosition,
        size=wx.DefaultSize, style=0, validator=wx.DefaultValidator,
        name=wx.TextCtrlNameStr
    ):
        wx.TextCtrl.__init__(self, parent, id, value='', pos=pos, size=size,
                             style=style, validator=validator, name=name)

        self._ac = AutoCompleter(choices[:])
        self.AutoComplete(self._ac)

    def SetValue(self, value: str) -> None:
        self.ChangeValue(value)

    def Clear(self) -> None:
        self._ac.SetChoices([])

    def Delete(self, n: int) -> None:
        self._ac.RemoveChoice(n)

    def Insert(self, item: str, pos: int) -> None:
        self._ac.InsertChoice(item, pos)

    def Set(self, items) -> None:
        self._ac.SetChoices(items)

    def SetItems(self, items: list[str]) -> None:
        self._ac.SetChoices(items)

    def Append(self, item) -> None:
        self._ac.AppendChoices(item)
