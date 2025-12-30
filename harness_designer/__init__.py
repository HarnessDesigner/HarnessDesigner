import wx

from .ui import splash as _splash


splash: _splash.Splash = None


class App(wx.App):
    def OnInit(self):
        global splash

        print('starting splash')
        splash = _splash.Splash(None)
        splash.Show()
        print('splash shown')
        return True

    def OnExit(self):
        from . import config

        config.Config.close()

        return wx.App.OnExit(self)


_app = None


def __main__():
    global _app
    _app = App()
    _app.MainLoop()
