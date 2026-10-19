# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A way to stop a call that is in flight, from another thread."""

from collections.abc import Callable

import threading

from . import errors as _errors
from .... import check_types as _check_types


class CancelToken:
    """Hand one to a call; call :meth:`cancel` from anywhere to stop it.

    Cancelling also runs the callbacks registered by the call (it registers
    one that closes its network connection), so a call blocked waiting for
    the next piece of the answer stops promptly instead of at the next
    piece.
    """

    @_check_types.do
    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []

    @property
    @_check_types.do
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @_check_types.do
    def cancel(self) -> None:
        with self._lock:
            if self._event.is_set():
                return

            self._event.set()
            callbacks = list(self._callbacks)

        for callback in callbacks:
            callback()

    @_check_types.do
    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise _errors.Cancelled()

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
