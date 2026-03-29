
import wx

try:
    from . import autocomplete_combobox as _autocomplete_combobox
except ImportError:
    import autocomplete_combobox as _autocomplete_combobox


class ComboBoxCtrl(wx.BoxSizer):
    """
    Combo box control with autocomplete and a label

    Bind the EVT_COMBOBOX event to get updates.

    In order to enter a new item using the text ctrlpressing the enter key after
    entering the item will cause the EVT_COMBOBOX even to occur. Enter MUST be used
    when keying in an item that doesn't exist in the list of items.
    """

    def __init__(self, parent, label, choices):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = _autocomplete_combobox.AutoCompleteComboBox(
            parent, wx.ID_ANY, choices=choices, style=wx.CB_SORT | wx.TE_PROCESS_ENTER | wx.CB_DROPDOWN)

        self.ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

        hsizer.Add(self.st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        hsizer.Add(self.ctrl, 1, wx.ALL | wx.EXPAND, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.Add(vsizer, 1)

    def _on_enter(self, _):
        event = wx.CommandEvent(wx.wxEVT_COMBOBOX)
        event.SetString(self.ctrl.GetValue())
        event.SetEventObject(self.ctrl)
        event.SetId(self.ctrl.GetId())
        self.ctrl.GetEventHandler().ProcessEvent(event)

    def Enable(self, flag=True):
        self.ctrl.Enable(flag)
        self.st.Enable(flag)

    def SetToolTip(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def SetToolTipString(self, text):
        self.ctrl.SetToolTip(text)
        self.st.SetToolTip(text)

    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)

    def SetValue(self, value: str):
        items = self.ctrl.GetItems()
        if value in items:
            self.ctrl.SetStringSelection(value)
        else:
            self.ctrl.ChangeValue(value)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()

    def Clear(self):  # NOQA
        self.ctrl.Clear()

    def Delete(self, n: int):
        self.ctrl.Delete(n)

    def Insert(self, item: str, pos: int, clientData):  # NOQA
        self.ctrl.Insert(item, pos, clientData)

    def Set(self, items):
        self.ctrl.set(items)

    def GetItems(self) -> list[str]:
        return list(self.ctrl.GetItems())[:]

    def SetItems(self, items: list[str]):
        self.ctrl.SetItems(items)

    def AppendItems(self, items):
        self.ctrl.AppendItems(items)

    def Append(self, item):
        return self.ctrl.Append(item)


if __name__ == '__main__':
    app = wx.App()

    frame = wx.Frame(None, wx.ID_ANY, size=(600, 300))
    panel = wx.Panel(frame, wx.ID_ANY, style=wx.BORDER_NONE)
    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    hsizer.Add(panel, 1, wx.EXPAND)

    vsizer = wx.BoxSizer(wx.VERTICAL)
    vsizer.Add(hsizer, 1, wx.EXPAND)

    frame.SetSizer(vsizer)

    sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Static Box")
    sb = sz.GetStaticBox()

    ctrl = ComboBoxCtrl(sb, 'This is a test:', ['choice 1', 'choice 2'])

    sz.Add(ctrl, 1, wx.ALL, 5)

    sizer = wx.BoxSizer(wx.VERTICAL)

    sizer.Add(sz, 1, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(sizer)

    frame.Show()

    app.MainLoop()