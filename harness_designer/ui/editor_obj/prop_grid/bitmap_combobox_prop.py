
import wx
from wx import propgrid as wxpg

from ...widgets import bitmap_autocomplete_combobox as _bitmap_autocomplete_combobox


class BitmapComboboxCtrl(wx.Panel):

    def __init__(self, parent, value, choices: list[str, wx.Bitmap, str], pos, size):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE,
                          pos=pos, size=size)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self._choices = choices

        self.__ctrl = _bitmap_autocomplete_combobox.BitmapAutoCompleteComboBox(
            parent, wx.ID_ANY, choices=choices, style=wx.CB_SORT | wx.CB_DROPDOWN)

        hsizer.Add(self.__ctrl, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(vsizer)

        self.SetValue(value)

        wx.CallAfter(self.SendSizeEvent)

    def SetValue(self, value: str):
        choices = [item[0] for item in self._choices]

        if value in choices:
            self.ctrl.SetStringSelection(value)
        else:
            self.ctrl.ChangeValue(value)

    def InsertItem(self, label, bitmap, tooltip, index):
        self._choices.insert(index, [label, bitmap, tooltip])

        value = self.GetValue()

        self.__ctrl.Clear()
        for item in self._choices:
            self.__ctrl.Append(*item)

        self.SetValue(value)

    def DeleteItem(self, index):
        value = self.GetValue()
        self._choices.pop(index)

        self.__ctrl.Clear()
        for item in self._choices:
            self.__ctrl.Append(*item)

        self.SetValue(value)

    def GetValue(self):
        return self.__ctrl.GetValue()

    def GetLastPosition(self) -> int:
        return self.__ctrl.GetLastPosition()

    def SetSelection(self, start, stop):
        self.__ctrl.SetSelection(start, stop)


class BitmapComboboxEditor(wxpg.PGEditor):

    def __init__(self):
        wxpg.PGEditor.__init__(self)

    def GetName(self):
        return 'Combobox'

    def CreateControls(self, propgrid, prop, pos, sz):
        value = prop.GetDisplayedString()
        choices = prop.GetChoices()

        ctrl = BitmapComboboxCtrl(propgrid.GetPanel(), value=value, choices=choices, pos=pos, size=sz)

        return wxpg.PGWindowList(ctrl)

    def UpdateControl(self, prop, ctrl):
        ctrl.SetValue(prop.GetDisplayedString())

    def DrawValue(self, dc, rect, prop, text):
        dc.DrawText(prop.GetDisplayedString(), rect.x + 5, rect.y)

    def OnEvent(self, propgrid, prop, ctrl, event):
        if not ctrl:
            return False

        evtType = event.GetEventType()

        if evtType == wx.wxEVT_COMMAND_TEXT_ENTER:
            if propgrid.IsEditorsValueModified():
                return True

        elif evtType == wx.wxEVT_COMMAND_TEXT_UPDATED:
            #
            # Pass this event outside wxPropertyGrid so that,
            # if necessary, program can tell when user is editing
            # a textctrl.
            event.Skip()
            event.SetId(propgrid.GetId())

            propgrid.EditorsValueWasModified()
            return False

        return False

    def GetValueFromControl(self, prop, ctrl):
        """ Return tuple (wasSuccess, newValue), where wasSuccess is True if
            different value was acquired successfully.
        """
        value = ctrl.GetValue()

        return True, value

    def SetControlStringValue(self, prop, ctrl, text):
        ctrl.SetValue(text)

    def OnFocus(self, prop, ctrl):
        ctrl.SetSelection(0, ctrl.GetLastPosition())

    def DeleteItem(self, ctrl, index: int) -> None:
        ctrl.DeleteItem(index)

    def InsertItem(self, ctrl, label: str, index: int) -> int:
        ctrl.InsertItem(label, index)
        return index


class BitmapComboboxProperty(wxpg.PGProperty):

    def __init__(self, label, name, value, choices):
        wxpg.PGProperty.__init__(self, label, name)

        self.m_value = value
        self.choices = choices

    def GetDisplayedString(self):
        return self.m_value

    def GetChoices(self):
        return self.choices

    def DeleteChoice(self, index: int) -> None:
        pass

    def AddChoice(self, label: str, value: int = wxpg.PG_INVALID_VALUE) -> int:
        if value == wxpg.PG_INVALID_VALUE:
            self.choices.append(label)
            return len(self.choices) - 1

        self.choices.insert(value, label)
        return value

    def SetChoices(self, choices):
        self.choices = choices

    def GetValue(self):
        return self.m_value

    def DoGetEditorClass(self):
        return wxpg.PropertyGridInterface.GetEditorByName("BitmapCombobox")
