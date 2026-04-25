import wx

from ..widgets import combobox_ctrl as _combobox_ctrl
from . import dialog_base as _dialog_base


class OpenProjectDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, last_project, project_names):
        _dialog_base.BaseDialog.__init__(self, parent, 'Open Project', size=(600, 200))
        self.last_project = last_project
        self.project_names = project_names

        self.project_ctrl = _combobox_ctrl.ComboBoxCtrl(
            self.panel, 'Project:', project_names, True)

        if last_project is not None and last_project in project_names:
            self.project_ctrl.SetValue(last_project)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.project_ctrl, 1, wx.LEFT | wx.RIGHT, 100)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(h_sizer, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 10)

        b_sizer = self.button_sizer.GetItem(1).GetSizer()

        for child in b_sizer.GetChildren():
            child = child.GetWindow()
            if isinstance(child, wx.Button) and child.GetLabel() == 'OK':
                child.SetLabel('Open')
                break

        self.panel.SetSizer(sizer)
        self.CenterOnParent()

    def GetValue(self):
        return self.project_ctrl.GetValue()
