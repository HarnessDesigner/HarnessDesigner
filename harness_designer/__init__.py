from typing import TYPE_CHECKING

import wx
from . import utils as _utils


if TYPE_CHECKING:
    from .ui import splash as _splash
    from . import logger as _logger

splash: "_splash.Splash" = None


class App(wx.App):
    logger: "_logger.Log" = None

    def OnInit(self):
        global splash

        from .ui import splash as _splsh
        from . import logger as _lggr

        self.logger = _lggr.Log()
        splash = _splsh.Splash(None, self.logger)

        splash.Show()
        return True

    def OnExit(self):
        from . import config

        print('Saving Config Data...')
        config.Config.close()

        print('Exiting Application...')

        self.logger.log_handler.close()
        self.logger = None
        return wx.App.OnExit(self)


_app = None


def __main__():
    global _app
    _app = App()
    _app.MainLoop()
