# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""CSV-backed logging helpers for :mod:`harness_designer.logger`."""

import platform
from .. import config as _config
import datetime
import zipfile
import os
import traceback
import pandas as pd

from .. import __version__
from . import stdout
from . import stderr


Config = _config.Config.logging

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
        'message': msg
    }


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

        last_log = None
        index = 0
        for i in range(Config.num_logfiles):
            log = f'log-{i + 1}.csv'
            log = os.path.join(Config.save_path, log)
            if os.path.exists(log):
                last_log = log
                index = i + 1
            else:
                break

        if last_log is None:
            index = 1
            last_log = os.path.join(Config.save_path, 'log-1.csv')
            # Create empty CSV with headers
            df = pd.DataFrame(columns=['timestamp', 'level', 'message'])
            df.to_csv(last_log, index=False)

        self._logfile_path = last_log
        self._logfile = open(last_log, 'a')
        self._index = index

        # Track current file size
        self._current_size = os.path.getsize(last_log)

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

    def _open_next_file(self):
        """Create and open the next CSV log file in the rotation sequence.

        :returns: ``None``.
        :rtype: None
        """
        if self._logfile is not None:
            self._logfile.close()

        log = f'log-{self._index}.csv'
        log = os.path.join(Config.save_path, log)
        self._logfile_path = log

        # Create new CSV file with headers
        df = pd.DataFrame(columns=['timestamp', 'level', 'message'])
        df.to_csv(log, index=False)

        self._current_size = os.path.getsize(log)
        self._logfile = open(log, 'a')
        self._callback()

    def _archive_files(self):
        """Archive the current set of log files into a ZIP rotation.

        :returns: ``None``.
        :rtype: None
        :raises OSError: Raised when archive files cannot be moved or removed.
        """
        if self._logfile is not None:
            self._logfile.close()

        for i in range(Config.num_archives):
            archive_name = f'log_archive-{i + 1}.zip'
            archive_path = os.path.join(Config.save_path, archive_name)
            if not os.path.exists(archive_path):
                break
        else:
            archive_name = f'log_archive-1.zip'
            archive_path = os.path.join(Config.save_path, archive_name)
            os.remove(archive_path)

            for i in range(1, Config.num_archives):
                src_name = f'log_archive-{i + 1}.zip'
                dst_name = f'log_archive-{i}.zip'

                src_path = os.path.join(Config.save_path, src_name)
                dst_path = os.path.join(Config.save_path, dst_name)
                os.rename(src_path, dst_path)

            archive_name = f'log_archive-{Config.num_archives}.zip'
            archive_path = os.path.join(Config.save_path, archive_name)

        zf = zipfile.ZipFile(archive_path, mode='x')
        for i in range(Config.num_logfiles):
            log = f'log-{i + 1}.csv'
            log = os.path.join(Config.save_path, log)
            if os.path.exists(log):
                zf.write(log, arcname=os.path.basename(log))
        zf.close()

        for i in range(Config.num_logfiles):
            log = f'log-{i + 1}.csv'
            log = os.path.join(Config.save_path, log)
            if os.path.exists(log):
                os.remove(log)

        self._index = 1

    def write(self, log_entry: dict):
        """Write a log entry (as dict) to CSV file using pandas"""
        if not log_entry or not log_entry.get('message', '').strip():
            return

        try:
            # Create DataFrame from log entry
            df = pd.DataFrame([log_entry])

            # Append to CSV file
            data = df.to_csv(header=False, index=False)
            self._logfile.write(data.strip() + '\n')

            # Update file size
            self._current_size += len(data)

            # Notify callback
            self._callback(df)

            # Check if we need to rotate
            if self._current_size >= Config.max_logfile_size:
                self._index += 1
                if self._index > Config.num_logfiles:
                    self._archive_files()

                self._open_next_file()

        except Exception as e:
            # Fallback in case of write error - don't want to crash the app
            print(f"Error writing to log: {e}")

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
        # No buffering to flush
        pass


