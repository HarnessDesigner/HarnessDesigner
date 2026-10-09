# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Debug logging helpers and decorators for :mod:`harness_designer`.

Timing workflow:

1. Set ``Config.debug.functions.log_duration`` and restart, so :func:`logfunc`
   decorates the functions. Leave ``log_args`` off for timing runs: formatting
   arguments is work the timer would otherwise measure.
2. Call :func:`begin_capture`.
3. Run the drag, rotate, load, or flush.
4. Call :func:`end_capture`. It prints a depth-indented call tree and a
   per-function summary, and returns the same text.

Nothing is printed while a capture runs, so logging never lands inside a timed
region. Each call records its inclusive time (the whole call) and its self time
(inclusive minus the time of its decorated children). The summary is sorted by
self time, which is where time is actually spent. A recursive function's
inclusive time counts once per level, so use the self columns for totals.
"""

from typing import TYPE_CHECKING, Any
from collections.abc import Callable

import threading
import time
import sys
import functools
import inspect

from . import config as _config
from . import check_types as _check_types


if TYPE_CHECKING:
    from . import logger as _logger


Config = _config.Config.debug.functions


class DebugPrinter:
    """Route debug output either to stdout or the application logger."""

    @_check_types.do
    def __init__(self) -> None:
        """Initialise the fallback debug printer.

        """

        @_check_types.do
        def log_printer(*args: tuple[Any]) -> None:
            """Print debug output until a logger becomes available.

            :param args: Positional values to print.
            :type args: tuple
            """
            from .ui import mainframe

            if mainframe._mainframe is not None:  # NOQA
                self.set_logger(mainframe._mainframe.logger)  # NOQA

            print(*args)

        self._logger = log_printer
        self._flush = sys.stdout.flush

    @_check_types.do
    def set_logger(self, logger: "_logger.Log") -> None:
        """Send future debug output to the application logger.

        :param logger: Logger instance that exposes ``debug`` and ``log_handler``.
        :type logger: _logger.Log
        """
        self._logger = logger.debug
        self._flush = logger.log_handler.flush

    @_check_types.do
    def __call__(self, *args: tuple[Any], end_stack: bool = False) -> None:
        """Emit debug output.

        :param args: Message parts forwarded to the current sink.
        :type args: tuple
        :param end_stack: Flush after logging when ending a stack trace block.
        :type end_stack: bool
        """
        self._logger(*args)

        if end_stack:
            self._flush()


_print_func = DebugPrinter()


class _Record:
    """One decorated call during a capture."""

    __slots__ = ('qualname', 'depth', 'label', 'duration', 'self_time')

    def __init__(self, qualname: str, depth: int, label: str) -> None:
        self.qualname = qualname
        self.depth = depth
        self.label = label
        self.duration: int = 0
        self.self_time: int = 0


class _ThreadState(threading.local):
    """Per-thread stack of child-time accumulators, one entry per open call."""

    def __init__(self) -> None:
        self.stack: list[int] = []


_state = _ThreadState()

# None when no capture is running. A list of _Record while one is.
_records: list[_Record] | None = None


def _format_label(qualname: str, args: tuple[Any], kwargs: dict[str, Any]) -> str:
    """Return the call label, with arguments only when ``log_args`` is on."""

    if not Config.log_args:
        return qualname

    parts = [repr(arg) for arg in args]
    parts.extend(f'{key}={value!r}' for key, value in kwargs.items())
    return f'{qualname}({", ".join(parts)})'


@_check_types.do
def logfunc(func: Callable) -> Callable:
    """Decorate a callable so it is timed while a capture is running.

    :param func: Callable to wrap.
    :type func: collections.abc.Callable
    :returns: Either the original callable or a timing wrapper.
    :rtype: collections.abc.Callable
    """

    if True not in (Config.log_args, Config.log_duration):
        return func

    # Cython staticmethods behave differently when a second decorator is also on
    # the function and it is called through an instance: the instance is passed
    # as an extra leading argument. Detect that case so the wrapper drops it.
    # Cython functions and methods also differ from Python's, so the check has to
    # cope with both; "func_name" is only present on the Cython function objects.
    is_static_method = False

    try:
        func.__call__.__self__.func_name  # NOQA
    except AttributeError:
        if not inspect.isfunction(func):  # function
            is_static_method = True

    @functools.wraps(func)
    def _wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> object:
        """Invoke ``func``, recording its timing when a capture is running.

        :param args: Positional arguments for ``func``.
        :type args: tuple
        :param kwargs: Keyword arguments for ``func``.
        :type kwargs: dict
        :returns: Return value from ``func``.
        :rtype: UNKNOWN
        """

        if is_static_method:
            args = list(args[1:])

        if _records is None:
            return func(*args, **kwargs)

        record = _Record(func.__qualname__, len(_state.stack),
                         _format_label(func.__qualname__, args, kwargs))
        _records.append(record)
        _state.stack.append(0)

        start = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            # Runs on an exception too, so the stack depth always stays right.
            duration = time.perf_counter_ns() - start
            child_time = _state.stack.pop()
            record.duration = duration
            record.self_time = duration - child_time

            if _state.stack:
                _state.stack[-1] += duration

    return _wrapper


@_check_types.do
def begin_capture() -> None:
    """Start recording timings for every decorated call.

    Starting a new capture discards any records from one that never ended.
    """
    global _records
    _records = []


@_check_types.do
def end_capture(print_report: bool = True) -> str:
    """Stop recording and report what was captured.

    :param print_report: Print the report through the debug printer.
    :type print_report: bool
    :returns: The call tree followed by the summary.
    :rtype: str
    """
    global _records

    records: list[_Record] = []
    if _records is not None:
        records = _records

    _records = None

    text = f'{_format_tree(records)}\n\n{_format_summary(records)}'

    if print_report:
        _print_func(text)

    return text


def _format_tree(records: list[_Record]) -> str:
    """One line per call, in the order the calls started."""

    lines = ['CALL TREE   inclusive ms    self ms   call']

    for record in records:
        indent = '  ' * record.depth
        lines.append(f'{record.duration / 1e6:17.3f}{record.self_time / 1e6:12.3f}   '
                     f'{indent}{record.label}')

    return '\n'.join(lines)


def _format_summary(records: list[_Record]) -> str:
    """Per-function totals, sorted by self time."""

    # qualname -> [calls, inclusive ns, self ns, longest inclusive ns]
    totals: dict[str, list[int]] = {}

    for record in records:
        entry = totals.get(record.qualname)
        if entry is None:
            entry = [0, 0, 0, 0]
            totals[record.qualname] = entry

        entry[0] += 1
        entry[1] += record.duration
        entry[2] += record.self_time

        if record.duration > entry[3]:
            entry[3] = record.duration

    rows = sorted(totals.items(), key=lambda item: item[1][2], reverse=True)

    lines = ['SUMMARY     calls    self ms    incl ms   mean self ms   max incl ms   function']

    for qualname, (calls, inclusive, self_time, longest) in rows:
        lines.append(f'{calls:12d}{self_time / 1e6:11.3f}{inclusive / 1e6:11.3f}'
                     f'{self_time / 1e6 / calls:15.4f}{longest / 1e6:14.3f}   {qualname}')

    return '\n'.join(lines)
