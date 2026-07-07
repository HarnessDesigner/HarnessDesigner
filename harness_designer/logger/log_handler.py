# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""CSV-backed logging helpers for :mod:`harness_designer.logger`."""

import platform
from .. import config as _config
import datetime
import io
import re
import sys
import threading
import zipfile
import os
import traceback
import pandas as pd

from .. import __version__
from . import stdout
from . import stderr


Config = _config.Config.logging

# pandas DataFrames aren't thread-safe, and this app touches them from the
# write() path (whichever thread is logging/printing) as well as several
# background loader threads in the log viewer. Concurrent access corrupts
# pandas' Copy-on-Write reference tracking and manifests as a spurious,
# self-sustaining ChainedAssignmentError (logging the warning triggers more
# pandas work, which re-triggers the warning). Every DataFrame construction/
# mutation in the logger and log viewer must go through this lock.
PANDAS_LOCK = threading.RLock()

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


def build_message(msg_type, args):
    """Build a log message and return as a dict for DataFrame"""
    strs = [str(arg) for arg in args]
    msg = ' '.join(strs).rstrip()

    timestamp = datetime.datetime.now()
    msg_type_str = _message_mapping.get(msg_type, 'UNKNOWN')

    return {
        'timestamp': timestamp.isoformat(),
        'level': msg_type_str,
        'message': msg,
        'timestamp_str': str(timestamp)
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


class LogHandler:
    """Write structured log entries to rotating CSV log files."""

    def _fake_callback(self, _=None):
        """Placeholder callback invoked when no external callback is bound.

        :param _: Callback payload from :meth:`write` or :meth:`_open_next_file`.
        :type _: object | None
        :returns: ``None``.
        :rtype: None
        """
        pass

    def __init__(self):
        """Initialize log file rotation state and open the current CSV file."""
        self._callback = self._fake_callback

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

        with PANDAS_LOCK:
            df = pd.DataFrame(columns=['timestamp', 'level', 'message', 'timestamp_str'])
            df.to_csv(path, index=False, encoding='utf-8', lineterminator='\n')
        return path

    def bind(self, callback):
        """Bind a callback invoked after writes and file rotation events.

        :param callback: Callable receiving the written DataFrame or no argument.
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
        with PANDAS_LOCK:
            df = pd.read_csv(path, encoding='utf-8')
            if 'timestamp' in df.columns:
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

        with PANDAS_LOCK:
            df = pd.read_csv(io.BytesIO(data), encoding='utf-8')
            if 'timestamp' in df.columns:
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
        self._callback()

    def _close_current_file(self):
        """Close the active log file and rename it with its end timestamp.

        :returns: ``None``.
        :rtype: None
        """
        self._logfile.close()

        start = _ACTIVE_LOG_RE.match(
            os.path.basename(self._logfile_path)).group(1)
        end = datetime.datetime.now().strftime(_TS_FMT)

        closed_path = _unique_path(f'{start} - {end}.log')
        os.rename(self._logfile_path, closed_path)
        self._logfiles[-1] = closed_path

    def _compact_logfiles(self):
        """Bundle the registered log files into a single ZIP archive.

        :returns: ``None``.
        :rtype: None
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

    def write(self, log_entry: dict):
        """Write a log entry (as dict) to CSV file using pandas"""
        if not log_entry or not log_entry.get('message', '').strip():
            return

        try:
            # Create DataFrame from log entry
            with PANDAS_LOCK:
                df = pd.DataFrame([log_entry])

                # Append to CSV file
                data = df.to_csv(header=False, index=False, encoding='utf-8', lineterminator='\n')
            self._logfile.write(data)
            self._logfile.flush()
            # Update file size
            self._current_size += len(data.encode('utf-8'))

            # Notify callback
            self._callback(df)

            # Check if we need to rotate
            if self._current_size >= Config.max_logfile_size:
                self._close_current_file()
                if len(self._logfiles) >= Config.num_logfiles:
                    self._compact_logfiles()

                self._open_next_file()

        except Exception as e:
            # Write straight to the real stderr, bypassing sys.stdout/stderr.
            # Those are redirected through StdOut/StdErr, which call back
            # into this same write() once a line completes - going through
            # print() here would re-enter write() on every failure, and a
            # persistent error becomes an infinite loop.
            if sys.__stderr__ is not None:
                try:
                    sys.__stderr__.write(f"Error writing to log: {e}\n")
                except Exception:  # NOQA
                    pass

    def close(self):
        """Close the handler.

        The current implementation keeps the file handle open for reuse, so no
        explicit close action is performed here.

        :returns: ``None``.
        :rtype: None
        """
        # No file handle to close since we append per write
        pass

    def flush(self):
        """Flush the handler.

        The current implementation does not manage an additional buffer, so the
        method is effectively a no-op.

        :returns: ``None``.
        :rtype: None
        """
        if self._logfile is not None:
            self._logfile.flush()


class Log(object):
    """Application logger that routes messages to CSV logs and stream wrappers."""

    def __init__(self):
        """Initialize logging, stream redirection, and startup environment logging."""
        self.log_handler = LogHandler()

        self.__stdout = stdout.StdOut(self)
        self.__stderr = _stderr = stderr.StdErr(self)

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

    def _write_lines(self, msg_type, *args):
        args = list(args)

        for arg in args[:]:
            if isinstance(arg, str) and '\n' in arg:
                for line in arg.split('\n'):
                    log_entry = build_message(msg_type, [line])
                    self.log_handler.write(log_entry)
                args.remove(arg)

        if args:
            log_entry = build_message(msg_type, args)
            self.log_handler.write(log_entry)

    def _write_block(self, msg_type, *args):
        log_entry = build_message(msg_type, args)
        self.log_handler.write(log_entry)

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
