import wx
from wx.lib import scrolledpanel

from . import prop_base as _prop_base


class ArrayFloatDialog(wx.Dialog):

    def __init__(self, parent, values, title='Modify Array'):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(300, 500), style=wx.RESIZE_BORDER | wx.CLOSE_BOX | wx.STAY_ON_TOP | wx.CAPTION)

        self.add_item_button = wx.Button(self, wx.ID_ANY, label='+', size=(30, 30))
        self.remove_item_button = wx.Button(self, wx.ID_ANY, label='-', size=(30, 30))
        self.move_item_up_button = wx.Button(self, wx.ID_ANY, label='▲', size=(30, 30))
        self.move_item_down_button = wx.Button(self, wx.ID_ANY, label='▼', size=(30, 30))

        font = self.add_item_button.GetFont()
        font.SetPointSize(font.GetPointSize() + 4)
        self.add_item_button.SetFont(font)
        self.remove_item_button.SetFont(font)

        self.add_item_button.SetToolTip('Add Item')
        self.remove_item_button.SetToolTip('Remove Item')
        self.move_item_up_button.SetToolTip('Move Item Up')
        self.move_item_down_button.SetToolTip('Move Item Down')

        self.move_item_up_button.Enable(False)
        self.move_item_down_button.Enable(False)
        self.remove_item_button.Enable(False)

        self.add_item_button.Bind(wx.EVT_BUTTON, self._on_add_item)
        self.remove_item_button.Bind(wx.EVT_BUTTON, self._on_remove_item)
        self.move_item_up_button.Bind(wx.EVT_BUTTON, self._on_move_item_up)
        self.move_item_down_button.Bind(wx.EVT_BUTTON, self._on_move_item_down)

        self.item_panel = scrolledpanel.ScrolledPanel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.selected_item = None
        self._items = []

        self.item_sizer = wx.BoxSizer(wx.VERTICAL)

        for item in values:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            item = str(item)
            ctrl = wx.TextCtrl(self.item_panel, wx.ID_ANY, item, style=wx.TE_PROCESS_ENTER)
            ctrl.Bind(wx.EVT_SET_FOCUS, self._on_item_focus)
            ctrl.Bind(wx.EVT_CHAR_HOOK, self._on_item_char)
            ctrl.Bind(wx.EVT_KILL_FOCUS, self._on_item_kill_focus)

            self._items.append(ctrl)

            sizer.Add(ctrl, 1, wx.ALL, 5)
            self.item_sizer.Add(sizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.item_sizer, 1)
        self.item_panel.SetSizer(hsizer)
        self.item_panel.SetupScrolling()

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)

        button_sizer.Add(self.add_item_button, 0, wx.ALL, 2)
        button_sizer.Add(self.remove_item_button, 0, wx.ALL, 2)
        button_sizer.Add(self.move_item_up_button, 0, wx.ALL, 2)
        button_sizer.Add(self.move_item_down_button, 0, wx.ALL, 2)

        dialog_button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        line = wx.StaticLine(self, wx.ID_ANY, size=(-1, 1))

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer2 = wx.BoxSizer(wx.VERTICAL)
        vsizer2.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        vsizer2.Add(line, 0, wx.ALL | wx.EXPAND, 5)
        vsizer1.Add(vsizer2, 0, wx.ALL | wx.EXPAND, 5)
        vsizer1.Add(self.item_panel, 1, wx.EXPAND | wx.ALL, 5)
        vsizer1.Add(dialog_button_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vsizer1)

    def _on_move_item_up(self, _):
        index = self._items.index(self.selected_item)
        value1 = self.selected_item.GetValue()
        index -= 1
        value2 = self._items[index].GetValue()
        self.selected_item.ChangeValue(value2)
        self._items[index].ChangeValue(value1)
        self._items[index].SetFocus()

    def _on_move_item_down(self, _):
        index = self._items.index(self.selected_item)
        value1 = self.selected_item.GetValue()
        index += 1
        value2 = self._items[index].GetValue()
        self.selected_item.ChangeValue(value2)
        self._items[index].ChangeValue(value1)
        self._items[index].SetFocus()

    def _on_remove_item(self, _):
        index = self._items.index(self.selected_item)
        item = self._items.pop(index)
        item.Hide()
        self.item_sizer.Detach(item)
        item.Destroy()
        self.item_sizer.Layout()
        self.item_panel.Layout()
        self.Layout()
        self.item_panel.SetupScrolling()

    def _on_add_item(self, _):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        ctrl = wx.TextCtrl(self.item_panel, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER)
        ctrl.Bind(wx.EVT_SET_FOCUS, self._on_item_focus)
        ctrl.Bind(wx.EVT_CHAR_HOOK, self._on_item_char)
        ctrl.Bind(wx.EVT_KILL_FOCUS, self._on_item_kill_focus)

        self._items.append(ctrl)

        sizer.Add(ctrl, 1, wx.ALL, 5)
        self.item_sizer.Add(sizer, 1, wx.EXPAND)

        self.item_sizer.Layout()
        self.item_panel.Layout()
        self.Layout()
        self.item_panel.SetupScrolling()
        ctrl.SetFocus()

    @staticmethod
    def _on_item_char(evt):
        key = evt.GetKeyCode()

        if 32 <= key <= 126:
            if 48 <= key <= 57 or key in (45, 46):
                evt.Skip()
        else:
            evt.Skip()

    def _on_item_kill_focus(self, evt):
        in_focus = evt.GetWindow()
        if in_focus not in self._items and in_focus not in (
            self.add_item_button,
            self.remove_item_button,
            self.move_item_down_button,
            self.move_item_up_button
        ):
            self.move_item_up_button.Enable(False)
            self.move_item_down_button.Enable(False)
            self.remove_item_button.Enable(False)
            self.selected_item = None

        evt.Skip()

    def _on_item_focus(self, evt):
        evt.Skip()

        item = evt.GetEventObject()
        self.selected_item = item
        index = item.GetLastPosition()
        item.SetSelection(0, index)

        item_index = self._items.index(item)
        if item_index == 0:
            self.move_item_up_button.Enable(False)
            self.move_item_down_button.Enable(True)
        elif item_index == len(self._items) - 1:
            self.move_item_up_button.Enable(True)
            self.move_item_down_button.Enable(False)
        else:
            self.move_item_up_button.Enable(True)
            self.move_item_down_button.Enable(True)

        self.remove_item_button.Enable(True)

    def GetValue(self) -> list[float]:
        values = []
        for item in self._items:
            value = item.GetValue()
            if value == '':
                continue
            values.append(float(value))
        return values


