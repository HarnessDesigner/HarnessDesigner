import wx

from . import prop_base as _prop_base


class EnumProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)
        self._choices = []
        self._value = 0
        self._labels = []

        self._ctrl: wx.RadioBox = None
        self._vsizer = wx.BoxSizer(wx.VERTICAL)

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._vsizer, 1)
        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def _on_change(self, evt):
        index = evt.GetInt()
        value = self._choices[index]

        if value == self._value:
            return

        self._value = value
        self._send_changed_event(int, value)

    def SetValue(self, value: int):
        index = self._choices.index(value)
        self._ctrl.SetSelection(index)
        self._value = value

    def GetValue(self) -> str:
        return self._value

    def Enable(self, flag=True):
        if self._ctrl is not None:
            self._ctrl.Enable(flag)

    def SetLabels(self, labels):
        self._labels = labels

        ctrl = wx.RadioBox(
            self, wx.ID_ANY, label=self.GetLabel(),
            choices=labels, majorDimension=3, style=wx.RA_SPECIFY_COLS)

        if self._ctrl is None:
            self._vsizer.Add(ctrl, 0, wx.ALL | wx.EXPAND, 5)
        else:
            self._vsizer.Replace(self._ctrl, ctrl)
            self._ctrl.Show(False)
            self._ctrl.Destroy()

        self._ctrl = ctrl

        self._ctrl.Bind(wx.EVT_RADIOBOX, self._on_change)

        last_parent = self
        parent = self.GetParent()

        while parent is not None and not isinstance(parent, wx.Notebook):
            last_parent = parent
            parent = parent.GetParent()

        last_parent.Layout()
        last_parent.SendSizeEvent()

    def GetLabels(self) -> list[str]:
        return self._labels

    def GetItems(self) -> list[int]:
        return self._choices

    def SetItems(self, items: list[int]):
        self._choices = items
