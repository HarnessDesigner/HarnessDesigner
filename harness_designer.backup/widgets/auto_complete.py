import wx


class AutoCompleter(wx.TextCompleter):
    def __init__(self, choices):
        self.choices = choices
        wx.TextCompleter.__init__(self)
        self._iLastReturned = wx.NOT_FOUND
        self._sPrefix = ''

    def Start(self, prefix):
        self._sPrefix = prefix.lower()
        self._iLastReturned = wx.NOT_FOUND

        for item in self.choices:
            if item.lower().startswith(self._sPrefix):
                return True

        return False

    def SetChoices(self, choices):
        self.choices = choices[:]

    def GetChoices(self):
        return self.choices[:]

    def GetNext(self):
        for i in range(self._iLastReturned + 1, len(self.choices)):
            if self.choices[i].lower().startswith(self._sPrefix):
                self._iLastReturned = i
                return self.choices[i]

        return ''


class AutoComplete(wx.TextCtrl):

    def __init__(self, parent, id=wx.ID_ANY, value='', pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, validator=wx.DefaultValidator,
                 name=wx.TextCtrlNameStr, autocomplete_choices=[]):

        wx.TextCtrl.__init__(self, parent, id, value=value, pos=pos, size=size,
                             style=style, validator=validator, name=name)

        self._ac = AutoCompleter(autocomplete_choices[:])
        self.AutoComplete(self._ac)

    def SetAutoCompleteChoices(self, choices):
        self._ac.SetChoices(choices)

    def GetAutoCompleteChoices(self):
        return self._ac.GetChoices()
