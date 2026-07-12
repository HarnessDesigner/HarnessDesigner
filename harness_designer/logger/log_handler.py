# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""CSV-backed logging helpers for :mod:`harness_designer.logger`."""

import platform
from .. import config as _config
import datetime
import io
import re
import sys
import threading
import typing
import zipfile
import os
import traceback
import pandas as pd

from .. import __version__
from . import redirect


Config = _config.Config.logging


class RotationEvent(typing.NamedTuple):
    """Sent to LogHandler's bound callback (via CallAfter) when the active
    file rotates. `closed_path` is always where the just-closed file now
    lives; `archive_path` is set too if that same rotation also bundled it
    (and other closed files) into a new archive - in which case
    `closed_path` no longer exists on its own, only as a member of it.
    """
    closed_path: str
    archive_path: typing.Optional[str]


INFO = 0
NOTICE = 1
WARNING = 2
DEBUG = 3
TRACEBACK = 4
ERROR = 5
WX_ERROR = 6
DATABASE = 7
FILE_TRANSFER = 8

_message_mapping = {
    INFO: 'INFO',
    NOTICE: 'NOTICE',
    WARNING: 'WARNING',
    DEBUG: 'DEBUG',
    TRACEBACK: 'TRACEBACK',
    ERROR: 'ERROR',
    WX_ERROR: 'WX_ERROR',
    DATABASE: 'DATABASE',
    FILE_TRANSFER: 'FILE'
}


def build_message(msg_type, msg):
    """Build a single log entry dict for a DataFrame row.

    `timestamp` is kept as a real datetime, not a string, so DataFrames
    built from this dict already have a proper datetime64 'timestamp'
    column from birth - nothing downstream needs to re-parse or reassign
    it (the .copy() + column-reassignment pattern pandas' chained-
    assignment machinery warns about). There's no separate string column
    for it either; formatting for display happens where it's displayed,
    not cached here.
    """
    return {
        'timestamp': datetime.datetime.now(),
        'level': _message_mapping.get(msg_type, 'UNKNOWN'),
        'message': msg,
    }


# Log/archive files are named after the date range they cover, so the range
# is visible without opening the file. The active file is suffixed
# " - pending" until it rotates out, at which point it's renamed with its
# end timestamp. Colons aren't legal in Windows file names, so the time
# portion uses periods instead. Month-day-year text doesn't sort correctly
# across month/year boundaries, so ordering is done by parsing each name's
# timestamp(s) rather than by raw string comparison. The trailing
# "(?:-\d+)?" on each pattern tolerates the "-N" suffix _unique_path() adds
# when a burst of rotations lands two files at the same second.
_TS_FMT = '%m-%d-%Y.%H.%M.%S'
_TS_PATTERN = r'\d{2}-\d{2}-\d{4}\.\d{2}\.\d{2}\.\d{2}'
_ACTIVE_LOG_RE = re.compile(rf'^({_TS_PATTERN}) - pending(?:-\d+)?\.log$')
_CLOSED_LOG_RE = re.compile(
    rf'^({_TS_PATTERN}) - ({_TS_PATTERN})(?:-\d+)?\.log$')
_ARCHIVE_RE = re.compile(
    rf'^({_TS_PATTERN}) - ({_TS_PATTERN})(?:-\d+)?\.archive$')


def _parse_ts(text):
    """Parse a filename timestamp field back into a ``datetime``.

    :param text: Timestamp field matched from a log/archive file name.
    :type text: str
    :returns: Parsed timestamp.
    :rtype: datetime.datetime
    """
    return datetime.datetime.strptime(text, _TS_FMT)


def _unique_path(name):
    """Return ``name`` under ``Config.save_path``, disambiguated on collision."""
    path = os.path.join(Config.save_path, name)
    if not os.path.exists(path):
        return path

    stem, ext = os.path.splitext(name)
    n = 1
    while True:
        path = os.path.join(Config.save_path, f'{stem}-{n}{ext}')
        if not os.path.exists(path):
            return path
        n += 1


