import wx

from . import ui


class App(wx.App):
    def OnInit(self):
        frame = ui.MainFrame()
        frame.Show()
        return True


app = App()
app.MainLoop()