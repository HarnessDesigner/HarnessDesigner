# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Ensures OCP is only ever accessed from a single, dedicated thread.

OCP is not built/marked as free-threading-safe, so every actual call
into it -- across the whole application -- is funneled through one
worker thread (started here, at import time) via the ``ocp_thread``
decorator. Callers on any other thread block until their submitted work
has run and get the return value (or a re-raised exception) back.

Example use::

    from .ocp_threadworker import ocp_thread as _ocp_thread


    @_ocp_thread
    def func_with_ocp_calls(param1, param2):
        import OCP

        # do ocp code here using the params given
        # NOTE: OCP objects can be returned from this function to be
        #       used in local storage, but if any operations need to be
        #       performed on that object it must be done like what is
        #       seen with this function -- i.e. via another @ocp_thread
        #       function, never directly from an arbitrary thread.


    some_result = func_with_ocp_calls('some arg', param2='some kwarg')
"""

# TODO: I have successfully gotten OCP to compile for all 3 platforms for
#       free threaded python (3.14t). This is a huge deal in terms of
#       performnace but it will require a lot of planning in order to bump the
#       python version being used to 3.14t. This code represents only the start
#       of that work and this work was done to validate being able to use multiple
#       threads when accessing some portions of OCP.

import queue
import threading


class OCPThreadTask:

    def __init__(self, func, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._exception = None
        self._lock = threading.Lock()
        self._lock.acquire()
        self._result = None

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def __call__(self):
        try:
            self._result = self._func(*self._args, **self._kwargs)
        except Exception as err:
            self._exception = err

        self._lock.release()

    @property
    def result(self):
        return self._result

    @property
    def exception(self):
        return self._exception


class _OCPThreadWorker(threading.Thread):

    def __init__(self):
        super().__init__(name='OCP Access Thread')
        self.daemon = True
        self._queue = queue.Queue()
        self._exit_event = threading.Event()

    def add(self, func, *args, **kwargs):
        worker = OCPThreadTask(func, *args, **kwargs)
        self._queue.put_nowait(worker)

        with worker:
            pass

        if worker.exception is not None:
            raise worker.exception

        return worker.result

    def run(self):
        while not self._exit_event.is_set():
            worker = self._queue.get(True)
            if worker is not None:
                worker()

    def stop(self):
        self._exit_event.set()
        self._queue.put(None)

        self.join(20.0)
        if self.is_alive():
            raise RuntimeError('could not stop OCP access thread')


OCPThreadWorker = _OCPThreadWorker()
OCPThreadWorker.start()


def ocp_thread(func):

    def _wrapper(*args, **kwargs):
        res = OCPThreadWorker.add(func, *args, **kwargs)
        return res

    return _wrapper
