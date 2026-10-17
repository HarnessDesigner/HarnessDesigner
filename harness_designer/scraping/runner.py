# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Running a scraper script in a thread of this process, and stopping it.

Decided by the user (SCRAPER_DESIGN.md, "Running scripts"): the script runs in a
thread, and Stop raises ``SystemExit`` inside that thread
(``PyThreadState_SetAsyncExc``). That reaches the thread only while it is running
Python code. A thread blocked in the operating system (``time.sleep``, a socket
read with no timeout, ``Thread.join()``, ``Queue.get()``, ...) is not reached, and
a long native call that holds the GIL (a catastrophic regex) freezes the whole
application. Those limits are the script author's to manage; the console says so
when a Stop does not take effect, and ``scraping/examples.py`` shows how to write
a script whose waits can be ended from outside.

The attributes of :class:`ScriptRun` that do not start with an underscore are
public on purpose: a second script can find this thread with
``threading.enumerate()`` and look at them.

No Qt in this module.
"""

from collections import deque
from typing import Any

import builtins
import ctypes
import linecache
import sys
import threading
import time
import traceback

from .. import check_types as _check_types

RUNNING = 'running'
FINISHED = 'finished'
FAILED = 'failed'
STOPPED = 'stopped'

# If a script prints faster than the console can show, the oldest text is
# dropped (and counted) rather than letting memory grow without end.
MAX_BUFFERED_CHARS = 2_000_000

# Finished runs kept for the console to show; older ones are forgotten.
MAX_FINISHED_RUNS = 20


class OutputBuffer:
    """Text a script printed that the console has not shown yet. The script's
    thread writes, the GUI takes."""

    @_check_types.do
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: deque[str] = deque()
        self._chars = 0
        self._dropped = 0

    @_check_types.do
    def write(self, text: str) -> None:
        with self._lock:
            self._chunks.append(text)
            self._chars += len(text)
            while self._chars > MAX_BUFFERED_CHARS and len(self._chunks) > 1:
                removed = self._chunks.popleft()
                self._chars -= len(removed)
                self._dropped += len(removed)

    @_check_types.do
    def take(self) -> tuple[str, int]:
        """(the text written since the last call, how many characters were
        dropped before it because nothing took them in time)."""
        with self._lock:
            text = ''.join(self._chunks)
            dropped = self._dropped
            self._chunks.clear()
            self._chars = 0
            self._dropped = 0

        return text, dropped


class ScriptRun(threading.Thread):
    """One run of one script.

    :ivar number: 1, 2, 3... in the order the runs were started.
    :ivar label: The script's name, for display.
    :ivar path: The file it was saved in; ``None`` for an unsaved script.
    :ivar source: The text that was run (the editor may have changed since).
    :ivar output: What the script printed, not yet shown (:class:`OutputBuffer`).
    :ivar state: ``running``, ``finished``, ``failed`` or ``stopped`` (use
        :meth:`status`, which also covers a thread that has already gone).
    :ivar error: The traceback text if the script failed.
    :ivar stop_requested: Stop was pressed at least once.
    """

    @_check_types.do
    def __init__(self, number: int, source: str, label: str, path: str | None = None) -> None:
        super().__init__(name=f'script-{number}', daemon=True)
        self.number = number
        self.label = label
        self.path = path
        self.source = source
        self.output = OutputBuffer()
        self.state = RUNNING
        self.error = ''
        self.stop_requested = False
        self.started_at = time.monotonic()
        self.ended_at: float | None = None
        self._code_name = f'<{label} run {number}>'

    # -- what the console shows -----------------------------------------------

    @_check_types.do
    def status(self) -> str:
        """The state, correct even when the thread ended in a way that did not
        get to record it (a Stop that arrived while it was tidying up)."""
        if self.state == RUNNING and self.ident is not None and not self.is_alive():
            if self.stop_requested:
                return STOPPED

            return FINISHED

        return self.state

    @_check_types.do
    def elapsed(self) -> float:
        """Seconds the script has run (or ran)."""
        end = self.ended_at
        if end is None:
            end = time.monotonic()

        return end - self.started_at

    # -- stopping -------------------------------------------------------------------

    @_check_types.do
    def request_stop(self) -> bool:
        """Raise ``SystemExit`` inside the script's thread.

        It takes effect only when that thread next runs Python code; a thread
        waiting in the operating system keeps waiting. Returns ``False`` when
        there was no running thread to send it to.

        :raises RuntimeError: The request would have reached more than one
            thread; it was cancelled.
        """
        ident = self.ident
        if ident is None or not self.is_alive():
            return False

        self.stop_requested = True
        delivered = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(ident), ctypes.py_object(SystemExit))
        if delivered > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(ident), None)
            raise RuntimeError('Stop would have reached more than one thread, so it was cancelled.')

        return delivered == 1

    # -- the thread -------------------------------------------------------------------

    @_check_types.do
    def run(self) -> None:
        self.started_at = time.monotonic()
        try:
            self._execute()
        except SystemExit:
            # A Stop that arrived after the script had ended, while this thread
            # was still tidying up: nothing is left to stop.
            pass
        finally:
            if self.state == RUNNING:
                if self.stop_requested:
                    self.state = STOPPED
                else:
                    self.state = FINISHED

            self.ended_at = time.monotonic()
            linecache.cache.pop(self._code_name, None)

    @_check_types.do
    def _execute(self) -> None:
        lines = self.source.splitlines(keepends=True)
        # So a traceback can show the script's own lines.
        linecache.cache[self._code_name] = (len(self.source), None, lines, self._code_name)

        try:
            code = compile(self.source, self._code_name, 'exec')
            exec(code, self._namespace())
        except SystemExit as leaving:
            self._left(leaving)
        except BaseException as problem:
            self.error = self._format_error(problem)
            self.output.write(self.error)
            self.state = FAILED
        else:
            self.state = FINISHED

    @_check_types.do
    def _left(self, leaving: SystemExit) -> None:
        """The script ended through ``SystemExit``: Stop, or its own ``sys.exit()``."""
        # The state is set last: whoever sees it change can rely on the output being complete.
        if self.stop_requested:
            self.output.write('\n[Stopped]\n')
            self.state = STOPPED
            return

        if leaving.code not in (None, 0):
            self.output.write(f'\n[The script exited with {leaving.code!r}]\n')

        self.state = FINISHED

    @_check_types.do
    def _format_error(self, problem: BaseException) -> str:
        """The traceback from the script's own first frame on (the runner's
        frames above it are not the user's business)."""
        trace = problem.__traceback__
        while trace is not None and trace.tb_frame.f_code.co_filename != self._code_name:
            trace = trace.tb_next

        return ''.join(traceback.format_exception(type(problem), problem, trace))

    @_check_types.do
    def _namespace(self) -> dict[str, Any]:
        script_builtins = dict(vars(builtins))
        script_builtins['print'] = self._print
        script_builtins['input'] = self._input

        file_name = self.path
        if file_name is None:
            file_name = self._code_name

        return {'__name__': '__main__', '__file__': file_name, '__builtins__': script_builtins}

    @_check_types.do
    def _print(self, *values: tuple[Any], sep: str | None = None, end: str | None = None, file: Any = None,
               flush: bool = False) -> None:
        """The script's ``print``: into the console, unless it names some
        other file object."""
        if file is not None and file is not sys.stdout and file is not sys.stderr:
            builtins.print(*values, sep=sep, end=end, file=file, flush=flush)
            return

        if sep is None:
            sep = ' '

        if end is None:
            end = '\n'

        self.output.write(sep.join(str(value) for value in values) + end)

    @_check_types.do
    def _input(self, prompt: str = '') -> str:
        raise RuntimeError('input() is not available in the script editor, which has no keyboard input for a '
                           'script. Put the value in the script instead.')


