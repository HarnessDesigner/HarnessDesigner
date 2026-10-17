# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Run a function off the GUI thread and get its result back on it."""

from collections.abc import Callable

import threading
import traceback

from PySide6 import QtCore

from ... import check_types as _check_types


class BackgroundJob(QtCore.QObject):
    """One function run on its own thread.

    ``finished`` carries the return value, ``failed`` the formatted
    traceback; exactly one of them is emitted, always back on the thread
    this object lives in (Qt queues the signal across threads).

    Keep a reference to the job until one of the signals arrives: a job
    collected while its thread is still running would crash.
    """

    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, work: Callable[[], object], parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._work = work
        self._thread = threading.Thread(target=self._run, daemon=True)

    @_check_types.do
    def start(self) -> None:
        self._thread.start()

    @_check_types.do
    def _run(self) -> None:
        # An exception must not vanish with the thread: it goes to `failed`
        # so whoever started the job can show or log it.
        try:
            result = self._work()
        except Exception:  # NOQA -- reported through the failed signal
            self.failed.emit(traceback.format_exc())
        else:
            self.finished.emit(result)
