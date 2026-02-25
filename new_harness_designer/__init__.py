from typing import TYPE_CHECKING

import wx
import os
from . import utils as _utils


if TYPE_CHECKING:
    from .ui import splash as _splash

splash: "_splash.Splash" = None


class App(wx.App):
    def OnInit(self):
        global splash

        from .ui import splash as _splsh

        splash = _splsh.Splash(None)
        splash.Show()
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