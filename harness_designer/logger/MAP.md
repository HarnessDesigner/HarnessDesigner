## FILES

#### __init__.py

Everywhere else in the app does `from . import logger` (or `from ... import logger`) and then calls
`logger.info(...)`, `logger.error(...)`, etc. as if this module were the logger itself. That's implemented
here by constructing the one-and-only `Log` instance (from `log_handler.py`) and binding its methods
directly as module-level names (`startup`, `flush`, `print`/`print_block`, `info`/`info_block`,
`debug`/`debug_block`, `notice`/`notice_block`, `warning`/`warning_block`, `error`/`error_block`,
`traceback`, `database`/`database_block`, and `log_handler` itself) — a plain, traceable alternative to
proxying every attribute access through a dynamic lookup. Note `print = _log.print` deliberately shadows the
builtin at module scope.

#### log_handler.py

`LogHandler(threading.Thread)` — writes structured log entries to rotating CSV log files, entirely on its
own worker thread. `write()` just appends the entry to a plain list and releases a `Semaphore`; it never
touches pandas, the CSV file, or blocks on anything, so callers never stall on log I/O — only `run()` (this
thread's body) ever pops from that list and does the real work. Log/archive files are named after the date
range they cover (the active file is suffixed `" - pending"` until it rotates out, then renamed with its end
timestamp; colons aren't legal in Windows file names, so the time portion uses periods). Files rotate past
`Config.max_logfile_size`, bundle into a ZIP `.archive` once `Config.num_logfiles` is reached, and the oldest
archive is evicted once `Config.num_archives` is hit. `flush()` blocks until everything queued before the
call is both written and flushed to disk — `error()`/`traceback()`/`database()` rely on this guarantee.
`read_log()`/`read_archived_log()` **must parse `'timestamp'` via `pandas.read_csv(parse_dates=...)` itself,
never via a post-hoc `df['timestamp'] = ...` reassignment** — in the frozen app this module is
Cython-compiled, so `df` has no Python frame to be a local of, and pandas 3.x's chained-assignment detection
misattributes a spurious `ChainedAssignmentError` to an unrelated pure-Python frame below it. `Log` (also in
this file) is the application logger that routes `print`/`info`/`debug`/etc. calls into `LogHandler` entries
and owns the `redirect.py` stdout/stderr wrappers; `startup()` writes the one-time GL/machine-info banner
block read from `..gl.info`. **Skeleton-generator mode:** PyCharm builds stubs by importing every compiled module in the project interpreter, each in a throwaway worker process named `Skeleton Generator Worker` (so an installed copy of this package is imported without the app ever starting). `Log.__init__` compares `multiprocessing.current_process().name` with `utils.SKELETON_WORKER_NAME` and, there, uses `NullLogHandler` (every method a no-op) instead of `LogHandler`, and skips the `redirect.StdOut`/`StdErr` wrappers. A no-op stand-in is needed rather than just not starting the thread: `LogHandler.__init__` itself creates the log folder, finalizes leftover `pending` files and opens a new one, and an unstarted handler's `flush()` blocks forever (so the first `error()` call would hang).

#### redirect.py

`_StreamRedirector(io.TextIOWrapper)` — shared buffering/mirroring plumbing for `StdOut`/`StdErr`, which
mirror `sys.stdout`/`sys.stderr` into the logger one completed line at a time (buffers partial text until
`'\n'`, mirrors writes to the real console when one exists, and implements the passthrough methods needed
so code elsewhere still sees a normal file-like object). Which real stream gets wrapped and which `Log`
method a completed line goes to is written directly in each subclass as a plain, fixed call
(`self._logger.info_block(text)` / `self._logger.error_block(text)`) rather than resolved through
`getattr` — easy to trace by reading, and something Cython can see and type at compile time.
