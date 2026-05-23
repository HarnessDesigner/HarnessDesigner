# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Callback registration helpers for database-backed model objects."""

import weakref


class CallbackMixin:
    """Provide callback registration and dispatch support.
    """
    def __init__(self):
        """Initialize callback storage for the mixin instance.
        """
        self._callbacks = []

    def bind(self, callback, tag: str) -> "Callback":
        """Register a callback for a specific update tag.

        :param callback: Bound method to invoke for matching tags.
        :type callback: UNKNOWN
        :param tag: Tag that must match before the callback is invoked.
        :type tag: str

        :returns: The created callback wrapper.
        :rtype: Callback
        """
        cb_class = Callback(self, callback, tag)
        self._callbacks.append(cb_class)

    def unbind(self, cb_class: "Callback"):
        """Remove a previously registered callback wrapper.

        :param cb_class: UNKNOWN.
        :type cb_class: 'Callback'

        :returns: ``None``.
        :rtype: None
        """
        try:
            self._callbacks.remove(cb_class)
        except ValueError:
            pass

    def _populate(self, tag):
        """Notify registered callbacks that match the supplied tag.

        :param tag: Callback or message tag associated with the operation.
        :type tag: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        for cb in self._callbacks:
            cb(tag, self)


class Callback:

    """Represent a weakly referenced callback binding.
    """
    def __init__(self, parent: CallbackMixin, callback, tag):
        """Initialize the callback wrapper.

        :param parent: Parent :class:`CallbackMixin` that owns this wrapper.
        :type parent: CallbackMixin
        :param callback: Bound method stored through :class:`weakref.WeakMethod`.
        :type callback: UNKNOWN
        :param tag: Tag that must match before the callback runs.
        :type tag: UNKNOWN
        """
        self._parent = parent
        self.tag = tag
        self._ref = weakref.WeakMethod(callback, self._remove_ref)
        self._ref_count = 0

    def unbind(self):
        """Unregister this callback wrapper from its parent.

        :returns: ``None``.
        :rtype: None
        """
        self._parent.unbind(self)

    def _remove_ref(self, ref):
        """Remove this wrapper when the weak callback reference expires.

        :param ref: Weak reference callback argument supplied by :mod:`weakref`.
        :type ref: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        self._parent.unbind(self)

    def __enter__(self):
        """Mark the callback as actively executing within a context manager.

        :returns: ``None``.
        :rtype: None
        """
        self._ref_count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear the active execution marker for the callback.

        :param exc_type: Exception type passed by the context manager protocol.
        :type exc_type: UNKNOWN
        :param exc_val: Exception instance passed by the context manager protocol.
        :type exc_val: UNKNOWN
        :param exc_tb: Traceback object passed by the context manager protocol.
        :type exc_tb: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        self._ref_count -= 1

    def __call__(self, tag, entry):
        """Invoke the wrapped callback when the supplied tag matches.

        :param tag: Callback or message tag associated with the operation.
        :type tag: UNKNOWN
        :param entry: Entry object forwarded to the callback.
        :type entry: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        if self._ref_count:
            return

        if tag == self.tag:
            cb = self._ref()
            if cb is None:
                self._parent.unbind(self)
            else:
                cb(entry)
