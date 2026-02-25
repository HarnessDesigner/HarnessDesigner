import wx


class OpenProjectDialog(wx.FileDialog):
    def __init__(self, parent, last_directory):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title="Create/Open Save File", style=wx.FD_OPEN | wx.FD_SHOW_HIDDEN)

        self.SetWildcard("Harness Maker files (.hrn)|.hrn")
        self.SetDirectory(last_directory)
        self.CenterOnParent()
