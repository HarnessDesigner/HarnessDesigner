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

_message_mapping = {
    INFO: 'INFO:',
    NOTICE: 'NOTICE:',
    WARNING: 'WARNING:',
    DEBUG: 'DEBUG:',
    TRACEBACK: 'TRACEBACK:',
    ERROR: 'ERROR:',
    WX_ERROR: 'WX_ERROR:'
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

        self.print_info('----------------------------------------')
        self.print_info('        Harness Designer started')
        self.print_info('----------------------------------------')
        self.print_info('')
        self.print_info('Harness Designer Version:', __version__.string)
        self.print_info('\n')
        self.print_info('--------------    GL     ---------------')

        data = _gl_info.get()
        for header, items in data.items():

            if isinstance(items, dict):
                pre_suf_count = int((40 - (len(header) + 4)) / 2)

                pre_suf = '=' * pre_suf_count

                header = f'{pre_suf}  {header}  '

                if pre_suf_count % 2:
                    pre_suf = f' {pre_suf}'

                self.print_info(header + pre_suf)

                for label, value in items.items():
                    self.print_info(f'{label}:', value)

                self.print_info('\n')
            else:
                self.print_info(f'{header}:', items)
        self.print_info('\n', '----------------------------------------', '\n')

        self.print_info('--------------  Machine  ---------------', '\n')
        self.print_info('Machine type:', platform.machine())
        self.print_info('Processor:', platform.processor())
        self.print_info('Architecture:', platform.architecture())
        self.print_info(
            'Python:',
            platform.python_branch(),
            platform.python_version(),
            platform.python_implementation(),
            platform.python_build(),
            f'[{platform.python_compiler()}]'
        )
        self.print_info('\n', '----------------------------------------', '\n')

        # redirect all wxPython error messages to our log
        class MyLog(wx.Log):

            def DoLog(self, level, msg, _):  # NOQA

                if level >= 6:
                    return

                msg = _build_message(WX_ERROR, f'({level})  {msg}')
                _stderr.write(msg)

        wx.Log.SetActiveTarget(MyLog())

        from ..import logger as _logger
        _logger.logger = self

    def print(self, *args, msg_type=INFO):
        msg = _build_message(msg_type, args)
        self.log_handler.write(msg)

    def print_info(self, *args):
        msg = _build_message(INFO, args)
        self.log_handler.write(msg)

    def print_debug(self, *args):
        msg = _build_message(DEBUG, args)
        self.log_handler.write(msg)

    def print_notice(self, *args):
        msg = _build_message(NOTICE, args)
        self.log_handler.write(msg)

    def print_warning(self, *args):
        msg = _build_message(WARNING, args)
        self.log_handler.write(msg)

    def print_error(self, *args):
        msg = _build_message(ERROR, args)
        self.log_handler.write(msg)

    def print_traceback(self, exception, msg=None):
        if msg:
            self.print_error(msg)

        err = ''.join(traceback.format_exception(exception))

        args = err.rstrip().splitlines()
        msg = _build_message(TRACEBACK, args)
        self.log_handler.write(msg)
