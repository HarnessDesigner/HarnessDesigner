import wx

from . import prop_base as _prop_base


class LongStringDialog(wx.Dialog):

    def __init__(self, parent, value: str, title: str = 'Enter Text'):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(300, 200), style=wx.RESIZE_BORDER | wx.CLOSE_BOX | wx.STAY_ON_TOP | wx.CAPTION)

        self.ctrl = wx.TextCtrl(self, wx.ID_ANY, value=value, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER | wx.HSCROLL | wx.TE_MULTILINE)
        button_szier = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.ctrl, 1, wx.EXPAND | wx.ALL, 10)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        vsizer.Add(button_szier, 0, wx.EXPAND | wx.ALL, 10)

        self.ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self.SetSizer(vsizer)

    def _on_enter(self, _):
        index = self.ctrl.GetInsertionPoint()
        start_text = self.ctrl.GetRange(0, index)
        all_text = self.ctrl.GetValue()
        all_text = all_text.replace(start_text, '')
        all_text = f'{start_text}\n{all_text}'
        self.ctrl.ChangeValue(all_text)
        self.ctrl.SetInsertionPoint(index + 1)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()


class LongStringProperty(_prop_base.Property):

    def __init__(self, label, name='', value='', style=0, units=None):
        self._style = style
        self._dialog_title = 'Enter Text'

        _prop_base.Property.__init__(self, label, name, value, units)

    def SetDialogTitle(self, value: str):
        self._dialog_title = value

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        if self._ctrl is not None:
            self._ctrl.ChangeValue(value)
            self._value = value

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)

        parent = self._parent_window

        style = self._style | wx.TE_LEFT | wx.TE_READONLY

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')
        self._ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=self._value, style=style)
        self._button = wx.Button(parent, wx.ID_ANY, label='...', size=(20, -1))

        self.Add(self._st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._ctrl, 1)
        hsizer.Add(self._button, 0)

        vsizer.Add(hsizer, 0, wx.ALL | wx.EXPAND, 5)
        self.Add(vsizer, 1)

        if self._units is not None:
            self._units_st = wx.StaticText(parent, wx.ID_ANY, label=self._units)
            self.Add(self._units_st, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        self._button.Bind(wx.EVT_BUTTON, self._on_dialog_button)

        def _do():
            h = self._ctrl.GetSize()[-1]
            self._button.SetSize((h, h))

        wx.CallAfter(_do)

    def _on_dialog_button(self, _):
        dlg = LongStringDialog(self._parent_window, self._value, self._dialog_title)
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.GetValue()
            if value == self._value:
                dlg.Destroy()
                return

            self._ctrl.ChangeValue(self._value)
            self._send_changed_event(str)

        dlg.Destroy()
