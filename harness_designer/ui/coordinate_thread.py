# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A worker thread that hands the status bar coordinates to the GUI thread.

The coordinates change on every mouse move, but writing them (three
``QLabel.setText`` calls) makes Qt re-lay-out the main window, so doing it on
every move held the 3D view down to ~45 fps. This thread keeps only the
NEWEST set it was given, runs the write on the GUI thread, and waits until
that has happened before it takes the next one.
"""

import threading
from typing import Any
from typing import Callable

from .. import check_types as _check_types


# How long the thread waits for the GUI thread to run a callback before it
# carries on anyway. A callback that never runs (the app is shutting down, or
# the main-thread dispatcher does not exist yet) must not hang the thread
# forever.
_CALLBACK_TIMEOUT = 1.0


class CoordinateThread(threading.Thread):
    """Runs the newest queued call on the GUI thread, one at a time.

    * :meth:`add` replaces whatever was waiting: only the newest call is ever
      kept, older ones are dropped unrun.
    * The thread sleeps while there is nothing queued (it never spins).
    * Each call is posted to the GUI thread with :func:`app.CallAfter` and the
      thread stalls until it has run, so there is never more than one call
      outstanding however fast :meth:`add` is called.
    * After each call it also waits ``min_interval`` seconds before taking
      the next. Without that the stall alone is not a limit: as soon as the
      GUI thread has run one call the next is posted, so the labels would be
      rewritten about once per event loop pass, the very per-mouse-move
      re-layout this thread exists to avoid.

    ``app.CallLater`` is not used for the hand-over: it is a
    ``QTimer.singleShot(0, ...)``, which only fires on a thread that has its
    own event loop, so called from here it would never run.
    """

    @_check_types.do
    def __init__(self, min_interval: float = 0.1):
        """
        :param min_interval: Least time, in seconds, between two calls.
        """
        super().__init__(name='CoordinateThread', daemon=True)

        self._min_interval = min_interval

        self._lock = threading.Lock()
        self._pending: tuple[Callable, tuple[Any, ...]] | None = None

        # set while a call is queued (or on stop) -- what the thread sleeps on
        self._wake = threading.Event()
        # set by the GUI thread once the posted call has run
        self._done = threading.Event()
        self._exit = threading.Event()

    @_check_types.do
    def add(self, func: Callable, *args: Any) -> None:
        """Queue ``func(*args)`` to run on the GUI thread, replacing any
        call still waiting. Safe to call from any thread."""
        with self._lock:
            self._pending = (func, args)

        self._wake.set()

    @_check_types.do
    def stop(self) -> None:
        """Ask the thread to end; it wakes at once wherever it is waiting."""
        self._exit.set()
        self._wake.set()
        self._done.set()

    @_check_types.do
    def run(self) -> None:
        # Deferred: app is still importing when this module is.
        from .. import app as _app

        while not self._exit.is_set():
            self._wake.wait()

            if self._exit.is_set():
                break

            # Taking the call and clearing the wake flag happen together
            # under the lock, so an add() landing right after sets it again
            # and is not lost.
            with self._lock:
                item = self._pending
                self._pending = None
                self._wake.clear()

            if item is None:
                continue

            func, args = item

            self._done.clear()
            _app.CallAfter(self._invoke, func, args)

            # Stall until the GUI thread has run it (or give up, see above).
            self._done.wait(_CALLBACK_TIMEOUT)

            # Do not free-wheel; also returns at once on stop().
            self._exit.wait(self._min_interval)

    @_check_types.do
    def _invoke(self, func: Callable, args: tuple[Any, ...]) -> None:
        """Runs on the GUI thread."""
        try:
            func(*args)
        except Exception as err:  # NOQA -- must not kill the GUI slot
            from .. import logger as _logger
            _logger.traceback(err, 'coordinate update error')
        finally:
            self._done.set()
