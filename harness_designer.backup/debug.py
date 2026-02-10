import time
import functools


class Config:
    function_time = True


def logger(func):

    if not Config.debug.log_args and not Config.debug.call_duration:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if Config.debug.log_args:
            args_ = ', '.join(repr(arg) for arg in args)
            kwargs_ = ', '.join(f'{key}={repr(value)}' for key, value in kwargs.items())

        if Config.debug.call_duration:
            start = time.perf_counter_ns()
            ret = func(*args, **kwargs)
            stop = time.perf_counter_ns()
        else:
            ret = func(*args, **kwargs)

        if Config.debug.log_args:
            if Config.debug.call_duration:
                print(f'({(stop - start) / 1000000, 2}ms){func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')
            else:
                print(f'{func.__qualname__}({", ".join(item for item in [args_, kwargs_] if item)}) --> {repr(ret)}')

        return ret

    return _wrapper
