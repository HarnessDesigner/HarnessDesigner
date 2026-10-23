# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Let code running on a worker thread ask the GUI thread to do something
and wait for the answer.

The reason this exists: a tool Claude calls runs on the worker thread (the
GUI thread must never wait on the network), but a tool that needs to ask the
user a question -- "which wire goes in the centre?" -- has to show a dialog,
and dialogs belong to the GUI thread. The tool handler calls
:func:`call_in_gui` with a function that shows the dialog and returns the
answer; the worker thread waits, the GUI thread stays live.
"""

from collections.abc import Callable
from typing import Any

import threading

from PySide6 import QtCore

from .. import cancel as _cancel
from .. import errors as _errors
from ..... import check_types as _check_types

# How often a waiting worker looks at its cancel token.
_POLL_SECONDS = 0.05


class _Call:
    @_check_types.do
    def __init__(self, function: Callable[[], Any]):
        self.function = function
        self.done = threading.Event()
        self.result: Any = None
        self.error: BaseException | None = None

    @_check_types.do
    def execute(self) -> None:
        try:
            self.result = self.function()
        except BaseException as error:  # NOQA -- handed back to the waiting thread, which re-raises it
            self.error = error
        finally:
            self.done.set()


class _Invoker(QtCore.QObject):
    """Lives on the GUI thread; signals sent to it from other threads are
    queued and run there."""

    requested = QtCore.Signal(object)

    @_check_types.do
    def __init__(self):
        super().__init__()
        self.requested.connect(self._execute)

    @QtCore.Slot(object)
    @_check_types.do
    def _execute(self, call: _Call) -> None:
        call.execute()


_invoker: _Invoker | None = None


@_check_types.do
def install() -> None:
    """Prepare :func:`call_in_gui`. Must run once on the GUI thread; a
    :class:`~harness_designer.claude.qt.ClaudeJob` does it when created."""
    global _invoker

    application = QtCore.QCoreApplication.instance()
    if application is None:
        raise RuntimeError('there is no QApplication')

    if QtCore.QThread.currentThread() is not application.thread():
        raise RuntimeError('install() must be called on the GUI thread')

    if _invoker is None:
        _invoker = _Invoker()


@_check_types.do
def call_in_gui(function: Callable[[], Any], cancel: _cancel.CancelToken | None = None) -> Any:
    """Run *function* on the GUI thread and return what it returns.

    Called from the GUI thread itself it simply runs the function. Called
    from a worker it blocks that worker (never the GUI) until the function
    has finished; an exception in the function is raised here.

    :param cancel: Stops the wait with ``Cancelled`` if the call is
        cancelled meanwhile (the function itself is not interrupted: a
        dialog already on screen stays until the user closes it).
    """
    application = QtCore.QCoreApplication.instance()
    if application is not None and QtCore.QThread.currentThread() is application.thread():
        return function()

    if _invoker is None:
        raise RuntimeError('call_in_gui needs install() to have run on the GUI thread first')

    call = _Call(function)
    _invoker.requested.emit(call)

    while not call.done.wait(_POLL_SECONDS):
        if cancel is not None and cancel.is_cancelled:
            raise _errors.Cancelled()

    if call.error is not None:
        raise call.error

    return call.result
