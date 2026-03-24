'''
import wx
import platform
from .. import config as _config
import datetime
import zipfile
import os
import traceback

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
    INFO: 'INFO:',
    NOTICE: 'NOTICE:',
    WARNING: 'WARNING:',
    DEBUG: 'DEBUG:',
    TRACEBACK: 'TRACEBACK:',
    ERROR: 'ERROR:',
    WX_ERROR: 'WX_ERROR:',
    DATABASE: 'DATABASE:',
    FILE_TRANSFER: 'FILE:'

}


def _build_message(msg_type, args):
    strs = [str(arg) for arg in args]

    msg = ' '.join(strs).rstrip()

    timestamp = datetime.datetime.now()
    timestamp = timestamp.strftime('(%m.%d.%Y-%H:%M:%S)')

    msg_type = _message_mapping.get(msg_type, 'UNKNOWN:')

    msg_type = f'{timestamp} {msg_type} '
    msg = msg.replace('\n', f'\n{msg_type}')

    return f'{msg_type}{msg}\n'


class LogHandler:

    def _fake_callback(self, _=None):
        pass

    def __init__(self):
        self._callback = self._fake_callback

        if not os.path.exists(Config.save_path):
            os.makedirs(Config.save_path)

        last_log = None
        index = 0
        for i in range(Config.num_logfiles):
            log = f'log-{i + 1}.log'
            log = os.path.join(Config.save_path, log)
            if os.path.exists(log):
                last_log = log
                index = i + 1
            else:
                break

        if last_log is None:
            index = 1
            last_log = os.path.join(Config.save_path, 'log-1.log')
            with open(last_log, 'w') as f:
                f.write('')

        with open(last_log, 'r') as f:
            log_data = f.read()

        self._logfile = open(last_log, 'a')
        self._logfile.seek(len(log_data))

        self._index = index
        self.log_data = log_data

    def bind(self, callback):
        self._callback = callback

    def _open_next_file(self):
        self._logfile.close()
        self.log_data = ''
        log = f'log-{self._index}.log'
        log = os.path.join(Config.save_path, log)
        self._logfile = open(log, 'w')
        self._callback()

    def _archive_files(self):
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
            log = f'log-{i + 1}.log'
            log = os.path.join(Config.save_path, log)
            zf.write(log)
        zf.close()

        for i in range(Config.num_logfiles):
            log = f'log-{i + 1}.log'
            log = os.path.join(Config.save_path, log)
            os.remove(log)

        self._index = 1

    def write(self, value):
        if not value.strip():
            return

        self.log_data += value
        self._logfile.write(value)
        self._callback(value)
        if len(self.log_data) >= Config.max_logfile_size and value.endswith('\n'):
            self._index += 1
            if self._index > Config.num_logfiles:
                self._archive_files()

            self._open_next_file()

    def close(self):
        try:
            self._logfile.close()
        except:  # NOQA
            pass

    def flush(self):
        try:
            self._logfile.flush()
        except:  # NOQA
            pass


class Log(object):

    def __init__(self):
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

        # redirect all wxPython error messages to our log
        class MyLog(wx.Log):

            def DoLog(self, level, msg, _):  # NOQA

                if level >= 6:
                    return

                if Config.log_wx_error:
                    msg = _build_message(WX_ERROR, f'({level})  {msg}')
                    _stderr.write(msg)

        wx.Log.SetActiveTarget(MyLog())

        from ..import logger as _logger
        _logger.logger = self

    def flush(self):
        self.log_handler.flush()

    def print(self, *args, msg_type=INFO):
        msg = _build_message(msg_type, args)
        self.log_handler.write(msg)

    def info(self, *args):
        msg = _build_message(INFO, args)
        self.log_handler.write(msg)

    def debug(self, *args):
        if Config.log_debug:
            msg = _build_message(DEBUG, args)
            self.log_handler.write(msg)

    def notice(self, *args):
        if Config.log_notice:
            msg = _build_message(NOTICE, args)
            self.log_handler.write(msg)

    def warning(self, *args):
        if Config.log_warning:
            msg = _build_message(WARNING, args)
            self.log_handler.write(msg)

    def error(self, *args):
        if Config.log_error:
            msg = _build_message(ERROR, args)
            self.log_handler.write(msg)

    def traceback(self, exception, msg=None):
        if msg:
            self.error(msg)

        if Config.log_traceback:
            err = ''.join(traceback.format_exception(exception))

            args = err.rstrip().splitlines()
            msg = _build_message(TRACEBACK, args)
            self.log_handler.write(msg)

    def database(self, *args):
        if Config.log_database:
            msg = _build_message(DATABASE, args)
            self.log_handler.write(msg)
'''


import wx
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

    def _fake_callback(self, _=None):
        pass

    def __init__(self):
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
        self._callback = callback

    def get_current_log_path(self):
        """Return the path to the current log file"""
        return self._logfile_path

    def _open_next_file(self):
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
            data = df.to_csv(header=False, index=False) + '\n'
            self._logfile.write(data)

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
        # No file handle to close since we append per write
        pass

    def flush(self):
        # No buffering to flush
        pass


class Log(object):

    def __init__(self):
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

        # redirect all wxPython error messages to our log
        class MyLog(wx.Log):

            def DoLog(self, level, msg, _):  # NOQA

                if level >= 6:
                    return

                if Config.log_wx_error:
                    msg = msg.split('\n')

                    log_entry = build_message(WX_ERROR, (f'({level})  {msg[0]}',))
                    _stderr.write_log(log_entry)

                    for line in msg[1:]:
                        log_entry = build_message(WX_ERROR, (f'     {line}',))
                        _stderr.write_log(log_entry)

        wx.Log.SetActiveTarget(MyLog())

        from ..import logger as _logger
        _logger.logger = self

    def flush(self):
        self.log_handler.flush()

    def print(self, *args, msg_type=INFO):
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
        if Config.log_error:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(ERROR, line)
                        self.log_handler.write(log_entry)
                    args.remove(arg)

            if args:
                log_entry = build_message(ERROR, args)
                self.log_handler.write(log_entry)

    def traceback(self, exception, msg=None):
        if msg:
            self.error(msg)

        if Config.log_traceback:
            lines = traceback.format_exception(exception)

            for line in lines:
                line = line.rstrip()
                log_entry = build_message(TRACEBACK, line)
                self.log_handler.write(log_entry)

    def database(self, *args):
        if Config.log_database:
            args = list(args)

            for arg in args[:]:
                if isinstance(arg, str) and '\n' in arg:
                    for line in arg.split('\n'):
                        log_entry = build_message(DATABASE, line)
                        self.log_handler.write(log_entry)
                    args.remove(arg)

            if args:
                log_entry = build_message(DATABASE, args)
                self.log_handler.write(log_entry)
