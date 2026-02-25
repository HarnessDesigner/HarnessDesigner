
import time
import functools

from . import config as _config


Config = _config.Config


class _DebugTimer:

    def __init__(self):
        self._timer_running = False
        self._timer_stack = []
        self._print_stack = []

    def start_new_timer(self):
        self._timer_stack.append(time.perf_counter_ns())

    def stop_timer(self):
        stop = time.perf_counter_ns()
        start = self._timer_stack.pop(-1)
        return (stop - start) / 1000000

    def __enter__(self):
        self._print_stack.append(time.perf_counter_ns())

    def __exit__(self, exc_type, exc_val, exc_tb):
        strt = time.perf_counter_ns()
        stop = strt
        start = self._print_stack.pop(-1)
        diff = stop - start

        for i in range(len(self._timer_stack)):
            self._timer_stack[i] += diff

        stop = time.perf_counter_ns()
        diff = (stop - strt) * 2

        for i in range(len(self._timer_stack)):
            self._timer_stack[i] += diff


_debug_timer = _DebugTimer()


def logfunc(func):

    if Config.debug.bypass:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if Config.debug.log_args:
            with _debug_timer:
                args_ = ', '.join(repr(arg) for arg in args)
                kwargs_ = ', '.join(f'{key}={repr(value)}' for key, value in kwargs.items())

        if Config.debug.call_duration:
            _debug_timer.start_new_timer()
            ret = func(*args, **kwargs)
            duration = _debug_timer.stop_timer()
        else:
            ret = func(*args, **kwargs)

        if Config.debug.log_args:
            if Config.debug.call_duration:
                with _debug_timer:
                    print(f'({duration}ms){func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')
            else:
                print(f'{func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')
        elif Config.debug.call_duration:
            with _debug_timer:
                print(f'({duration}ms){func.__qualname__}')

        return ret

    return _wrapper
