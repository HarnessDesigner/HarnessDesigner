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
            df.to_csv(last_log, index=False, encoding='utf-8', lineterminator='\n')

        self._logfile_path = last_log
        self._logfile = open(last_log, 'a', encoding='utf-8', newline='')
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
        df.to_csv(log, index=False, encoding='utf-8', lineterminator='\n')

        self._current_size = os.path.getsize(log)
        self._logfile = open(log, 'a', encoding='utf-8', newline='')
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
            data = df.to_csv(header=False, index=False, encoding='utf-8', lineterminator='\n')
            self._logfile.write(data)

            # Update file size
            self._current_size += len(data.encode('utf-8'))

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
        if self._logfile is not None:
            self._logfile.flush()


class Log(object):
    """Application logger that routes messages to CSV logs and stream wrappers."""

    def __init__(self):
        """Initialize logging, stream redirection, and startup environment logging."""
        self.log_handler = LogHandler()

        self.__stdout = stdout.StdOut(self)
        self.__stderr = _stderr = stderr.StdErr(self)

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

        startup_block.extend([
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
        ])

        self.info_block('\n'.join(startup_block))

        from ..import logger as _logger
        _logger.logger = self

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
            lines = traceback.format_exception(exception)

            for line in lines:
                line = line.rstrip()
                log_entry = build_message(TRACEBACK, [line])
                self.log_handler.write(log_entry)
                self.log_handler.flush()

    def database(self, *args):
        if Config.log_database:
            self._write_lines(DATABASE, *args)
            self.log_handler.flush()

    def database_block(self, *args):
        if Config.log_database:
            self._write_block(DATABASE, *args)
            self.log_handler.flush()
