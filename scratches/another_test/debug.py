import time
import functools


class Config:
    function_time = True


# decorator function to tine how long functions take to run.
def timeit(func):

    if not Config.function_time:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        start_time = time.time()
        res = func(*args, **kwargs)
        end_time = time.time()
        print(f'{func.__qualname__}: {round((end_time - start_time) * 1000, 2)}ms')
        return res

    return _wrapper