class Runner:
    """The scripts that have been started in this process, newest last."""

    @_check_types.do
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: list[ScriptRun] = []
        self._counter = 0

    @_check_types.do
    def start(self, source: str, label: str, path: str | None = None) -> ScriptRun:
        """Start running *source* now. Several runs may be alive at once (a
        second script is how a stuck first one is released)."""
        with self._lock:
            self._counter += 1
            run = ScriptRun(self._counter, source, label, path)
            self._runs.append(run)
            self._trim()

        run.start()
        return run

    @_check_types.do
    def runs(self) -> list[ScriptRun]:
        with self._lock:
            return list(self._runs)

    @_check_types.do
    def active(self) -> list[ScriptRun]:
        """The runs whose thread is still alive."""
        return [run for run in self.runs() if run.status() == RUNNING]

    @_check_types.do
    def forget(self, run: ScriptRun) -> bool:
        """Drop a finished run from the list. A run still alive is kept."""
        with self._lock:
            if run.status() == RUNNING or run not in self._runs:
                return False

            self._runs.remove(run)
            return True

    @_check_types.do
    def stop_all(self) -> int:
        """Send Stop to every live run (the application is closing). Returns
        how many it was sent to; does not wait for them."""
        sent = 0
        for run in self.active():
            try:
                if run.request_stop():
                    sent += 1
            except RuntimeError:
                continue

        return sent

    @_check_types.do
    def _trim(self) -> None:
        """Forget the oldest finished runs beyond the limit (caller holds the lock)."""
        finished = [run for run in self._runs if run.status() != RUNNING]
        for run in finished[:-MAX_FINISHED_RUNS]:
            self._runs.remove(run)
