import wx

from . import ui


class App(wx.App):
    def OnInit(self):
        print('starting mainframe')
        frame = ui.MainFrame()
        print('showing main frame')
        frame.Show()
        return True

    def OnExit(self):
        from . import config

        config.Config.close()

        return wx.App.OnExit(self)


print('starting app')
app = App()

print('running main loop')
app.MainLoop()
