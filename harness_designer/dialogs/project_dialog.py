import wx

from ....gui_controls import auto_complete


class OpenProjectDialog(wx.Dialog):

    def __init__(self, parent, recent_projects, project_names):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='Open Project', style=wx.CAPTION | wx.STAY_ON_TOP)
        self.recent_projects = recent_projects
        self.project_names = project_names

        if recent_projects:
            value = recent_projects[0]
        else:
            value = wx.EmptyString

        self.project_ctrl = auto_complete.AutoComplete(self, wx.ID_ANY, value=value, autocomplete_choices=project_names, size=(200, -1))
        project_label = wx.StaticText(self, wx.ID_ANY, label='Project:')

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(project_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM, 20)
        h_sizer.Add(self.project_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM | wx.LEFT, 20)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(h_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT | wx.TOP, 40)
        sizer.AddStretchSpacer(1)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        b_sizer = button_sizer.GetItem(1).GetSizer()

        for child in b_sizer.GetChildren():
            child = child.GetWindow()
            if isinstance(child, wx.Button) and child.GetLabel() == 'OK':
                child.SetLabel('Open')
                break

        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)
        self.CenterOnParent()

    def GetValue(self):
        return self.project_ctrl.GetValue()
