# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Qt application bootstrap helpers for :mod:`harness_designer`."""

import sys
import time
import threading
import traceback as _traceback

from . import logger

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QObject, QTimer

from PySide6.QtCore import Qt
from . import check_types as _check_types

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

_call_on_main = None


@_check_types.do
def _qt_message_handler(msg_type, context, message):
    """Log every Qt-native qDebug/qWarning/qCritical/qFatal message.

    Installed via qInstallMessageHandler in App._init -- see that call
    site for why this exists (Qt's own C++-side diagnostics, like a
    cross-thread OpenGL makeCurrent() failure, never raise a catchable
    Python exception, so this is the only way to ever see one logged).

    :param msg_type: The Qt message severity (QtDebugMsg/QtInfoMsg/
        QtWarningMsg/QtCriticalMsg/QtFatalMsg).
    :param context: QMessageLogContext -- may have empty file/line/
        function fields depending on build config.
    :param message: The message text.
    """
    from PySide6.QtCore import QtMsgType

    thread_name = threading.current_thread().name
    location = f'{context.file}:{context.line}' if context.file else ''
    text = f'[Qt] {message} (thread={thread_name}){" " + location if location else ""}'

    # The handler runs synchronously on whatever thread actually triggered
    # the Qt-side qWarning/qCritical call (a Python->C++ call in practice,
    # e.g. QOpenGLWidget.makeCurrent()) -- format_stack() here captures
    # that SAME thread's real Python call chain at this exact moment, the
    # one piece of information a bare Qt message never carries on its own.
    stack = ''.join(_traceback.format_stack())
    text += f'\nPython call stack (thread={thread_name}) at time of message:\n{stack}'

    if msg_type in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        logger.error(text)
    else:
        logger.warning(text)


@_check_types.do
def CallLater(func, *args) -> None:
    """Schedule a callable to execute after the current event handler returns.

    Unlike :func:`CallAfter`, this always defers ``func`` until the event loop
    regains control, even when called from the main thread.

    :param func: Callable to invoke.
    :type func: collections.abc.Callable
    :param args: Positional arguments passed to ``func``.
    :type args: tuple
    """
    QTimer.singleShot(0, lambda f=func, a=args: f(*a))


@_check_types.do
def CallAfter(func, *args) -> None:
    """Schedule a callable to execute on the Qt main thread.

    A no-op before :class:`App` is constructed (e.g. the package gets
    imported for its side effects - stdout/stderr redirection starts as
    soon as ``logger`` is imported - without ever building an ``App``,
    such as a CI build importing the package to compile extensions).
    There's no main thread to dispatch to yet, so there's nothing to do.

    :param func: Callable to invoke later.
    :type func: collections.abc.Callable
    :param args: Positional arguments passed to ``func``.
    :type args: tuple
    """
    if _call_on_main is None:
        return

    _call_on_main.emit(lambda f=func, a=args: f(*a))  # NOQA


_after_start_cbs = []


@_check_types.do
def CallAfterStart(func, *args) -> None:
    _after_start_cbs.append((func, args))


class _AppSignals(QObject):
    """Cross-thread signals for the App startup sequence."""
    call_on_main = Signal(object)   # payload: a zero-arg callable


class App(QObject):
    """Own the Qt application object and startup workflow.

    This class coordinates splash creation, background loading, and shutdown
    handling for :mod:`harness_designer`.
    """

    @_check_types.do
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

    @_check_types.do
    def setStyleSheet(self, style_sheet):
        self._qt_app.setStyleSheet(style_sheet)

    # ------------------------------------------------------------------
    # Qt signal dispatch — runs on main thread
    # ------------------------------------------------------------------

    @_check_types.do
    def _dispatch(self, fn):  # NOQA
        """Execute a zero-argument callable on the main thread.

        :param fn: Callable emitted through :class:`_AppSignals`.
        :type fn: collections.abc.Callable
        """
        fn()

    @_check_types.do
    def call_after(self, fn):
        """Schedule fn() to run on the Qt main thread (like wx.CallAfter)."""
        self._signals.call_on_main.emit(fn)

    # ------------------------------------------------------------------
    # Startup sequence  (replaces OnInit + OnEventLoopEnter + _thread_loop)
    # ------------------------------------------------------------------

    @_check_types.do
    def _init(self):
        """Runs on the main thread before the event loop starts."""

        import harness_designer as _hd

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
        self.logger = logger
        logger.startup()

        # Capture Qt's own native warnings/errors (e.g. "Cannot make
        # QOpenGLContext current in a different thread") into the log --
        # these come from Qt's C++ side (qWarning/qCritical), not a raised
        # Python exception, so no try/except anywhere in Python code would
        # ever catch one. Logging the thread name lets an intermittent,
        # timing-dependent GL-threading issue actually be tracked down
        # from a real occurrence instead of guessed at.
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(_qt_message_handler)

        from . import config as _config
        from . import themes as _themes

        _themes.load_theme(_config.Config.mainframe.theme)

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

    @_check_types.do
    def _start_loading_thread(self):
        """Start the background worker that finishes application startup."""
        t = threading.Thread(target=self._thread_loop, daemon=True)
        t.start()

    @_check_types.do
    def _thread_loop(self):
        """Runs on the background thread — mirrors the original _thread_loop."""
        import harness_designer as _hd
        self.splash.wait()

        event = threading.Event()
        error = [False]

        # ---- import mainframe on main thread ----
        @_check_types.do
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
            @_check_types.do
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

        @_check_types.do
        def _do():
            """Show the main frame after startup completes.

            """

            _hd._mainframe.show()  # NOQA

        self.call_after(_do)

        @_check_types.do
        def _do():
            for func, args in _after_start_cbs:
                func(*args)

        self.call_after(_do)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @_check_types.do
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

    @_check_types.do
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
