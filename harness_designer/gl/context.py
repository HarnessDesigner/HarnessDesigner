# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading
from typing import TYPE_CHECKING

from PySide6.QtGui import QOpenGLContext

if TYPE_CHECKING:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget


class GLContext:
    """
    Thread-safe OpenGL context manager.

    wx: wrapped glcanvas.GLContext + canvas.SetCurrent(context).
    Qt:  QOpenGLWidget manages its own context internally; we call
         widget.makeCurrent() / doneCurrent() at acquire/release time.

    Re-entrant: the same thread may acquire multiple times (e.g. a helper
    called from inside paintGL) without deadlocking.  The context is only
    released — and doneCurrent() only called — when the outermost caller
    exits.

    Now safe to use inside initializeGL/resizeGL/paintGL - will detect
    if context is already current and avoid redundant makeCurrent() calls.
    """

    def __init__(self, canvas: "QOpenGLWidget"):
        self.canvas = canvas
        self._lock = threading.RLock()
        self.ref = 0
        self._made_current = False  # Track if WE made the context current

    @property
    def is_locked(self) -> bool:
        return self.ref != 0

    def acquire(self):
        self._lock.acquire()
        if self.ref == 0:
            # Check if context is already current
            current_ctx = QOpenGLContext.currentContext()
            widget_ctx = self.canvas.context()
            
            if current_ctx != widget_ctx:
                # Only call makeCurrent if context is not already current
                self.canvas.makeCurrent()
                self._made_current = True
            else:
                # Context already current (e.g., inside initializeGL/paintGL)
                self._made_current = False
        self.ref += 1

    def release(self):
        self.ref -= 1
        if self.ref == 0:
            # Only call doneCurrent if WE made it current
            if self._made_current:
                self.canvas.doneCurrent()
                self._made_current = False
        self._lock.release()

    def __enter__(self) -> "GLContext":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
