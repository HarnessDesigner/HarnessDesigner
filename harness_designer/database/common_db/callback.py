import weakref


class CallbackMixin:
    def __init__(self):
        self._callbacks = []

    def bind(self, callback, tag: str) -> "Callback":
        cb_class = Callback(self, callback, tag)
        self._callbacks.append(cb_class)

    def unbind(self, cb_class: "Callback"):
        try:
            self._callbacks.remove(cb_class)
        except ValueError:
            pass

    def _populate(self, tag):
        for cb in self._callbacks:
            cb(tag, self)


class Callback:

    def __init__(self, parent: CallbackMixin, callback, tag):
        self._parent = parent
        self.tag = tag
        self._ref = weakref.WeakMethod(callback, self._remove_ref)
        self._ref_count = 0

    def unbind(self):
        self._parent.unbind(self)

    def _remove_ref(self, ref):
        self._parent.unbind(self)

    def __enter__(self):
        self._ref_count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def __call__(self, tag, entry):
        if self._ref_count:
            return

        if tag == self.tag:
            cb = self._ref()
            if cb is None:
                self._parent.unbind(self)
            else:
                cb(entry)
