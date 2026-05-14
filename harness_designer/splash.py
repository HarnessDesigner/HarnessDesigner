# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import threading
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QBrush, QPen
from PySide6.QtCore import Qt, QTimer, Signal, QObject


if TYPE_CHECKING:
    from . import logger as _logger


class _SplashSignals(QObject):
    """Signals must live on a QObject; we separate them so Splash stays clean."""
    refresh_requested = Signal()


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

    def __init__(self, args, logger: "_logger.Log"):
        self.logger = logger
        self.load_database = '--load-database' in args
        self.startup_args = args

        self._draw_lock = threading.Lock()
        self._init_event = threading.Event()

        # Load splash image via Pillow (same as wx version)
        base_path = os.path.dirname(__file__)
        img = Image.open(os.path.join(base_path, 'image/small_splash.png'))
        img = img.convert('RGBA')
        self._img_w, self._img_h = img.size

        # Convert PIL image → QPixmap
        from PySide6.QtGui import QImage
        raw = img.tobytes('raw', 'RGBA')
        qimage = QImage(raw, self._img_w, self._img_h, QImage.Format_RGBA8888)
        self._splash_pixmap = QPixmap.fromImage(qimage.copy())
        img.close()

        # The visible window area matches the original sizing
        self._size = (self._img_w - 65, self._img_h)

        # Build the composite render pixmap (splash + status bar)
        self._render_pixmap = QPixmap(self._size[0], self._size[1])
        self._render_pixmap.fill(Qt.transparent)

        # Signals (cross-thread repaint)
        self._signals = _SplashSignals()

        # Build the actual Qt window — must happen on the main thread.
        # We create it immediately since __init__ is called from OnInit
        # (which is already on the main thread).
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import QPoint

        self._window = QLabel()
        self._window.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen |
            Qt.Tool                  # keeps it off the taskbar
        )
        self._window.setAttribute(Qt.WA_TranslucentBackground)
        self._window.setFixedSize(self._size[0], self._size[1])

        # Connect refresh signal so worker threads can trigger a repaint
        self._signals.refresh_requested.connect(self._do_refresh)

        # Draw initial frame
        self.draw('Loading...')
        self._window.setPixmap(self._render_pixmap)
        self._window.move(
            (QApplication.primaryScreen().availableGeometry().center() -
             self._window.rect().center())
        )
        self._window.show()
        QApplication.processEvents()

        self._init_event.set()   # splash is visible; background thread may proceed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait(self):
        """Block until the splash window is visible."""
        self._init_event.wait()

    def Show(self, show=True):
        if show:
            self._window.show()
        else:
            self._window.hide()

    def Destroy(self):
        """Close and delete the splash window.  Mirrors wx.Frame.Destroy()."""
        QApplication.restoreOverrideCursor()

        def _do():
            with self._draw_lock:
                self._window.close()
                self._window.deleteLater()

        if threading.main_thread() == threading.current_thread():
            _do()
        else:
            self._signals.refresh_requested.connect(lambda: _do())
            self._signals.refresh_requested.emit()

    def SetText(self, text: str, log=True) -> None:
        if log:
            self.logger.info(text)

        self.draw(text)

        if threading.main_thread() != threading.current_thread():
            event = threading.Event()

            def _on_refresh():
                self._signals.refresh_requested.disconnect(_on_refresh)
                event.set()

            self._signals.refresh_requested.connect(_on_refresh)
            self._signals.refresh_requested.emit()
            event.wait()
        else:
            self._do_refresh()

    def flush(self):
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Internal drawing
    # ------------------------------------------------------------------

    def draw(self, text: str):
        with self._draw_lock:
            w, h = self._size
            bmp_height = self._img_h - 40
            bar_height = h - bmp_height

            pixmap = QPixmap(w, h)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw the splash image (offset -30, -20 as in wx version)
            painter.drawPixmap(-30, -20, self._splash_pixmap)

            # Draw the status bar background
            painter.setBrush(QBrush(QColor(0, 0, 0, 255)))
            painter.setPen(QPen(Qt.NoPen))
            painter.drawRect(0, bmp_height, w, bar_height)

            # Draw status text centred in the bar
            painter.setPen(QColor(190, 190, 190, 255))
            font = QFont()
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

    def _do_refresh(self):
        """Must be called on the main thread."""
        with self._draw_lock:
            self._window.setPixmap(self._render_pixmap)
            self._window.repaint()
        QApplication.processEvents()