class Log(object):
    """Application logger that routes messages to CSV logs and stream wrappers."""

    def __init__(self):
        """Initialize logging, stream redirection, and startup environment logging."""
        self.log_handler = LogHandler()

        self.__stdout = stdout.StdOut(self)
        self.__stderr = _stderr = stderr.StdErr(self)

        from ..gl import info as _gl_info

        self.info('----------------------------------------')
        self.info('        Harness Designer started')
        self.info('----------------------------------------')
        self.info('')
        self.info('Harness Designer Version:', __version__.string)
        self.info('\n')
        self.info('--------------    GL     ---------------')

        data = _gl_info.get()
        for header, items in data.items():

            if isinstance(items, dict):
                pre_suf_count = int((40 - (len(header) + 4)) / 2)

                pre_suf = '=' * pre_suf_count

                header = f'{pre_suf}  {header}  '

                if pre_suf_count % 2:
                    pre_suf = f' {pre_suf}'

                self.info(header + pre_suf)

                for label, value in items.items():
                    self.info(f'{label}:', value)

                self.info('\n')
            else:
                self.info(f'{header}:', items)
        self.info('\n', '----------------------------------------', '\n')

        self.info('--------------  Machine  ---------------', '\n')
        self.info('Machine type:', platform.machine())
        self.info('Processor:', platform.processor())
        self.info('Architecture:', platform.architecture())
        self.info(
            'Python:',
            platform.python_branch(),
            platform.python_version(),
            platform.python_implementation(),
            platform.python_build(),
            f'[{platform.python_compiler()}]'
        )
        self.info('\n', '----------------------------------------', '\n')

        from ..import logger as _logger
        _logger.logger = self

    def flush(self):
        """Flush the underlying :class:`LogHandler`.

        :returns: ``None``.
        :rtype: None
        """
        self.log_handler.flush()

    def print(self, *args, msg_type=INFO):
        """Write a message with an explicit log level.

        Embedded newline characters are split into separate log entries.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :param msg_type: Numeric log level constant.
        :type msg_type: int
        :returns: ``None``.
        :rtype: None
        """
        args = list(args)

        for arg in args[:]:
            if isinstance(arg, str) and '\n' in arg:
                for line in arg.split('\n'):
                    log_entry = build_message(msg_type, line)
                    self.log_handler.write(log_entry)
                args.remove(arg)

        if args:
            log_entry = build_message(msg_type, args)
            self.log_handler.write(log_entry)

    def info(self, *args):
        """Write an informational message.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        args = list(args)

        for arg in args[:]:
            if isinstance(arg, str) and '\n' in arg:
                for line in arg.split('\n'):
                    log_entry = build_message(INFO, line)
                    self.log_handler.write(log_entry)
                args.remove(arg)

        if args:
            log_entry = build_message(INFO, args)
            self.log_handler.write(log_entry)

    def debug(self, *args):
        """Write a debug message when debug logging is enabled.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        if Config.log_debug:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(DEBUG, line)
                        self.log_handler.write(log_entry)
                    args.remove(arg)

            if args:
                log_entry = build_message(DEBUG, args)
                self.log_handler.write(log_entry)

    def notice(self, *args):
        """Write a notice message when notice logging is enabled.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        if Config.log_notice:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(NOTICE, line)
                        self.log_handler.write(log_entry)
                    args.remove(arg)

            if args:
                log_entry = build_message(NOTICE, args)
                self.log_handler.write(log_entry)

    def warning(self, *args):
        """Write a warning message when warning logging is enabled.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        if Config.log_warning:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(WARNING, line)
                        self.log_handler.write(log_entry)
                    args.remove(arg)

            if args:
                log_entry = build_message(WARNING, args)
                self.log_handler.write(log_entry)

    def error(self, *args):
        """Write an error message when error logging is enabled.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        if Config.log_error:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(ERROR, line)
                        self.log_handler.write(log_entry)
                        self.log_handler.flush()
                    args.remove(arg)

            if args:
                log_entry = build_message(ERROR, args)
                self.log_handler.write(log_entry)
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
            lines = traceback.format_exception(exception)

            for line in lines:
                line = line.rstrip()
                log_entry = build_message(TRACEBACK, [line])
                self.log_handler.write(log_entry)
                self.log_handler.flush()

    def database(self, *args):
        """Write a database log message when database logging is enabled.

        :param args: Message parts to stringify and join.
        :type args: tuple
        :returns: ``None``.
        :rtype: None
        """
        if Config.log_database:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(DATABASE, line)
                        self.log_handler.write(log_entry)
                        self.log_handler.flush()

                    args.remove(arg)

            if args:
                log_entry = build_message(DATABASE, args)
                self.log_handler.write(log_entry)
                self.log_handler.flush()
