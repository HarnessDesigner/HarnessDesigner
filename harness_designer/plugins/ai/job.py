# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Job -- one instruction handed to an AI Session. See AI_PLUGIN_DESIGN.md.

Created and subclassed by the app's call site (the assistant panel, the
bundle organizer) -- never by a plugin. A plugin reads whatever request data
a Job subclass carries and calls back into it; it never knows what the
overridden methods actually do with the result. Request-data shape is
deliberately NOT defined here (see AI_PLUGIN_DESIGN.md "Open questions") --
a concrete Job subclass carries whatever its own call site needs (an
instruction, tools, context) as its own attributes.
"""

from typing import Any
from collections.abc import Callable

from ... import app as _app
from ... import check_types as _check_types


class Job:
    """Base class a call site subclasses to hand the AI something to do.

    ``on_progress``/``on_usage`` may be called any number of times while the
    Job runs. Exactly one of ``on_complete``/``on_error`` is called once,
    terminal. None of these run on the GUI thread -- a subclass that needs to
    touch a widget uses :meth:`call_after`, never anything else.
    """

    @_check_types.do
    def __init__(self, *, name: str = '') -> None:
        self.name = name

    @_check_types.do
    def call_after(self, fn: Callable, *args: tuple[Any]) -> None:
        """Run ``fn(*args)`` on the GUI thread; forwards to ``app.CallAfter``."""
        _app.CallAfter(fn, *args)

    @_check_types.do
    def on_progress(self, current: int | float, total: int | float) -> None:
        """Called zero or more times while the Job runs. No-op by default."""

    @_check_types.do
    def on_usage(self, tokens_used: int, tokens_limit: int | None) -> None:
        """Called zero or more times while the Job runs. No-op by default."""

    @_check_types.do
    def on_complete(self, result: Any) -> None:
        raise NotImplementedError

    @_check_types.do
    def on_error(self, error: Exception) -> None:
        raise NotImplementedError
