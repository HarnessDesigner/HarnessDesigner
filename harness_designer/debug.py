from typing import TYPE_CHECKING
import time
import sys
import functools

from . import config as _config

if TYPE_CHECKING:
    from . import logger as _logger
    from . import ui as _ui


Config = _config.Config


_stack_count = 0

class DebugPrinter:

    def __init__(self):

        def log_printer(*args):
            from .ui import mainframe

            if mainframe._mainframe is not None:  # NOQA
                self.set_logger(mainframe._mainframe.logger)  # NOQA

            print(*args)

        self._logger = log_printer
        self._flush = sys.stdout.flush

    def set_logger(self, logger: "_logger.Log"):
        self._logger = logger.print_debug
        self._flush = logger.log_handler.flush

    def __call__(self, *args, end_stack=False):
        self._logger(*args)

        if end_stack:
            self._flush()


_print_func = DebugPrinter()


def logfunc(func):

    if Config.debug.bypass:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        global _stack_count

        if Config.debug.log_args:
            args_ = ', '.join(repr(arg) for arg in args)
            kwargs_ = ', '.join(f'{key}={repr(value)}' for key, value in kwargs.items())

        if _stack_count == 0:
            _print_func('START STACK')

        _stack_count += 1

        if Config.debug.call_duration:
            start = time.perf_counter_ns()
            ret = func(*args, **kwargs)
            stop = time.perf_counter_ns()
            duration = (stop - start) / 1000000

        else:
            ret = func(*args, **kwargs)

        _stack_count -= 1

        if Config.debug.log_args:
            if Config.debug.call_duration:
                _print_func(f'({duration}ms){func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')
            else:
                _print_func(f'{func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')

            if _stack_count == 0:
                _print_func('END STACK', end_stack=True)

        elif Config.debug.call_duration:
            _print_func(f'({duration}ms){func.__qualname__}')

            if _stack_count == 0:
                _print_func('END STACK', end_stack=True)

        return ret

    return _wrapper
