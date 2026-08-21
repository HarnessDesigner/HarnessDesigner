# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Splash screen rendering used during application startup."""

from typing import TYPE_CHECKING

import os
import threading
from PIL import Image
from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from . import check_types as _check_types


if TYPE_CHECKING:
    from . import logger as _logger


class _SplashSignals(QtCore.QObject):
    """
    Signals must live on a QObject; we separate them so Splash stays clean.
    """

    refreshRequested: QtCore.SignalInstance = QtCore.Signal()


class Splash:
    """
    Borderless, always-on-top splash screen that displays a splash image with a
    status-text bar along the bottom.

    Public API is unchanged from the wx version:
        SetText(text, log=True)
        flush()
        wait()
        Destroy()
    """

    @_check_types.do
    def __init__(self, args, logger: "_logger.Log"):
        """
        Create and display the splash screen.

        :param args: Command-line arguments supplied to the application.
        :type args: list[str]
        :param logger: Logger used for startup status messages.
        :type logger: _logger.Log
        """

        self.logger = logger
        self.load_database = '--load-database' in args
        self.startup_args = args

        self._draw_lock = threading.Lock()
        self._init_event = threading.Event()

        # Status-strip progress bar. None means "plain text, no bar" --
        # see start_progress()/set_progress()/end_progress_bar().
        self._status_text = ''
        self._progress_max: int | None = None
        self._progress_value: int = 0

        # Load splash image via Pillow (same as wx version)
        base_path = os.path.dirname(__file__)

        img = Image.open(
            os.path.join(base_path, 'image/images/small_splash.png'))

        img = img.convert('RGBA')
        self._img_w, self._img_h = img.size

        # Convert PIL image → QPixmap
        raw = img.tobytes('raw', 'RGBA')

        qimage = QtGui.QImage(
            raw, self._img_w, self._img_h, QtGui.QImage.Format.Format_RGBA8888)

        self._splash_pixmap = QtGui.QPixmap.fromImage(qimage.copy())
        img.close()

        # The visible window area matches the original sizing
        self._size = (self._img_w - 65, self._img_h)

        # Build the composite render pixmap (splash + status bar)
        self._render_pixmap = QtGui.QPixmap(self._size[0], self._size[1])
        self._render_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        # Signals (cross-thread repaint)
        self._signals = _SplashSignals()

        # Build the actual Qt window — must happen on the main thread.
        # We create it immediately since __init__ is called from OnInit
        # (which is already on the main thread).
        self._window = QtWidgets.QLabel()
        self._window.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint |
                                    QtCore.Qt.WindowType.WindowStaysOnTopHint |
                                    QtCore.Qt.WindowType.SplashScreen |
                                    # keeps it off the taskbar
                                    QtCore.Qt.WindowType.Tool)

        self._window.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._window.setFixedSize(self._size[0], self._size[1])

        # Connect refresh signal so worker threads can trigger a repaint
        self._signals.refreshRequested.connect(self._do_refresh)

        # Draw initial frame
        self.draw('Loading...')
        self._window.setPixmap(self._render_pixmap)

        self._position_window()

        self._window.show()
        QtWidgets.QApplication.processEvents()

        # splash is visible; background thread may proceed
        self._init_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @_check_types.do
    def wait(self):
        """
        Block until the splash window is visible.
        """

        self._init_event.wait()

    @_check_types.do
    def Show(self, show=True):
        """
        Show or hide the splash window.

        :param show: ``True`` to show the splash, ``False`` to hide it.
        :type show: bool
        """

        if show:
            self._window.show()
        else:
            self._window.hide()

    @_check_types.do
    def Destroy(self):
        """
        Close and delete the splash window.
        """

        QtWidgets.QApplication.restoreOverrideCursor()

        @_check_types.do
        def _do():
            with self._draw_lock:
                self._window.close()
                self._window.deleteLater()

        if threading.main_thread() == threading.current_thread():
            _do()
        else:
            self._signals.refreshRequested.connect(lambda: _do())
            self._signals.refreshRequested.emit()

    @_check_types.do
    def SetText(self, text: str, log=True) -> None:
        """
        Update the status text shown on the splash screen.

        :param text: Status text to draw.
        :type text: str
        :param log: Log the message through the application logger.
        :type log: bool
        """

        if log:
            self.logger.info(text)

        self._status_text = text
        self.draw(text)

        if threading.main_thread() != threading.current_thread():
            event = threading.Event()

            @_check_types.do
            def _on_refresh():
                self._signals.refreshRequested.disconnect(_on_refresh)
                event.set()

            self._signals.refreshRequested.connect(_on_refresh)
            self._signals.refreshRequested.emit()
            event.wait()
        else:
            self._do_refresh()

    @_check_types.do
    def flush(self):  # NOQA
        """
        Process pending Qt events for the splash screen.
        """

        QtWidgets.QApplication.processEvents()

    @_check_types.do
    def start_progress(self, label: str, max_value: int) -> None:
        """
        Switch the status strip into progress-bar mode, filling it
        left-to-right as :meth:`set_progress` advances -- mirrors
        MainFrame's own start_progress/set_progress/end_progress_bar
        status-bar API.

        :param label: Status text to show while the bar fills.
        :type label: str
        :param max_value: Number of steps the bar represents.
        :type max_value: int
        """

        self._progress_max = max_value
        self._progress_value = 0
        self.SetText(label)

    @_check_types.do
    def set_progress(self, value: int, label: str | None = None) -> None:
        """
        Advance the progress bar started by :meth:`start_progress`.

        :param value: Current step, ``0..max_value``.
        :type value: int
        :param label: Replacement status text; keeps the current text
            if omitted.
        :type label: str | None
        """

        self._progress_value = value

        if label is None:
            label = self._status_text

        self.SetText(label, log=False)

    @_check_types.do
    def end_progress_bar(self) -> None:
        """
        Return the status strip to plain text mode.
        """

        self._progress_max = None

    # ------------------------------------------------------------------
    # Internal positioning
    # ------------------------------------------------------------------

    @_check_types.do
    def _position_window(self) -> None:
        """
        Center the splash over where the mainframe window is about to
        open (``Config.mainframe.position``/``size``), rather than always
        the primary display -- otherwise, once the splash stays up past
        the mainframe's own show() (see ui/mainframe.py's
        ``_open_project``), a splash centered on a different monitor than
        the mainframe reads as broken.

        Falls back to centering on the primary display outright when
        ``position``/``size`` aren't set yet (first-ever launch -- the
        mainframe's own default-geometry logic, in MainFrame.__init__,
        hasn't run yet the first time this is called). The remaining
        multi-monitor safety (falling back to whichever display holds the
        most of the mainframe's own remembered rectangle when the exact
        remembered position is no longer fully on-screen) is shared with
        every other borderless window that centers itself the same way --
        see ``utils/window_geometry.py``'s ``safe_center``.
        """

        from . import config as _config
        from . import utils as _utils

        mf_config = _config.Config.mainframe
        position = mf_config.position
        size = mf_config.size

        screens = QtWidgets.QApplication.screens()
        primary = QtWidgets.QApplication.primaryScreen()

        if position is None or size is None or not screens:
            center = primary.availableGeometry().center()
        else:
            mf_rect = QtCore.QRect(
                int(position[0]), int(position[1]), int(size[0]), int(size[1]))

            center = _utils.safe_center(mf_rect, self._size)

        self._window.move(center - self._window.rect().center())

    # ------------------------------------------------------------------
    # Internal drawing
    # ------------------------------------------------------------------

    @_check_types.do
    def draw(self, text: str):
        """
        Render the splash image and current status text into a pixmap.

        :param text: Status text to draw.
        :type text: str
        """

        with self._draw_lock:
            w, h = self._size
            bmp_height = self._img_h - 40
            bar_height = h - bmp_height

            pixmap = QtGui.QPixmap(w, h)
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            # Draw the splash image (offset -30, -20 as in wx version)
            painter.drawPixmap(-30, -20, self._splash_pixmap)

            # Draw the status bar background
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 255)))
            painter.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
            painter.drawRect(0, bmp_height, w, bar_height)

            # Progress fill -- drawn on top of the bar background, behind
            # the status text, so the strip itself doubles as the bar
            # (start_progress()/set_progress()/end_progress_bar() toggle
            # this on/off via self._progress_max).
            if self._progress_max:
                fraction = self._progress_value / self._progress_max
                fraction = min(1.0, max(0.0, fraction))
                fill_width = int(w * fraction)

                painter.setBrush(QtGui.QBrush(QtGui.QColor(70, 130, 200, 255)))
                painter.drawRect(0, bmp_height, fill_width, bar_height)

            # Draw status text centred in the bar
            painter.setPen(QtGui.QColor(190, 190, 190, 255))
            font = QtGui.QFont()
            font.setPointSize(9)
            painter.setFont(font)

            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            tx = (w - tw) // 2
            ty = bmp_height + (bar_height - th) // 2 + fm.ascent() - 5

            painter.drawText(tx, ty, text)
            painter.end()

            self._render_pixmap = pixmap

    @_check_types.do
    def _do_refresh(self):
        """
        Must be called on the main thread.
        """

        with self._draw_lock:
            self._window.setPixmap(self._render_pixmap)
            self._window.repaint()

        QtWidgets.QApplication.processEvents()
