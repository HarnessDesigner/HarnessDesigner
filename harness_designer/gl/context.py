# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading
from typing import TYPE_CHECKING


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

    IMPORTANT: Do NOT use this inside initializeGL / resizeGL / paintGL.
    Qt guarantees the context is already current when it calls those three
    methods.  Only use GLContext for GL work done *outside* those callbacks
    (e.g. take_snapshot, set_focal_target, background-thread uploads).
    """

    def __init__(self, canvas: "QOpenGLWidget"):
        self.canvas = canvas
        self._lock = threading.RLock()
        self.ref = 0

    @property
    def is_locked(self) -> bool:
        return self.ref != 0

    def acquire(self):
        self._lock.acquire()
        if self.ref == 0:
            # Make context current on first acquire
            self.canvas.makeCurrent()
        self.ref += 1

    def release(self):
        self.ref -= 1
        if self.ref == 0:
            # Release context on last release
            self.canvas.doneCurrent()
        self._lock.release()

    def __enter__(self) -> "GLContext":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
