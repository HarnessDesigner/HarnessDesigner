# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Run a Claude call on its own thread and hear about it on the GUI thread.

    job = ClaudeJob.ask(client, 'Which layer?')
    job.textDelta.connect(self.append_text)
    job.finished.connect(self.show_answer)
    job.failed.connect(lambda error: self.show_error(error.user_message))
    job.start()
    ...
    job.cancel()          # from a Stop button

Exactly one of ``finished``, ``failed`` and ``cancelled`` is emitted, once.
"""

from collections.abc import Callable
from typing import Any

import threading
import traceback

from PySide6 import QtCore

from . import gui_call as _gui_call
from .. import cancel as _cancel
from .. import client as _client
from .. import conversation as _conversation
from .. import errors as _errors
from .. import messages as _messages
from ..... import check_types as _check_types

# A job that is running must not be garbage collected under its own thread.
_running: set['ClaudeJob'] = set()
_running_lock = threading.Lock()

Work = Callable[[_cancel.CancelToken, _conversation.TextCallback, _conversation.ToolCallback], _messages.Response]


class ClaudeJob(QtCore.QObject):
    """
    :ivar textDelta: A piece of Claude's answer (``str``).
    :ivar toolCalled: A tool ran (name, arguments, result text, is_error).
    :ivar finished: Done (``Response``).
    :ivar failed: It failed (``ClaudeError``; show its ``user_message``).
    :ivar cancelled: :meth:`cancel` stopped it.
    """

    textDelta = QtCore.Signal(str)
    toolCalled = QtCore.Signal(str, object, str, bool)
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(object)
    cancelled = QtCore.Signal()

    @_check_types.do
    def __init__(self, work: Work, parent: QtCore.QObject | None = None):
        """Create jobs on the GUI thread. *work* receives the cancel token
        and the two progress callbacks and returns the Response."""
        super().__init__(parent)
        _gui_call.install()

        self._work = work
        self._token = _cancel.CancelToken()
        self._thread = threading.Thread(target=self._run, name='ClaudeJob', daemon=True)
        self._started = False

    @classmethod
    @_check_types.do
    def ask(cls, client: _client.ClaudeClient, prompt: str, parent: QtCore.QObject | None = None,
            **options: dict[str, Any]) -> 'ClaudeJob':
        """A job for ``client.ask(prompt, **options)``."""
        @_check_types.do
        def work(token: _cancel.CancelToken, on_text: _conversation.TextCallback,
                 on_tool: _conversation.ToolCallback) -> _messages.Response:
            return client.ask(prompt, on_text=on_text, on_tool=on_tool, cancel=token, **options)

        return cls(work, parent)

    @classmethod
    @_check_types.do
    def send(cls, conversation: _conversation.Conversation, content: str | list[dict[str, Any]],
             parent: QtCore.QObject | None = None) -> 'ClaudeJob':
        """A job for ``conversation.send(content)``."""
        @_check_types.do
        def work(token: _cancel.CancelToken, on_text: _conversation.TextCallback,
                 on_tool: _conversation.ToolCallback) -> _messages.Response:
            return conversation.send(content, on_text=on_text, on_tool=on_tool, cancel=token)

        return cls(work, parent)

    @property
    @_check_types.do
    def token(self) -> _cancel.CancelToken:
        """The job's cancel token (hand it to anything the job's tools wait on)."""
        return self._token

    @property
    @_check_types.do
    def is_running(self) -> bool:
        return self._started and self._thread.is_alive()

    @_check_types.do
    def start(self) -> None:
        if self._started:
            raise RuntimeError('a job can only be started once')

        self._started = True
        with _running_lock:
            _running.add(self)

        self._thread.start()

    @_check_types.do
    def cancel(self) -> None:
        """Stop the call; ``cancelled`` follows shortly."""
        self._token.cancel()

    @_check_types.do
    def _run(self) -> None:
        try:
            response = self._work(self._token, self.textDelta.emit, self._tool_called)
        except _errors.Cancelled:
            self._finish(self.cancelled.emit)
        except _errors.ClaudeError as err:
            # Cython can't compile `except ... as err` when a nested closure (the lambda
            # below) captures `err` directly: it needs to implicitly `del err` at the end
            # of the block but can't delete a name that's become a closure cell. Rebinding
            # to a plain local first keeps `err` itself out of the closure.
            caught = err
            self._finish(lambda: self.failed.emit(caught))
        except Exception as err:  # NOQA -- a bug must reach the user as a failure, not vanish with the thread
            wrapped = _errors.ClaudeError(f'Unexpected {type(err).__name__}: {err}',
                                          details=traceback.format_exc())
            self._finish(lambda: self.failed.emit(wrapped))
        else:
            self._finish(lambda: self.finished.emit(response))

    @_check_types.do
    def _tool_called(self, name: str, arguments: dict[str, Any], result: str, is_error: bool) -> None:
        self.toolCalled.emit(name, arguments, result, is_error)

    @_check_types.do
    def _finish(self, emit: Callable[[], None]) -> None:
        try:
            emit()
        finally:
            with _running_lock:
                _running.discard(self)