class LogHandler(threading.Thread):
    """Write structured log entries to rotating CSV log files.

    Writing runs entirely on this object's own thread. write() just
    appends the entry to a plain list and releases a semaphore - it never
    touches pandas, the CSV file, or blocks on anything, so callers never
    stall on log I/O. run() (this thread's body) is the only code that
    ever pops from that list and does the actual work, so there's nothing
    to lock between one call to write() and another.
    """

    def _fake_callback(self, _=None):
        """Placeholder callback invoked when no external callback is bound.

        :param _: A DataFrame for a new entry, or a RotationEvent for a
            rotation.
        :type _: pandas.DataFrame | RotationEvent | None
        :returns: ``None``.
        :rtype: None
        """
        pass

    def __init__(self):
        """Initialize log file rotation state and open the current CSV file."""
        super().__init__(daemon=True)

        self._callback = self._fake_callback

        # FIFO work queue for the worker thread: append()/pop(0) are each
        # a single atomic operation under the GIL, and there's exactly one
        # consumer (run(), on this thread), so nothing else needs to guard
        # access to this list.
        self._queue = []
        # Starts at 0 so run()'s first acquire() blocks immediately;
        # write()/flush() each call release() exactly once per item they
        # add, which is always valid on a Semaphore (unlike a Lock, it has
        # no "already unlocked" error state to race into).
        self._signal = threading.Semaphore(0)
        self._exit_event = threading.Event()

        if not os.path.exists(Config.save_path):
            os.makedirs(Config.save_path)

        # Enumerated once here; every rotation/archive/eviction afterwards
        # just appends to or pops from these two ordered (oldest-first)
        # lists instead of re-scanning the directory.
        self._logfiles = self._scan(_ACTIVE_LOG_RE, _CLOSED_LOG_RE)
        self._archives = self._scan(_ARCHIVE_RE)

        # Only the newest "pending" file is resumable; any older ones are
        # leftovers from a crash and need to be finalized so they're
        # eligible for archiving like any other closed log file.
        for path in self._logfiles[:-1]:
            match = _ACTIVE_LOG_RE.match(os.path.basename(path))
            if match:
                end = datetime.datetime.fromtimestamp(
                    os.path.getmtime(path)).strftime(_TS_FMT)
                closed_path = _unique_path(f'{match.group(1)} - {end}.log')
                os.rename(path, closed_path)
                self._logfiles[self._logfiles.index(path)] = closed_path

        if self._logfiles and _ACTIVE_LOG_RE.match(
                os.path.basename(self._logfiles[-1])):
            active = self._logfiles[-1]
        else:
            active = self._create_logfile()
            self._logfiles.append(active)

        self._logfile_path = active
        self._logfile = open(active, 'a', encoding='utf-8', newline='')

        # Track current file size
        self._current_size = os.path.getsize(active)

    @staticmethod
    def _scan(*patterns):
        """Enumerate ``Config.save_path`` for names matching ``patterns``.

        :param patterns: Compiled regexes to match against file names.
        :type patterns: re.Pattern
        :returns: Matching paths, sorted oldest first by their parsed
            starting timestamp.
        :rtype: list[str]
        """
        entries = []
        for name in os.listdir(Config.save_path):
            for pattern in patterns:
                match = pattern.match(name)
                if match:
                    entries.append((_parse_ts(match.group(1)), name))
                    break

        entries.sort(key=lambda entry: entry[0])
        return [os.path.join(Config.save_path, name) for _, name in entries]

    @staticmethod
    def _create_logfile():
        """Create a fresh, empty CSV log file named for the current time.

        :returns: Path to the newly created file.
        :rtype: str
        """
        start = datetime.datetime.now().strftime(_TS_FMT)
        path = _unique_path(f'{start} - pending.log')

        df = pd.DataFrame(columns=['timestamp', 'level', 'message'])
        df.to_csv(path, index=False, encoding='utf-8', lineterminator='\n')
        return path

    def bind(self, callback):
        """Bind a callback invoked (via CallAfter, on the main thread) after
        writes and file rotation events.

        :param callback: Callable receiving either the written entry's
            DataFrame, or - on rotation - a RotationEvent.
        :type callback: collections.abc.Callable
        :returns: ``None``.
        :rtype: None
        """
        self._callback = callback

    def get_current_log_path(self):
        """Return the path to the current log file"""
        return self._logfile_path

    def list_logfiles(self):
        """Return current (non-archived) log file paths, oldest first.

        :returns: Snapshot of the registered, un-archived log file paths.
        :rtype: list[str]
        """
        return list(self._logfiles)

    def list_archives(self):
        """Return archive file paths, oldest first.

        :returns: Snapshot of the registered archive file paths.
        :rtype: list[str]
        """
        return list(self._archives)

    @staticmethod
    def list_archive_contents(archive_path):
        """Return the log file names bundled inside an archive.

        :param archive_path: Path to an archive returned by :meth:`list_archives`.
        :type archive_path: str
        :returns: Member log file names, in archive order.
        :rtype: list[str]
        """
        with zipfile.ZipFile(archive_path, 'r') as zf:
            return zf.namelist()

    @staticmethod
    def read_log(path):
        """Read a log file into a DataFrame with ``timestamp`` parsed.

        :param path: Path to a log file returned by :meth:`list_logfiles`.
        :type path: str
        :returns: Parsed log entries.
        :rtype: pandas.DataFrame
        """
        df = pd.read_csv(path, encoding='utf-8')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    @staticmethod
    def read_archived_log(archive_path, member_name):
        """Read one bundled log file out of an archive into a DataFrame.

        :param archive_path: Path to an archive returned by :meth:`list_archives`.
        :type archive_path: str
        :param member_name: Name from :meth:`list_archive_contents`.
        :type member_name: str
        :returns: Parsed log entries.
        :rtype: pandas.DataFrame
        """
        with zipfile.ZipFile(archive_path, 'r') as zf:
            data = zf.read(member_name)

        df = pd.read_csv(io.BytesIO(data), encoding='utf-8')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def _open_next_file(self):
        """Create, open, and register the next CSV log file.

        :returns: ``None``.
        :rtype: None
        """
        path = self._create_logfile()
        self._logfiles.append(path)

        self._logfile_path = path
        self._current_size = os.path.getsize(path)
        self._logfile = open(path, 'a', encoding='utf-8', newline='')

    def _close_current_file(self):
        """Close the active log file and rename it with its end timestamp.

        :returns: The path the active file was renamed to.
        :rtype: str
        """
        self._logfile.close()

        start = _ACTIVE_LOG_RE.match(
            os.path.basename(self._logfile_path)).group(1)
        end = datetime.datetime.now().strftime(_TS_FMT)

        closed_path = _unique_path(f'{start} - {end}.log')
        os.rename(self._logfile_path, closed_path)
        self._logfiles[-1] = closed_path
        return closed_path

    def _compact_logfiles(self):
        """Bundle the registered log files into a single ZIP archive.

        :returns: Path to the new archive.
        :rtype: str
        """
        start = _CLOSED_LOG_RE.match(
            os.path.basename(self._logfiles[0])).group(1)
        end = _CLOSED_LOG_RE.match(
            os.path.basename(self._logfiles[-1])).group(2)

        if len(self._archives) >= Config.num_archives:
            os.remove(self._archives.pop(0))

        archive_path = _unique_path(f'{start} - {end}.archive')

        zf = zipfile.ZipFile(archive_path, mode='x')
        for path in self._logfiles:
            zf.write(path, arcname=os.path.basename(path))
        zf.close()

        for path in self._logfiles:
            os.remove(path)

        self._logfiles = []
        self._archives.append(archive_path)
        return archive_path

    def write(self, log_entry: dict):
        """Queue a log entry for the worker thread to write. Never blocks."""
        if not log_entry or not log_entry.get('message', '').strip():
            return

        self._queue.append(log_entry)
        self._signal.release()

    def run(self):
        """Worker thread body: the only code that writes/rotates log files."""
        while not self._exit_event.is_set():
            self._signal.acquire()

            while self._queue:
                item = self._queue.pop(0)
                if isinstance(item, threading.Event):
                    # A flush()/stop() barrier: flush what's been written so
                    # far *before* releasing the caller waiting on it - that
                    # ordering is the guarantee flush() makes.
                    self._flush_file()
                    item.set()
                else:
                    self._process_entry(item)

            # Queue's empty: one flush for however many entries were just
            # batched through in this pass, instead of one per entry.
            self._flush_file()

    def _flush_file(self):
        if self._logfile is not None:
            self._logfile.flush()

    def _process_entry(self, log_entry: dict):
        """Write one entry to the CSV file and rotate if it's now too big."""
        try:
            df = pd.DataFrame([log_entry])

            # date_format matches datetime.isoformat() so the on-disk
            # format is unchanged now that 'timestamp' is a real
            # datetime64 column instead of a pre-stringified one.
            data = df.to_csv(header=False, index=False, encoding='utf-8',
                             lineterminator='\n',
                             date_format='%Y-%m-%dT%H:%M:%S.%f')

            self._logfile.write(data)
            self._current_size += len(data.encode('utf-8'))

            # Deferred: this module is imported synchronously as part of
            # harness_designer.app's own module-level `from . import
            # logger`, so `..app` isn't fully loaded yet at that point. By
            # the time a write actually happens, it is.
            from .. import app as _app
            _app.CallAfter(self._callback, df)

            if self._current_size >= Config.max_logfile_size:
                closed_path = self._close_current_file()

                archive_path = None
                if len(self._logfiles) >= Config.num_logfiles:
                    archive_path = self._compact_logfiles()

                self._open_next_file()

                # A RotationEvent (as opposed to write()'s DataFrame) tells
                # the viewer this is a rotation, and where the file it
                # might currently be showing now lives.
                _app.CallAfter(
                    self._callback, RotationEvent(closed_path, archive_path))

        except Exception as e:
            # Write straight to the real stderr, bypassing sys.stdout/stderr.
            # Those are redirected through StdOut/StdErr, which route back
            # into write() once a line completes - going through print()
            # here would just queue another entry for this same thread to
            # pick up, and a persistent error becomes an infinite loop.
            if sys.__stderr__ is not None:
                try:
                    sys.__stderr__.write(f"Error writing to log: {e}\n")
                except Exception:  # NOQA
                    pass

    def stop(self):
        """Drain the queue, stop the worker thread, and close the file.

        Blocks until every entry queued before this call is written.
        """
        self.flush()
        self._exit_event.set()
        self._signal.release()
        self.join()

        if self._logfile is not None:
            self._logfile.close()

    def close(self):
        """Stop the worker thread, writing everything already queued first."""
        self.stop()

    def flush(self):
        """Block until every entry queued before this call has been
        written *and* flushed to disk.

        write() is async (queued to the worker thread), so this is what
        error()/traceback()/database() rely on to guarantee their line is
        actually on disk before they return. The flush itself happens on
        the worker thread, in run(), before it releases this barrier.
        """
        barrier = threading.Event()
        self._queue.append(barrier)
        self._signal.release()
        barrier.wait()

        if self._logfile is not None:
            self._logfile.flush()


