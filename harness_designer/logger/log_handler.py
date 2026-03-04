import codecs
import sys
import wx
from traceback import extract_tb, format_exception_only
import platform
from .. import config as _config
import datetime
import zipfile
import os


from .. import __version__
from . import stdout
from . import stderr


def _build_message(msg_type, args):
    strs = []

    for arg in args:
        arg = str(arg).strip()

        if msg_type == 'WARNING':

            arg = arg.replace('Traceback', 'Warning')

        strs += [arg]

    msg = ' '.join(strs)

    if msg_type == 'DEBUG':
        msg = 'DEBUG: ' + msg.replace('\n', '\nDEBUG: ')

    elif msg_type == 'NOTICE':
        msg = 'NOTICE: ' + msg.replace('\n', '\nNOTICE: ')

    elif msg_type == 'INFO':
        msg = 'INFO: ' + msg.replace('\n', '\nINFO: ')

    elif msg_type == 'WARNING':
        msg = 'WARNING: ' + msg.replace('\n', '\nWARNING: ')

    timestamp = datetime.datetime.now()
    timestamp = timestamp.strftime('(%m.%d.%Y-%H:%M:%S)')

    std_msg = timestamp + msg.replace('\n', '\n' + timestamp) + '\n'

    return std_msg


Config = _config.Config.logging


class LogHandler:

    def _fake_callback(self, _=None):
        pass

    def __init__(self):
        self._callback = self._fake_callback

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

        self._logfile = open(last_log, 'w')
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
        self.log_data += value
        self._logfile.write(value)
        self._callback(value)
        if len(self.log_data) >= Config.max_logfile_size and value.endswith('\n'):
            self._index += 1
            if self._index > Config.num_logfiles:
                self._archive_files()

            self._open_next_file()


class Log(object):

    def __init__(self):
        self.log_handler = LogHandler()

        self.__stdout = stdout.StdOut(self)
        self.__stderr = _stderr = stderr.StdErr(self)

        self.print_notice("----------------------------------------")
        self.print_notice("        Harness Designer started")
        self.print_notice("----------------------------------------")
        self.print_notice('Harness Designer', "Version:", __version__.string)
        self.print_notice("Machine type:", platform.machine())
        self.print_notice("Processor:", platform.processor())
        self.print_notice("Architecture:", platform.architecture())
        self.print_notice(
            "Python:",
            platform.python_branch(),
            platform.python_version(),
            platform.python_implementation(),
            platform.python_build(),
            "[{0}]".format(platform.python_compiler())
        )
        self.print_notice("----------------------------------------")

        # redirect all wxPython error messages to our log
        class MyLog(wx.Log):

            def DoLog(self, level, msg, _):  # NOQA

                if level >= 6:
                    return

                _stderr.write("wxError%d: %s\n" % (level, msg))

        wx.Log.SetActiveTarget(MyLog())

    def print(self, *args, msg_type='INFO'):
        msg = _build_message(msg_type, args)
        self.log_handler.write(msg)

    def print_notice(self, *args):
        msg = _build_message('NOTICE', args)
        self.log_handler.write(msg)

    def print_warning(self, *args):
        msg = _build_message('WARNING', args)
        self.log_handler.write(msg)

    def print_error(self, *args):
        """
        Prints an error message to the logger. The message will get a special
        icon and a red colour, so the user can easily identify it as an error
        message.
        """
        msg = _build_message('ERROR', args)
        self.log_handler.write(msg)

    def print_traceback(self, msg=None, skip=0, excInfo=None):
        if msg:
            self.print_error(msg)

        if excInfo is None:
            excInfo = sys.exc_info()

        tbType, tbValue, tbTraceback = excInfo

        slist = [
            'Traceback (most recent call last) ({__version__.string}):\n'
        ]

        decode = codecs.getdecoder('utf-8')

        if tbTraceback:
            for fname, lno, funcName, text in extract_tb(tbTraceback)[skip:]:
                slist.append(f'  File "{decode(fname)[0]}", line {lno}, in {funcName}\n')
                if text:
                    slist.append(f"    {text}\n")

        for line in format_exception_only(tbType, tbValue):
            slist.append(decode(line)[0])

        error = "".join(slist)

        args = error.rstrip().split('\n')
        msg = _build_message('ERROR', args)
        self.log_handler.write(msg)
