import wx

from . import ui


class App(wx.App):
    def OnInit(self):
        frame = ui.MainFrame()
        frame.Show()
        return True

    def OnExit(self):
        from . import config

        config.Config.close()

        return wx.App.OnExit(self)



app = App()
app.MainLoop()