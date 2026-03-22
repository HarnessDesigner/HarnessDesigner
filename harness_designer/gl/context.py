
import threading

from wx import glcanvas


class GLContext:

    def __init__(self, canvas: glcanvas.GLCanvas):
        self.canvas = canvas
        self.context = glcanvas.GLContext(canvas)
        self._lock = threading.RLock()
        self._refs_lock = threading.Lock()
        self._refs = {}
        self._refs_order = []

    @property
    def is_locked(self):
        cur_thread = threading.current_thread()

        with self._refs_lock:
            if not self._refs_order:
                return False

            if self._refs_order[0] == cur_thread:
                return False

            return True

    def acquire(self):
        cur_thread = threading.current_thread()

        with self._refs_lock:
            if cur_thread not in self._refs:
                self._refs[cur_thread] = 0
                self._refs_order.append(cur_thread)

            self._refs[cur_thread] += 1

        self._lock.acquire()
        self.canvas.SetCurrent(self.context)

    def release(self):
        self._lock.release()
        cur_thread = threading.current_thread()

        with self._refs_lock:
            self._refs[cur_thread] -= 1

            if self._refs[cur_thread] == 0:
                del self._refs[cur_thread]
                self._refs_order.remove(cur_thread)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
