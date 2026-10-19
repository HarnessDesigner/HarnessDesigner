# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cooperative cancellation for a Job in flight, with a reason.

Generalizes harness_designer/claude/cancel.py's CancelToken one layer up (see
AI_PLUGIN_DESIGN.md "Threading and cancellation") so any AI plugin can use
the same mechanism without depending on the Claude-specific package. Plain
Python threads cannot be killed from outside, so this cooperative
check-then-raise pattern is the only mechanism -- a plugin with a real side
effect must checkpoint rather than assume a call will run to completion.
"""

from collections.abc import Callable

import threading

from ... import check_types as _check_types


REASON_CLOSE = 0
"""The Session itself is shutting down -- stop the thread, do not re-send."""

REASON_STEER = 1
""""Send now": discard the in-flight call and immediately re-send with the
new message folded in -- the Job keeps running, this is never reported to
it as an error."""


class Cancelled(Exception):
    """Raised by CancelToken.raise_if_cancelled(); carries why (a REASON_* value)."""

    @_check_types.do
    def __init__(self, reason: int) -> None:
        super().__init__('cancelled')
        self.reason = reason


class CancelToken:
    """Hand one to a call; call :meth:`cancel` from anywhere to stop it."""

    @_check_types.do
    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []
        self._reason: int | None = None

    @property
    @_check_types.do
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    @_check_types.do
    def reason(self) -> int | None:
        """``None`` until cancelled; one of the ``REASON_*`` values after."""
        return self._reason

    @_check_types.do
    def cancel(self, reason: int = REASON_CLOSE) -> None:
        with self._lock:
            if self._event.is_set():
                return

            self._reason = reason
            self._event.set()
            callbacks = list(self._callbacks)

        for callback in callbacks:
            callback()

    @_check_types.do
    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled(self._reason)

    @_check_types.do
    def wait(self, timeout: float) -> bool:
        """Wait up to *timeout* seconds; True when cancelled."""
        return self._event.wait(timeout)

    @_check_types.do
    def add_callback(self, callback: Callable[[], None]) -> None:
        """Run *callback* when cancelled (at once if already cancelled)."""
        with self._lock:
            already = self._event.is_set()
            if not already:
                self._callbacks.append(callback)

        if already:
            callback()

    @_check_types.do
    def remove_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
