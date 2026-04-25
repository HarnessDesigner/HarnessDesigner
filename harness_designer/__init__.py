from typing import TYPE_CHECKING

import wx
import sys
import time

import threading

from . import utils as _utils


if TYPE_CHECKING:
    from . import splash as _splash
    from . import logger as _logger
    from . import ui as _ui


splash: "_splash.Splash" = None
_mainframe: "_ui.MainFrame" = None


class App(wx.App):
    logger: "_logger.Log" = None

    def __init__(self, args):
        self._args = args
        self.splash = None
        self.frame = None
        wx.App.__init__(self)

    def OnInit(self):
        self.frame = wx.Frame(None, wx.ID_ANY)
        self.frame.Show(False)

        try:
            from .gl import info as _gl_info

            _gl_info.get(parent=self.frame)
        except Exception as err:  # NOQA
            from . import critical_error_dialog as _critical_error_dialog

            dlg = _critical_error_dialog.CriticalErrorDialog(self.frame, err)
            dlg.ShowModal()
            dlg.Destroy()
            self.frame.Destroy()
            return False

        try:
            from . import logger as _lggr
            self.logger = _lggr.Log()

        except Exception as err:  # NOQA
            from . import critical_error_dialog as _critical_error_dialog

            dlg = _critical_error_dialog.CriticalErrorDialog(self.frame, err)
            dlg.ShowModal()
            dlg.Destroy()
            self.frame.Destroy()
            return False

        global splash

        if _mainframe is None and self.frame is not None:
            try:
                from .splash import Splash

                self.splash = splash = Splash(self._args, self.logger)
                splash.Show()
            except Exception as err:  # NOQA
                from . import critical_error_dialog as _critical_error_dialog

                dlg = _critical_error_dialog.CriticalErrorDialog(self.frame, err)
                dlg.ShowModal()
                dlg.Destroy()

                self.frame.Destroy()
                return False

        return True

    def _thread_loop(self):
        global _mainframe
        self.splash.wait()

        event = threading.Event()
        error = [False]

        def _do():
            global _mainframe

            try:
                from .ui import mainframe
            except Exception as e:  # NOQA
                self.logger.traceback(e)

                from . import critical_error_dialog

                err_dlg = (
                    critical_error_dialog.CriticalErrorDialog(self.splash, e))

                err_dlg.ShowModal()
                err_dlg.Destroy()

                self.splash.Show(False)
                self.splash.Destroy()

                self.ExitMainLoop()
                error[0] = True
                event.set()
                return

            self.splash.SetText('Starting Mainframe')

            try:
                mainframe._mainframe = mainframe.MainFrame(
                    self.splash, self.logger
                )

            except Exception as e:  # NOQA
                self.logger.traceback(e)
                from . import critical_error_dialog

                err_dlg = (
                    critical_error_dialog.CriticalErrorDialog(self.splash, e))

                err_dlg.ShowModal()
                err_dlg.Destroy()

                self.splash.Show(False)
                self.splash.Destroy()
                self.ExitMainLoop()

                error[0] = True
                event.set()
                return

            _mainframe = mainframe._mainframe  # NOQA

            event.set()

        wx.CallAfter(_do)
        event.wait()

        if error[0]:
            return

        try:
            _mainframe.open_database(self.splash)  # NOQA
        except Exception as err:  # NOQA
            def _do(e):
                self.logger.traceback(e)
                from . import critical_error_dialog

                err_dlg = (
                    critical_error_dialog.CriticalErrorDialog(self.splash, e))
                err_dlg.ShowModal()
                err_dlg.Destroy()

                self.splash.Show(False)
                self.splash.Destroy()
                self.ExitMainLoop()

                event.set()
                return

            wx.CallAfter(_do, err)
            event.wait()
            return

        self.splash.SetText('DONE!')
        time.sleep(0.50)

        def _do():
            _mainframe.Show(True)  # NOQA
            self.splash.Show(False)
            self.splash.Destroy()
            event.set()

        wx.CallAfter(_do)
        event.wait()

    def OnEventLoopEnter(self, loop):
        if _mainframe is None and self.frame is not None:
            self.frame.Destroy()
            self.frame = None

            t = threading.Thread(target=self._thread_loop)
            t.daemon = True
            t.start()

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
    import multiprocessing

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):

        multiprocessing.freeze_support()

    multiprocessing.set_start_method('spawn')

    if args is None:
        args = sys.argv[1:]

    global _app

    _app = App(args)
    _app.MainLoop()
