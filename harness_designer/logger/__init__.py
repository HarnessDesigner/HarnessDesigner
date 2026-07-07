# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Public logger exports for :mod:`harness_designer.logger`."""

from typing import TYPE_CHECKING

from . import log_handler as _log_handler

Log = _log_handler.Log
LogHandler = _log_handler.LogHandler


class DynamicLogLoader:

    def __init__(self):
        import sys

        mod = sys.modules[__name__]

        self.__cached__ = mod.__cached__
        self.__doc__ = mod.__doc__
        self.__file__ = mod.__file__
        self.__loader__ = mod.__loader__
        self.__name__ = mod.__name__
        self.__package__ = mod.__package__
        self.__spec__ = mod.__spec__

        self.__original_module__ = mod
        self.__logger = Log()

        sys.modules[__name__] = self

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if hasattr(self.__logger, item):
            return getattr(self.__logger, item)

        return getattr(self.__original_module__, item)


__log = DynamicLogLoader()


if TYPE_CHECKING:

    log_handler: LogHandler = None

    def startup():
        pass

    def flush():
        pass

    def print(*args, msg_type=_log_handler.INFO):
        pass

    def print_block(*args, msg_type=_log_handler.INFO):
        pass

    def info(*args):
        pass

    def info_block(*args):
        pass

    def debug(*args):
        pass

    def debug_block(*args):
        pass

    def notice(*args):
        pass

    def notice_block(*args):
        pass

    def warning(*args):
        pass

    def warning_block(*args):
        pass

    def error(*args):
        pass

    def error_block(*args):
        pass

    def traceback(exception, msg=None):
        pass

    def database(*args):
        pass

    def database_block(*args):
        pass

