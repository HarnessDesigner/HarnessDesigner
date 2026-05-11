# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget


class GLContext:
    """
    Thread-safe OpenGL context manager.

    wx: wrapped glcanvas.GLContext + canvas.SetCurrent(context).
    Qt:  QOpenGLWidget manages its own context internally; we just call
         widget.makeCurrent() / doneCurrent() at acquire/release time.

    The re-entrant reference-counting logic is identical to the original —
    only the two wx API calls change.
    """

    def __init__(self, canvas: "QOpenGLWidget"):
        self.canvas = canvas
        # Qt owns the actual GL context object; we don't create one.
        self._lock = threading.RLock()
        self._refs_lock = threading.Lock()
        self._refs: dict[threading.Thread, int] = {}
        self._refs_order: list[threading.Thread] = []

    @property
    def is_locked(self) -> bool:
        cur_thread = threading.current_thread()
        with self._refs_lock:
            if not self._refs_order:
                return False
            return self._refs_order[0] != cur_thread

    def acquire(self) -> None:
        cur_thread = threading.current_thread()

        with self._refs_lock:
            if cur_thread not in self._refs:
                self._refs[cur_thread] = 0
                self._refs_order.append(cur_thread)
            self._refs[cur_thread] += 1

        self._lock.acquire()
        # wx: canvas.SetCurrent(self.context)
        # Qt: makeCurrent() activates the widget's own context
        self.canvas.makeCurrent()

    def release(self) -> None:
        # wx: no explicit "done" call needed after SetCurrent
        # Qt: doneCurrent() is good practice; keeps context hygiene correct
        # when multiple widgets share a thread.
        self.canvas.doneCurrent()
        self._lock.release()

        cur_thread = threading.current_thread()
        with self._refs_lock:
            self._refs[cur_thread] -= 1
            if self._refs[cur_thread] == 0:
                del self._refs[cur_thread]
                self._refs_order.remove(cur_thread)

    def __enter__(self) -> "GLContext":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
