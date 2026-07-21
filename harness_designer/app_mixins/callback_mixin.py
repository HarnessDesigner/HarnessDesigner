# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import weakref


class CallbackMixin:

    # these need to be explicitly set in the child classes __init__ function
    __callbacks__: list = []
    __unbound_callbacks__: list = []
    __ref_count__: int = 0

    def __enter__(self):
        """
        Begin a batched update.

        Increments the internal ref-count guard so that individual setter calls
        and in-place operators do NOT fire callbacks while the
        context is active.  This lets you update all components as a
        single logical move without triggering recalculations

        The caller must trigger ``_process_update()`` explicitly after the
        block if the change should propagate, OR use a final setter outside
        the block which will fire ``_process_update()`` normally.

        Note: the context manager does NOT automatically fire callbacks on
        exit.  This is intentional — some callers (e.g. the transition 3D
        object's __init__) need to update points without triggering redraws
        until the entire object is ready.
        """

        self.__ref_count__ += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Decrement the ref-count guard.  See __enter__."""

        self.__ref_count__ -= 1

    def _remove_cb(self, ref):
        """
        Drop a dead callback weak reference from the callback list.

        :param ref: Weak method reference scheduled for removal.
        :type ref: :class:`weakref.WeakMethod`
        :returns: ``None``
        :rtype: None
        """

        try:
            self.__callbacks__.remove(ref)
        except:  # NOQA
            pass

    def bind(self, callback):
        """
        Register a callback to be called whenever this Point's coordinates
        change.

        The callback receives the Point instance as its only argument.
        Internally it is stored as a ``WeakMethod`` so that binding a bound
        method does not prevent the owning object from being garbage-collected.
        When the owning object is collected the dead weakref is silently
        removed from the callback list during the next ``_process_update()``.

        Duplicate registrations are tolerated — the first duplicate found
        during ``_process_update()`` is removed so each unique callback fires
        at most once per update cycle.

        IMPORTANT — objects must bind their callbacks at the same time they
        acquire a reference to the Point (i.e. in the ORM mixin property
        accessor after calling ``add_object``).  If a callback is never bound,
        the object will not respond to position changes even though it holds a
        reference to the shared Point.
        """

        # we don't explicitly check to see if a callback is already registered
        # what we care about is if a callback is called only one time and that
        # check is done when the callbacks are being done and if there happend
        # to be a duplicate the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(callback, self._remove_cb)

        self.__callbacks__.append(ref)

    def unbind(self, callback):
        """
        Remove a previously registered callback.

        Iterates the full callback list removing ALL registrations of the
        given callback, including any duplicates.  This is intentional: if a
        callback was accidentally bound more than once, a single unbind call
        removes all copies.

        IMPORTANT — when an object is deleted or its connection to this Point
        is severed (e.g. a wire endpoint is reassigned to a different point_id),
        unbind should be called to avoid the callback firing for a Point the
        object no longer owns.  Failure to unbind is not fatal — the WeakMethod
        will eventually be collected — but it can cause spurious updates while
        the owning object still exists.
        """

        ref = weakref.WeakMethod(callback)
        if ref in self.__callbacks__:
            while ref in self.__callbacks__:
                self.__callbacks__.remove(ref)
        else:
            self.__unbound_callbacks__.append(callback)

        for ref in self.__callbacks__[:]:
            cb = ref()
            if cb is None:
                while ref in self.__callbacks__:
                    self.__callbacks__.remove(ref)

    def _process_callbacks(self):
        """
        Fire all registered callbacks, unless batching is active.

        If ``__ref_count__`` is non-zero (i.e. the caller is inside a ``with
        point:`` block) this method returns immediately without firing
        anything.  This is the mechanism that allows multiple coordinate
        components to be updated atomically.

        Dead weakrefs (callbacks whose owning object has been collected) are
        silently pruned during iteration.  Duplicate callbacks are detected
        and removed — each unique callback fires at most once per update cycle
        even if it was registered more than once.

        There are suitations where a reference can be deleted as the result
        if a callback being called. This had to be managed in a very special way
        in order to keep from getting errors. The biggest issue is that you
        cannot do a comparison between 2 weak reference objects reliably.
        This is due to the mechanics in the weakref where if the referant exists
        it will use that for the comparison instead of the actual weakref object
        """

        if self.__ref_count__:
            return

        del self.__unbound_callbacks__[:]
        used_callbacks = []
        callbacks = self.__callbacks__[:]
        del self.__callbacks__[:]

        for ref in callbacks:
            if ref in used_callbacks:
                continue
            cb = ref()
            if cb is None:
                continue
            cb(self)
            used_callbacks.append(ref)

        for ref in self.__callbacks__[:]:
            cb = ref()
            if cb is None:
                self.__callbacks__.remove(ref)
            elif cb in self.__unbound_callbacks__:
                self.__unbound_callbacks__.remove(cb)

        self.__callbacks__.extend([ref for ref in used_callbacks
                                   if ref() is not None
                                   and ref not in self.__callbacks__
                                   and ref() not in self.__unbound_callbacks__])

        del self.__unbound_callbacks__[:]