class Log(object):
    """Application logger that routes messages to CSV logs and stream wrappers."""

    def __init__(self):
        """Initialize logging, stream redirection, and startup environment logging."""
        self.log_handler = LogHandler()
        self.log_handler.start()

        # `self` is a fully usable Log instance already (methods resolve
        # via the class, independent of __init__ completing), so it's
        # handed straight to the wrappers instead of having them import
        # harness_designer.logger on every write.
        self._stdout = redirect.StdOut(self)
        self._stderr = redirect.StdErr(self)

    def startup(self):
        from ..gl import info as _gl_info

        startup_block = [
            '----------------------------------------',
            '        Harness Designer started',
            '----------------------------------------',
            '',
            f'Harness Designer Version: {__version__.string}',
            '',
            '--------------    GL     ---------------'
        ]

        data = _gl_info.get()
        for header, items in data.items():
            if isinstance(items, dict):
                pre_suf_count = int((40 - (len(header) + 4)) / 2)
                pre_suf = '=' * pre_suf_count
                header_line = f'{pre_suf}  {header}  '

                if pre_suf_count % 2:
                    pre_suf = f' {pre_suf}'

                startup_block.append(header_line + pre_suf)

                for label, value in items.items():
                    startup_block.append(f'{label}: {value}')

                startup_block.append('')
            else:
                startup_block.append(f'{header}: {items}')

        startup_block.extend(
            [
                '',
                '----------------------------------------',
                '',
                '--------------  Machine  ---------------',
                '',
                f'Machine type: {platform.machine()}',
                f'Processor: {platform.processor()}',
                f'Architecture: {platform.architecture()}',
                (
                    'Python: '
                    f'{platform.python_branch()} '
                    f'{platform.python_version()} '
                    f'{platform.python_implementation()} '
                    f'{platform.python_build()} '
                    f'[{platform.python_compiler()}]'
                ),
                '',
                '----------------------------------------',
                ''
            ]
        )

        self.info_block('\n'.join(startup_block))

    @staticmethod
    def _join(args):
        return ' '.join(str(arg) for arg in args).rstrip()

    def _write_lines(self, msg_type, *args):
        """Write each line of the joined args as its own log entry."""
        for line in self._join(args).split('\n'):
            self.log_handler.write(build_message(msg_type, line))

    def _write_block(self, msg_type, *args):
        """Write the joined args as a single, possibly multiline, log entry."""
        self.log_handler.write(build_message(msg_type, self._join(args)))

    def flush(self):
        """Flush the underlying :class:`LogHandler`.

        :returns: ``None``.
        :rtype: None
        """
        self.log_handler.flush()

    def print(self, *args, msg_type=INFO):
        self._write_lines(msg_type, *args)

    def print_block(self, *args, msg_type=INFO):
        self._write_block(msg_type, *args)

    def info(self, *args):
        self._write_lines(INFO, *args)

    def info_block(self, *args):
        self._write_block(INFO, *args)

    def debug(self, *args):
        if Config.log_debug:
            self._write_lines(DEBUG, *args)

    def debug_block(self, *args):
        if Config.log_debug:
            self._write_block(DEBUG, *args)

    def notice(self, *args):
        if Config.log_notice:
            self._write_lines(NOTICE, *args)

    def notice_block(self, *args):
        if Config.log_notice:
            self._write_block(NOTICE, *args)

    def warning(self, *args):
        if Config.log_warning:
            self._write_lines(WARNING, *args)

    def warning_block(self, *args):
        if Config.log_warning:
            self._write_block(WARNING, *args)

    def error(self, *args):
        if Config.log_error:
            self._write_lines(ERROR, *args)
            self.log_handler.flush()

    def error_block(self, *args):
        if Config.log_error:
            self._write_block(ERROR, *args)
            self.log_handler.flush()

    def traceback(self, exception, msg=None):
        """Write an exception traceback and optional message.

        :param exception: Exception instance to format.
        :type exception: BaseException
        :param msg: Optional message written before the traceback.
        :type msg: str | None
        :returns: ``None``.
        :rtype: None
        """
        if msg:
            self.error(msg)

        if Config.log_traceback:
            block = ''.join(traceback.format_exception(exception)).rstrip()
            if block:
                self._write_block(TRACEBACK, block)
                self.log_handler.flush()

    def database(self, *args):
        if Config.log_database:
            self._write_lines(DATABASE, *args)
            self.log_handler.flush()

    def database_block(self, *args):
        if Config.log_database:
            self._write_block(DATABASE, *args)
            self.log_handler.flush()
