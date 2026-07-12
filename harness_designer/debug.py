# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Debug logging helpers and decorators for :mod:`harness_designer`."""

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
    """Route debug output either to stdout or the application logger."""

    def __init__(self):
        """Initialise the fallback debug printer.

        """

        def log_printer(*args):
            """Print debug output until a logger becomes available.

            :param args: Positional values to print.
            :type args: tuple
            """
            from .ui import mainframe

            if mainframe._mainframe is not None:  # NOQA
                self.set_logger(mainframe._mainframe.logger)  # NOQA

            print(*args)

        self._logger = log_printer
        self._flush = sys.stdout.flush

    def set_logger(self, logger: "_logger.Log"):
        """Send future debug output to the application logger.

        :param logger: Logger instance that exposes ``debug`` and ``log_handler``.
        :type logger: _logger.Log
        """
        self._logger = logger.debug
        self._flush = logger.log_handler.flush

    def __call__(self, *args, end_stack=False):
        """Emit debug output.

        :param args: Message parts forwarded to the current sink.
        :type args: tuple
        :param end_stack: Flush after logging when ending a stack trace block.
        :type end_stack: bool
        """
        self._logger(*args)

        if end_stack:
            self._flush()


_print_func = DebugPrinter()


def logfunc(func):
    """Decorate a callable to log arguments and/or duration.

    :param func: Callable to wrap.
    :type func: collections.abc.Callable
    :returns: Either the original callable or a wrapped logging proxy.
    :rtype: collections.abc.Callable
    """

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
        func.__call__.__self__.func_name  # NOQA
    except AttributeError:
        if not inspect.isfunction(func):  # function
            is_static_method = True

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        """Invoke ``func`` while collecting configured debug output.

        :param args: Positional arguments for ``func``.
        :type args: tuple
        :param kwargs: Keyword arguments for ``func``.
        :type kwargs: dict
        :returns: Return value from ``func``.
        :rtype: UNKNOWN
        """
        global _stack_count
        nonlocal is_static_method

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
