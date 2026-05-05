import wx

# wx.PD_REMAINING_TIME
# wx.PD_ESTIMATED_TIME
# wx.PD_ELAPSED_TIME
# wx.PD_CAN_SKIP
# wx.PD_CAN_ABORT
# wx.PD_AUTO_HIDE
# wx.PD_APP_MODAL


class ProjectLoadDialog(wx.ProgressDialog):

    def __init__(self, parent):
        wx.ProgressDialog.__init__(self, 'Project Loading...', '', parent=parent, style=wx.PD_SMOOTH)
        self.CenterOnParent()

    def Update(self, value, newmsg=''):
        max_val = self.GetRange()

        msg = f'{newmsg}     {value}[{max_val}]'
        wx.ProgressDialog.Update(self, value, msg)
