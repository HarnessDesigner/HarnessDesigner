
import wx
import os

from . import prop_base as _prop_base


wxEVT_IMAGE_PATH_CHANGED = wx.NewEventType()
EVT_IMAGE_PATH_CHANGED = wx.PyEventBinder(wxEVT_IMAGE_PATH_CHANGED, 0)


class PathEvent(wx.CommandEvent):

    def __init__(self, evt_type):
        wx.CommandEvent.__init__(self, evt_type)
        self._value = None

    def SetValue(self, value):
        self._value = value

    def GetValue(self):
        return self._value


class PathCtrl(wx.BoxSizer):

    def __init__(self, parent, path):
        self._path = path
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.path_ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(parent, wx.ID_ANY, '...')
        self.wildcards = ''

        self.Add(self.path_ctrl, 0, wx.ALL, 5)
        self.Add(self.path_button, 0, wx.ALL, 5)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self.path_ctrl.Bind(wx.EVT_CHAR, self.on_path_char)

    def SetWildcards(self, value):
        self.wildcards = value

    def on_path_char(self, evt):
        def _do():
            value = self.path_ctrl.GetValue()

            self.path_button.Enable(not value.startswith('http'))

        wx.CallAfter(_do)
        evt.Skip()

    def GetValue(self) -> str:
        return self._path

    def SetValue(self, value: str):
        self._path = value
        self.path_ctrl.ChangeValue(value)
        self.path_button.Enable(not value.startswith('http'))

    def Bind(self, *args, **kwargs):
        self.path_ctrl.Bind(*args, **kwargs)

    def Unbind(self, *args, **kwargs):
        self.path_ctrl.Unbind(*args, **kwargs)

    def on_open_file(self, _):
        value = self.path_ctrl.GetValue()

        if not value:
            default_dir = os.path.expandvars('~')
            default_file = ''
        else:
            default_dir, default_file = os.path.split(value)

            if not os.path.exists(value):
                default_file = ''

                if not os.path.exists(default_dir):
                    default_dir = os.path.expandvars('~')

        dlg = wx.FileDialog(
            self, '', defaultDir=default_dir, defaultFile=default_file,
            wildcard=self.wildcards, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path != self._path:
                self._path = path
                self._send_changed_event()

        dlg.Destroy()

    def _send_changed_event(self):
        event = PathEvent(wxEVT_IMAGE_PATH_CHANGED)
        event.SetValue(self._path)
        event.SetId(self.path_ctrl.GetId())
        event.SetEventObject(self.path_ctrl)
        self.path_ctrl.GetEventHandler().ProcessEvent(event)

    def _on_enter(self, _):
        path = self.path_ctrl.GetValue()
        if path == self._path:
            return

        self._path = path
        self._send_changed_event()


class PathProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)

        self._value = ''
        self._st = wx.StaticText(self, wx.ID_ANY, label=label + ':')
        self._ctrl = PathCtrl(self, '')
        self._ctrl.Bind(EVT_IMAGE_PATH_CHANGED, self._on_path_changed)

    def Realize(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self._st, 0, wx.ALL, 5)
        hsizer.Add(self._ctrl, 1, wx.ALL, 5)

        self._sizer.Add(hsizer, 0, wx.EXPAND)

    def _on_path_changed(self, _):
        path = self._ctrl.GetValue()
        if path == self._value:
            return

        self._value = path
        self._send_changed_event(str, path)

    def SetWildcards(self, value):
        self._ctrl.SetWildcards(value)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.SetValue(value)
