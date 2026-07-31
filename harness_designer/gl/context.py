# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading
from typing import TYPE_CHECKING

from PySide6.QtGui import QOpenGLContext
from PySide6 import QtOpenGLWidgets
from .. import check_types as _check_types

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

    ``with ctx:`` ONLY -- there is no public acquire()/release(). An
    unhandled exception between a manual acquire() and its release() call
    silently leaks the ref count upward forever (Qt's own slot/callback
    dispatch swallows an uncaught Python exception instead of propagating
    it, so the code never even reaches the release() line) -- every
    later acquire() on that same instance then trusts a ref>0 it should
    no longer trust, eventually surfacing as a "context has not been
    acquired" crash at some unrelated, hard-to-reproduce later moment.
    ``with`` closes this at the source: __exit__ always runs, exception
    or not, so the ref count can never desync from reality. Confirmed
    2026-07-29 as the actual root cause of exactly that crash.
    """

    @_check_types.do
    def __init__(self, canvas: "QOpenGLWidget"):
        """Initialise the :class:`GLContext` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`QOpenGLWidget`
        """
        self.canvas = canvas
        self._lock = threading.RLock()
        self.ref = 0
        self._made_current = False  # Track if WE made the context current

    @property
    @_check_types.do
    def is_locked(self) -> bool:
        """Return the is locked.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self.ref != 0

    @_check_types.do
    def _acquire(self):
        """Internal: called only by __enter__. Not public -- see the
        class docstring for why acquire()/release() were removed."""
        self._lock.acquire()

        # Checked on EVERY acquire, not just the ref==0 -> 1 transition:
        # another GL widget's own Qt-triggered repaint can call
        # makeCurrent() on ITS context at any point while this one is
        # nested-held (ref > 0), silently stealing thread-current-ness out
        # from under us without touching our own refcount. Trusting a
        # stale "we're ref>0 so we must still be current" assumption here
        # is exactly what produced a real "context has not been acquired"
        # crash despite the caller already being inside a matching
        # acquire()/release() pair. Re-verifying and re-establishing
        # current-ness on every call closes that hole; only the ref==0
        # transition's own _made_current bookkeeping changes, so a nested
        # acquire re-establishing current-ness here never takes over
        # responsibility for the eventual doneCurrent() from whichever
        # call actually owns it.
        current_ctx = QOpenGLContext.currentContext()
        widget_ctx = QtOpenGLWidgets.QOpenGLWidget.context(self.canvas)

        if current_ctx != widget_ctx:
            self.canvas.makeCurrent()
            if self.ref == 0:
                self._made_current = True
        elif self.ref == 0:
            # Context already current (e.g., inside initializeGL/paintGL)
            self._made_current = False

        self.ref += 1

    @_check_types.do
    def _release(self):
        """Internal: called only by __exit__. Not public -- see the
        class docstring for why acquire()/release() were removed."""
        self.ref -= 1
        if self.ref == 0:
            # Only call doneCurrent if WE made it current
            if self._made_current:
                self.canvas.doneCurrent()
                self._made_current = False

        self._lock.release()

    @_check_types.do
    def __enter__(self) -> "GLContext":
        """Enter the managed context -- use as ``with ctx: ...``."""
        self._acquire()
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the managed context.

        Always runs -- exception or not -- which is the entire point;
        see the class docstring.
        """
        self._release()