class ArrayFloatProperty(_prop_base.Property):

    def __init__(self, parent, label):
        self._dialog_title = 'Enter Decimal Values'
        _prop_base.Property.__init__(self, parent, label)

        self._value = []

        self._st = wx.StaticText(self, wx.ID_ANY, label=self._label + ':')

        self._ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', style=wx.TE_LEFT | wx.TE_READONLY)
        self._button = wx.Button(self, wx.ID_ANY, label='...', size=(20, -1))

        self._button.Bind(wx.EVT_BUTTON, self._on_dialog_button)

    def GetValue(self) -> list[float]:
        return self._value

    def SetValue(self, value: list[float]):
        self._value = value
        value = ', '.join(str(item) for item in self._value)

        self._ctrl.ChangeValue(value)

    def Realize(self):
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.Add(self._ctrl, 1)
        hsizer2.Add(self._button, 0)

        vsizer.Add(hsizer2, 0, wx.ALL | wx.EXPAND, 5)
        hsizer1.Add(vsizer, 1)

        self._sizer.Add(hsizer1, 0, wx.EXPAND)

    def SetDialogTitle(self, value: str):
        self._dialog_title = value

    def _on_dialog_button(self, _):
        dlg = ArrayFloatDialog(self, self._value, self._dialog_title)
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.GetValue()
            if value == self._value:
                dlg.Destroy()
                return

            self._value = value
            value = ', '.join(str(item) for item in value)
            self._ctrl.ChangeValue(value)

            self._send_changed_event(list, self._value)

        dlg.Destroy()
