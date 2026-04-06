
import wx
from wx import propgrid as wxpg
import os

from .... import utils as _utils


class ModelCtrl(wx.Panel):

    def __init__(self, parent, file_types, original_path, size, pos):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE, size=size, pos=pos)
        self.file_types = file_types

        self.original_path = original_path

        if original_path is None:
            original_path = ''

        self.new_value = original_path

        self.path_ctrl = wx.TextCtrl(self, wx.ID_ANY, value=original_path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(self, wx.ID_ANY, '...')

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.path_ctrl, 0, wx.ALL, 5)
        hsizer.Add(self.path_button, 0, wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

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
            self.path_ctrl.ChangeValue(path)
            self.new_value = path

        dlg.Destroy()

    def _on_enter(self, evt):
        value = self.path_ctrl.GetValue()
        self.new_value = value
        evt.Skip()

    def GetValue(self):
        return self.new_value

    def SetValue(self, value):
        self.new_value = value
        self.path_ctrl.SetValue(value)


class ModelEditor(wxpg.PGEditor):

    def __init__(self):
        self.property = None
        self.statbmp: wx.StaticBitmap = None
        self.tc: wx.TextCtrl = None
        self.bmp: wx.Bitmap = None
        wxpg.PGEditor.__init__(self)

    def CreateControls(self, propgrid, prop, pos, sz):
        w, h = sz
        h = 100 + 25

        original_path = prop.GetValue()
        file_types = prop.GetFileTypes()

        ctrl = ModelCtrl(propgrid.GetPanel(), file_types, original_path, (w, h), pos)

        return wxpg.PGWindowList(ctrl)

    def GetName(self):
        return self.__class__.__name__

    def UpdateControl(self, prop, ctrl):
        s = prop.GetDisplayedString()
        ctrl.SetValue(s)

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
        textVal = ctrl.GetValue()
        res, value = prop.StringToValue(textVal, wxpg.PG_EDITABLE_VALUE)

        # Changing unspecified always causes event (returning
        # True here should be enough to trigger it).
        if not res and value is None:
            res = True

        return res, value

    def SetControlStringValue(self, prop, ctrl, txt):
        ctrl.SetValue(txt)

    def CanContainCustomImage(self):
        return True


class ModelProperty(wxpg.PGProperty):

    def __init__(self, label, name, value, file_types):
        wxpg.PGProperty.__init__(self, label, name)

        self.m_value = value

        self._file_types = file_types

    def GetDisplayedString(self):
        return str(self.m_value)

    def GetFileTypes(self):
        return self._file_types

    def GetValue(self):
        return self.m_value

    def DoGetEditorClass(self):
        return wxpg.PropertyGridInterface.GetEditorByName("Model")
