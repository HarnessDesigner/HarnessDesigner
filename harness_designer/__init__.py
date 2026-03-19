from typing import TYPE_CHECKING

import wx
import sys

from . import utils as _utils


if TYPE_CHECKING:
    from . import splash as _splash
    from . import logger as _logger

splash: "_splash.Splash" = None


class App(wx.App):
    logger: "_logger.Log" = None

    def __init__(self, args):
        self._args = args
        wx.App.__init__(self)

    def OnInit(self):
        global splash

        try:
            from .splash import Splash

            splash = Splash(self._args)

            splash.Show()
        except Exception as err:  # NOQA
            from . import critical_error_dialog as _critical_error_dialog

            frame = wx.Frame(None, wx.ID_ANY)
            frame.Show(False)

            dlg = _critical_error_dialog.CriticalErrorDialog(frame, err)
            dlg.ShowModal()
            dlg.Destroy()
            frame.Destroy()
            return False

        try:
            from .gl import info as _gl_info

            _gl_info.get(parent=splash)
        except Exception as err:  # NOQA
            from . import critical_error_dialog as _critical_error_dialog

            dlg = _critical_error_dialog.CriticalErrorDialog(splash, err)
            dlg.ShowModal()
            dlg.Destroy()
            splash.Destroy()
            return False

        try:
            from . import logger as _lggr

            self.logger = _lggr.Log()

            splash.set_logger(self.logger)
        except Exception as err:  # NOQA
            from . import critical_error_dialog as _critical_error_dialog

            dlg = _critical_error_dialog.CriticalErrorDialog(splash, err)
            dlg.ShowModal()
            dlg.Destroy()
            splash.Destroy()
            return False

        return True

    def OnExit(self):
        from . import config

        self.logger.info('Saving Config Data...')
        config.Config.close()

        self.logger.info('Exiting Application...')

        self.logger.log_handler.close()
        self.logger = None
        return wx.App.OnExit(self)


_app = None


def __main__(args=None):
    if args is None:
        args = sys.argv[1:]

    global _app

    _app = App(args)
    _app.MainLoop()
