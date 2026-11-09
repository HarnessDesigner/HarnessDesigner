# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Union as _Union

import types
import threading
import weakref
import shiboken6
from PySide6 import QtGui, QtOpenGLWidgets

from .. import check_types as _check_types
from .. import logger as _logger


class _ThreadStack(threading.local):
    """Each thread gets its own empty stack (``__init__`` runs once per thread)."""

    def __init__(self):
        super().__init__()
        self.frames: list = []


class _Frame:
    """One ``with canvas.context:`` as the manager saw it on entry: whether it had to switch the thread's current GL context and,
    if it did, which context was current before (to be made current again on exit)."""

    def __init__(self, context: "GLContext", switched: bool, previous_qt: QtGui.QOpenGLContext | None,
                 previous: _Union["GLContext", None]):
        self.context = context
        self.switched = switched
        self.previous_qt = previous_qt
        self.previous = previous


class ContextManager:
    """
    The one place that knows which GL context is current on a thread, and puts the previous one back.

    OpenGL has one current context per thread, and ``makeCurrent()`` / ``doneCurrent()`` just replace it. A ``with
    canvas.context:`` that is entered while another context is current (the arena maintenance pass runs under the 3D
    editor's context, and can be entered from inside the peg board's ``paintGL``) used to end with ``doneCurrent()``, leaving
    NO context current for the rest of the caller, so every later GL call failed with ``GL_INVALID_OPERATION`` and Qt finished
    the paint without a context (access violation).

    Every ``GLContext`` enter and exit goes through here. An enter that has to switch contexts remembers the one that was
    current (a ``GLContext`` of a canvas, found through ``QOpenGLContext``, or any other context, such as an offscreen one); the
    matching exit makes it current again. If nothing was current before, the exit is a plain ``doneCurrent()``. An enter that
    finds its own context already current (inside that canvas's ``paintGL``) changes nothing and restores nothing.

    The stack is per thread, as the current context is.
    """

    def __init__(self):
        self._local = _ThreadStack()
        self._contexts: weakref.WeakSet = weakref.WeakSet()

    @_check_types.do
    def register(self, context: "GLContext") -> None:
        """Make a canvas's ``GLContext`` known, so a context that is current can be traced back to its canvas."""
        self._contexts.add(context)

    @property
    def _stack(self) -> list[_Frame]:
        return self._local.frames

    @property
    @_check_types.do
    def active(self) -> _Union["GLContext", None]:
        """The ``GLContext`` entered most recently on this thread and not yet exited (what the code running now asked for), or
        ``None``. It is what was asked for, not a promise that Qt has not made another context current since."""
        stack = self._stack

        if stack:
            return stack[-1].context

        return None

    @_check_types.do
    def _owner_of(self, qt_context: QtGui.QOpenGLContext) -> _Union["GLContext", None]:
        for context in list(self._contexts):
            if not shiboken6.isValid(context.canvas):
                continue

            if QtOpenGLWidgets.QOpenGLWidget.context(context.canvas) == qt_context:
                return context

        return None

    @_check_types.do
    def enter(self, context: "GLContext") -> None:
        """Make the canvas's context current if it is not, remembering what was current."""
        current = QtGui.QOpenGLContext.currentContext()
        widget_context = QtOpenGLWidgets.QOpenGLWidget.context(context.canvas)

        # current is None whenever nothing is current on this thread yet (e.g. a DB-callback cascade running before this canvas
        # has ever been shown/painted, so widget_context is also still None); None == None would read as "already current" and
        # skip makeCurrent() entirely. Only a real current context that is this widget's own counts as already current.
        # Checked on EVERY enter, not just the outermost: another GL widget's Qt-triggered repaint can make its own context
        # current while this one is held.
        if current is not None and current == widget_context:
            self._stack.append(_Frame(context, False, None, None))
            return

        previous = None
        if current is not None:
            previous = self._owner_of(current)

        context.canvas.makeCurrent()
        self._stack.append(_Frame(context, True, current, previous))

    @_check_types.do
    def exit(self, context: "GLContext") -> None:
        """End the matching ``enter``: put back the context that was current before it, or none if there was none."""
        stack = self._stack

        if not stack:
            _logger.error('GLContext exit with no matching enter')
            return

        frame = stack.pop()

        if frame.context is not context:
            _logger.error('GLContext exit does not match the enter on top of the stack')

        if not frame.switched:
            return

        self._restore(frame)

    @_check_types.do
    def _restore(self, frame: _Frame) -> None:
        previous_qt = frame.previous_qt

        if previous_qt is not None and shiboken6.isValid(previous_qt):
            previous = frame.previous

            if previous is not None and shiboken6.isValid(previous.canvas):
                # a canvas's own makeCurrent() also binds the widget's framebuffer, which a bare context switch would not
                previous.canvas.makeCurrent()
                return

            if previous is None:
                # a context that is not a canvas's (an offscreen one): back to it on its own surface
                previous_qt.makeCurrent(previous_qt.surface())
                return

        frame.context.canvas.doneCurrent()


CONTEXTS = ContextManager()


class GLContext:
    """
    Thread-safe OpenGL context manager for one canvas.

    wx: wrapped glcanvas.GLContext + canvas.SetCurrent(context).
    Qt:  QOpenGLWidget manages its own context internally; we call
         widget.makeCurrent() at enter time and, at exit, hand the thread back
         to whatever context was current before (``CONTEXTS``, the
         ``ContextManager`` above), or ``doneCurrent()`` if there was none.

    Re-entrant: the same thread may enter multiple times (e.g. a helper
    called from inside paintGL) without deadlocking.  Entering while this
    canvas's own context is already current (inside initializeGL/paintGL)
    switches nothing, so nothing is released or restored on exit.

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
    def __init__(self, canvas: "QtOpenGLWidgets.QOpenGLWidget"):
        """Initialise the :class:`GLContext` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`QOpenGLWidget`
        """
        self.canvas = canvas
        self._lock = threading.RLock()
        self.ref = 0

        CONTEXTS.register(self)

    @property
    @_check_types.do
    def is_locked(self) -> bool:
        """True while this context is entered (``with``) on any thread."""
        return self.ref != 0

    @_check_types.do
    def _acquire(self) -> None:
        """Internal: called only by __enter__. Not public -- see the
        class docstring for why acquire()/release() were removed."""
        self._lock.acquire()
        CONTEXTS.enter(self)
        self.ref += 1

    @_check_types.do
    def _release(self) -> None:
        """Internal: called only by __exit__. Not public -- see the
        class docstring for why acquire()/release() were removed."""
        self.ref -= 1
        CONTEXTS.exit(self)
        self._lock.release()

    @_check_types.do
    def __enter__(self) -> "GLContext":
        """Enter the managed context -- use as ``with ctx: ...``."""
        self._acquire()
        return self

    @_check_types.do
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: types.TracebackType | None) -> None:
        """Exit the managed context.

        Always runs -- exception or not -- which is the entire point;
        see the class docstring.
        """
        self._release()
