# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Qt application bootstrap helpers for :mod:`harness_designer`."""

import sys
import time
import threading

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QObject

from PySide6.QtCore import Qt

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

_call_on_main = None


def CallAfter(func, *args) -> None:
    """Schedule a callable to execute on the Qt main thread.

    :param func: Callable to invoke later.
    :type func: collections.abc.Callable
    :param args: Positional arguments passed to ``func``.
    :type args: tuple
    """
    _call_on_main.emit(lambda f=func, a=args: f(*a))  # NOQA


class _AppSignals(QObject):
    """Cross-thread signals for the App startup sequence."""
    call_on_main = Signal(object)   # payload: a zero-arg callable


class App(QObject):
    """Own the Qt application object and startup workflow.

    This class coordinates splash creation, background loading, and shutdown
    handling for :mod:`harness_designer`.
    """

    def __init__(self, args):
        """Initialise application state and cross-thread signals.

        :param args: Command-line arguments passed to the application.
        :type args: list[str]
        """
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

    def setStyleSheet(self, style_sheet):
        self._qt_app.setStyleSheet(style_sheet)

    # ------------------------------------------------------------------
    # Qt signal dispatch — runs on main thread
    # ------------------------------------------------------------------

    def _dispatch(self, fn):  # NOQA
        """Execute a zero-argument callable on the main thread.

        :param fn: Callable emitted through :class:`_AppSignals`.
        :type fn: collections.abc.Callable
        """
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
        from . import themes as _themes
        from . import config as _config

        _themes.load_theme(_config.Config.mainframe.theme)

        # Set default QSurfaceFormat for shared OpenGL contexts
        # This MUST be called before ANY OpenGL context is created (including GL info query)
        from PySide6.QtGui import QSurfaceFormat
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        # 4x MSAA — QOpenGLWidget renders into a multisampled FBO and
        # resolves it automatically. Framebuffer readbacks must go through
        # grabFramebuffer() (resolved), not raw glReadPixels.
        fmt.setSamples(4)
        # fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setVersion(3, 3)
        # fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

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
        """Start the background worker that finishes application startup.

        """
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
            """Import and construct the main frame on the UI thread.

            """
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
                """Report a database-open failure on the main thread.

                :param e: Exception raised while opening the database.
                :type e: Exception
                """
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
            """Show the main frame after startup completes.

            """
            _hd._mainframe.show()  # NOQA

        self.call_after(_do)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def MainLoop(self):
        """Initialise the application and run the Qt event loop.

        :returns: This method does not normally return because it exits the
            process via :func:`sys.exit`.
        :rtype: None
        """
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
