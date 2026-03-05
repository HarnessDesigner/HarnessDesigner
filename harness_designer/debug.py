from typing import TYPE_CHECKING
import time
import functools

from . import config as _config

if TYPE_CHECKING:

    from . import ui as _ui


Config = _config.Config


_stack_count = 0

_print_func = print


def logfunc(func):

    if Config.debug.bypass:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        global _print_func
        global _stack_count

        if _print_func == print:
            from .ui import mainframe

            if mainframe._mainframe is not None:  # NOQA
                _print_func = mainframe._mainframe.logger.print_debug  # NOQA

        if Config.debug.log_args:
            args_ = ', '.join(repr(arg) for arg in args)
            kwargs_ = ', '.join(f'{key}={repr(value)}' for key, value in kwargs.items())

        if _stack_count == 0:
            _print_func('\n', 'START STACK')

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
                _print_func('END STACK', '\n')

        elif Config.debug.call_duration:
            _print_func(f'({duration}ms){func.__qualname__}')

            if _stack_count == 0:
                _print_func('END STACK\n\n')

        return ret

    return _wrapper
