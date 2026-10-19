# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Session -- one open-ended AI activity. See AI_PLUGIN_DESIGN.md.

Created by an AIBase plugin (AIBase.create_session), never directly. Named
from its first Job's instruction (mechanism not yet built). Closed when the
user closes the AI dialog that owns it -- never when a Job completes; the
user can hand the same Session another, related Job right after.
"""

from collections.abc import Callable

import queue
import threading

from . import cancel as _cancel
from ... import check_types as _check_types


class Session:
    """Holds history and runs Jobs one at a time, on its own thread."""

    @_check_types.do
    def __init__(self, *, name: str = '') -> None:
        self.name = name
        self._queue: queue.Queue = queue.Queue()
        self._cancel_token: _cancel.CancelToken | None = None
        self._pending_steer: str | None = None
        self._lock = threading.Lock()
        self._closed = False
        self._thread: threading.Thread | None = None

    @property
    @_check_types.do
    def is_closed(self) -> bool:
        return self._closed

    @_check_types.do
    def current_cancel_token(self) -> _cancel.CancelToken:
        """A fresh token for the call about to start; replaces the last one."""
        with self._lock:
            token = _cancel.CancelToken()
            self._cancel_token = token
            return token

    @_check_types.do
    def steer(self, message: str) -> None:
        """"Send now": fold *message* into the Job currently running.

        Cancels whatever call is in flight (reason=STEER) and stashes
        *message* for the plugin's run loop to pick up (see
        :meth:`take_steer_message`) and re-send with -- the Job keeps
        running, nothing is reported to it as an error.
        """
        with self._lock:
            self._pending_steer = message
            token = self._cancel_token

        if token is not None:
            token.cancel(_cancel.REASON_STEER)

    @_check_types.do
    def take_steer_message(self) -> str | None:
        """Consume and clear whatever :meth:`steer` last stashed, if any."""
        with self._lock:
            message = self._pending_steer
            self._pending_steer = None
            return message

    @_check_types.do
    def close(self) -> None:
        """The user closed the AI dialog -- stop the current call and the thread."""
        with self._lock:
            if self._closed:
                return

            self._closed = True
            token = self._cancel_token

        if token is not None:
            token.cancel(_cancel.REASON_CLOSE)

        self._put(None)

    @_check_types.do
    def _start(self, loop: Callable) -> None:
        """Start the session's own worker thread. Called once, by AIBase."""
        thread = threading.Thread(target=loop, args=(self,), daemon=True)
        self._thread = thread
        thread.start()

    @_check_types.do
    def _put(self, item: object) -> None:
        self._queue.put(item)

    @_check_types.do
    def _get(self) -> object:
        return self._queue.get()
