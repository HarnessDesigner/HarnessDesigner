# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import time
import threading

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QObject


_call_on_main = None


def CallAfter(func, *args) -> None:
    _call_on_main.emit(lambda f=func, a=args: f(*a))  # NOQA


class _AppSignals(QObject):
    """Cross-thread signals for the App startup sequence."""
    call_on_main = Signal(object)   # payload: a zero-arg callable


class App(QObject):

    def __init__(self, args):
        global _call_on_main

        QObject.__init__(self)  # must call this

        self._args = args
        self.splash = None
        self.frame = None
        self.logger = None

        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self._signals = _AppSignals()
        self._signals.call_on_main.connect(self._dispatch)

        _call_on_main = self._signals.call_on_main

    # ------------------------------------------------------------------
    # Qt signal dispatch — runs on main thread
    # ------------------------------------------------------------------

    def _dispatch(self, fn):  # NOQA
        fn()

    def call_after(self, fn):
        """Schedule fn() to run on the Qt main thread (like wx.CallAfter)."""
        self._signals.call_on_main.emit(fn)

    # ------------------------------------------------------------------
    # Startup sequence  (replaces OnInit + OnEventLoopEnter + _thread_loop)
    # ------------------------------------------------------------------

    def _init(self):
        """Runs on the main thread before the event loop starts."""

        import harness_designer as _hd

        # Query GL capabilities using a temporary offscreen surface
        try:
            from .gl import info as _gl_info
            _gl_info.get()
        except Exception as err:
            from . import critical_error_dialog as _ced
            dlg = _ced.CriticalErrorDialog(None, err)
            dlg.exec()
            return False

        # Set up logger
        try:
            from . import logger as _lggr
            self.logger = _lggr.Log()
        except Exception as err:
            from . import critical_error_dialog as _ced
            dlg = _ced.CriticalErrorDialog(None, err)
            dlg.exec()
            return False

        # Show splash
        try:
            from .splash import Splash
            self.splash = _hd.splash = Splash(self._args, self.logger)
        except Exception as err:
            from . import critical_error_dialog as _ced
            dlg = _ced.CriticalErrorDialog(None, err)
            dlg.exec()
            return False

        # Kick off the background loading thread once the event loop is running
        self._start_loading_thread()
        return True

    def _start_loading_thread(self):
        t = threading.Thread(target=self._thread_loop, daemon=True)
        t.start()

    def _thread_loop(self):
        """Runs on the background thread — mirrors the original _thread_loop."""
        import harness_designer as _hd
        self.splash.wait()

        event = threading.Event()
        error = [False]

        # ---- import mainframe on main thread ----
        def _import_mainframe():
            try:
                from .ui import mainframe
            except Exception as e:
                self.logger.traceback(e)
                from . import critical_error_dialog
                err_dlg = critical_error_dialog.CriticalErrorDialog(None, e)
                err_dlg.exec()
                self.splash.Show(False)
                self.splash.Destroy()
                self._qt_app.quit()
                error[0] = True
                event.set()
                return

            self.splash.SetText('Starting Mainframe')

            try:
                mainframe._mainframe = mainframe.MainFrame(
                    self.splash, self.logger
                )
            except Exception as e:
                self.logger.traceback(e)
                from . import critical_error_dialog
                err_dlg = critical_error_dialog.CriticalErrorDialog(None, e)
                err_dlg.exec()
                self.splash.Show(False)
                self.splash.Destroy()
                self._qt_app.quit()
                error[0] = True
                event.set()
                return

            _hd._mainframe = mainframe._mainframe  # NOQA
            event.set()

        self.call_after(_import_mainframe)
        event.wait()

        if error[0]:
            return

        # ---- open database ----
        try:
            _hd._mainframe.open_database(self.splash)  # NOQA
        except Exception as err:
            def _do(e=err):
                self.logger.traceback(e)
                from . import critical_error_dialog
                err_dlg = critical_error_dialog.CriticalErrorDialog(None, e)
                err_dlg.exec()
                self.splash.Show(False)
                self.splash.Destroy()
                self._qt_app.quit()
                event.set()

            self.call_after(_do)
            event.wait()
            return

        # ---- show main window, hide splash ----
        self.splash.SetText('DONE!')
        time.sleep(0.50)

        def _do():
            _hd._mainframe.show()  # NOQA

        self.call_after(_do)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def MainLoop(self):
        if not self._init():
            return

        result = self._qt_app.exec()
        sys.exit(result)

    def OnExit(self):
        """Called automatically by MainLoop when the event loop ends."""
        from . import config

        if self.logger:
            self.logger.info('Saving Config Data...')
        config.Config.close()

        if self.logger:
            self.logger.info('Exiting Application...')
            self.logger.log_handler.close()
            self.logger = None
