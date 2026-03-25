from typing import TYPE_CHECKING
import time
import sys
import functools
import inspect

from . import config as _config

if TYPE_CHECKING:
    from . import logger as _logger


Config = _config.Config.debug.functions

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
        self._logger = logger.debug
        self._flush = logger.log_handler.flush

    def __call__(self, *args, end_stack=False):
        self._logger(*args)

        if end_stack:
            self._flush()


_print_func = DebugPrinter()


def logfunc(func):

    if True not in (Config.log_args, Config.log_duration):
        return func

    # there is a bug in Cython staticmethods when there is a second decorator
    # also on the same function and that function is called through the instance
    # of that class the instance ends up getting passed in the call. This adds
    # an additional positional argument shifting them all over by 1 which results
    # in a traceback occuring because the type is incorrect or there are too
    # many arguments being supplied to the function call.
    # Cython also has different types for functions and methods that are not
    # compatable with Pythons inspect module so we have to do a different check.
    # it appears that Cythons functions and methods hav things arranged differently
    # than Python does and it also has some additional atributes. staticmethods
    # do not have an attribute that functions and methods have and that attribute
    # is "func_name". Since the program is able to be compiled without Cython
    # being used we want to make sure that is still possible which can be seen
    # with the call to inspect in the exception catching.
    is_static_method = False

    try:
        func.__call__.__self__.func_name
    except AttributeError:
        if not inspect.isfunction(func):  # function
            is_static_method = True

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        global _stack_count

        if is_static_method:
            args = list(args[1:])

        if Config.log_args:
            args_ = ', '.join(repr(arg) for arg in args)
            kwargs_ = ', '.join(f'{key}={repr(value)}' for key, value in kwargs.items())
        else:
            args_ = ''
            kwargs_ = ''

        if _stack_count == 0:
            _print_func('START STACK')

        _stack_count += 1

        if Config.log_duration:
            start = time.perf_counter_ns()
            ret = func(*args, **kwargs)
            stop = time.perf_counter_ns()
            duration = (stop - start) / 1000000
        else:
            duration = 0
            ret = func(*args, **kwargs)

        _stack_count -= 1

        if Config.log_args:
            if Config.log_duration:
                _print_func(f'({duration}ms){func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')
            else:
                _print_func(f'{func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')

        elif Config.log_duration:
            _print_func(f'({duration}ms){func.__qualname__}')

        if _stack_count == 0:
            _print_func('END STACK', end_stack=True)

        return ret

    return _wrapper
