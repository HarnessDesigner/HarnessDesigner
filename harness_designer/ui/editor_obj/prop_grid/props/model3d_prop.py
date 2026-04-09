import wx
import os

from . import prop_base as _prop_base
from ..... import utils as _utils


wxEVT_IMAGE_PATH_CHANGED = wx.NewEventType()
EVT_IMAGE_PATH_CHANGED = wx.PyEventBinder(wxEVT_IMAGE_PATH_CHANGED, 0)


class PathCtrl(wx.BoxSizer):

    def __init__(self, parent, path):
        self._path = path
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.path_ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(parent, wx.ID_ANY, '...')

        self.Add(self.path_ctrl, 0, wx.ALL, 5)
        self.Add(self.path_button, 0, wx.ALL, 5)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

    def Bind(self, *args, **kwargs):
        self.path_ctrl.Bind(*args, **kwargs)

    def Unbind(self, *args, **kwargs):
        self.path_ctrl.Unbind(*args, **kwargs)

    def on_open_file(self, _):
        value = self.path_ctrl.GetValue()

        if not value or value.startswith('http'):
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
            wildcard=_utils.MODEL_FILE_WILDCARDS, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path != self._path:
                self._path = path
                self._send_changed_event()

        dlg.Destroy()

    def _send_changed_event(self):
        event = wx.CommandEvent(wxEVT_IMAGE_PATH_CHANGED)
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


class Model3DProperty(_prop_base.Property):

    def __init__(self, label, name, value='', file_types={}, save_path=None):
        self._file_types = file_types
        self._save_path = save_path
        self._image_sizer: wx.BoxSizer = None

        _prop_base.Property.__init__(label, name, value, units=None)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')

        self._ctrl = PathCtrl(parent, self._value)
        self._ctrl.Bind(EVT_IMAGE_PATH_CHANGED, self._on_path_changed)

        self.Add(self._st, 0, wx.ALL, 5)
        self.Add(self._ctrl, 1, wx.ALL, 5)

    def _on_path_changed(self, _):
        path = self._ctrl.GetValue()
        if path == self._value:
            return

        self._value = path
        self._send_changed_event(str)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
