import weakref


class SignalMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._callbacks = {'all': []}

    def _remove_ref(cls, ref):
        for id_, refs in list(cls._callbacks.items()):
            if ref in refs:
                refs.remove(ref)
                break

    def Bind(cls, callback, id: int | None = None) -> None:
        if id is None:
            id = 'all'

        if id not in cls._callbacks:
            cls._callbacks[id] = []

        cls._callbacks[id].append(weakref.ref(callback, cls._remove_ref))

    def Unbind(cls, callback, id: int | None = None) -> None:
        if id is None:
            id = 'all'

        if id not in cls._callbacks:
            return

        for ref in cls._callbacks[id][:]:
            cb = ref()
            if cb is None:
                cls._callbacks[id].remove(ref)
            elif cb == callback:
                cls._callbacks[id].remove(ref)
                return

    def __call__(cls, **kwargs):
        id = kwargs.get('id', 'all')  # NOQA

        def _do_callbacks(_id):
            for ref in cls._callbacks[_id][:]:
                cb = ref()
                if cb is None:
                    cls._callbacks[_id].remove(ref)
                else:
                    cb(**kwargs)

        _do_callbacks(id)
        if isinstance(id, int):
            _do_callbacks('all')


class Signal(metaclass=SignalMeta):

    def __init__(self, **kwargs):
        # this method never gets called, it is overridden by the
        # __call__ method in the metaclass
        pass

    def Bind(self, callback, id: int | None = None) -> None:
        # this method never gets called, it is overridden by the
        # Bind method in the metaclass
        pass

    def Unbind(self, callback, id: int | None = None) -> None:
        # this method never gets called, it is overridden by the
        # Unbind method in the metaclass
        pass


from .bundle import (  # NOQA
    SIGNAL_BUNDLE_SELECTED,
    SIGNAL_BUNDLE_P1_MOVED,
    SIGNAL_BUNDLE_P2_MOVED,
    SIGNAL_BUNDLE_LOADED,
    SIGNAL_BUNDLE_REMOVED,
    SIGNAL_BUNDLE_LAYOUT_NEW,
    SIGNAL_BUNDLE_LAYOUT_ADDED,
    SIGNAL_BUNDLE_LAYOUT_MOVED,
    SIGNAL_BUNDLE_LAYOUT_LOADED,
    SIGNAL_BUNDLE_LAYOUT_REMOVED,
    SIGNAL_BUNDLE_LAYOUT_SELECTED
)

from .connector import (  # NOQA
    SIGNAL_CONNECTOR_SELECTED,
    SIGNAL_CONNECTOR_MOVED,
    SIGNAL_CONNECTOR_ANGLE_CHANGED,
    SIGNAL_CONNECTOR_NEW,
    SIGNAL_CONNECTOR_ADDED,
    SIGNAL_CONNECTOR_LOADED
)

from .project import (  # NOQA
    SIGNAL_PROJECT_LOAD,
    SIGNAL_PROJECT_SAVE,
    SIGNAL_PROJECT_CLOSE,
    SIGNAL_PROJECT_LOADED
)

from .transition import (  # NOQA
    SIGNAL_TRANSITION_SELECTED,
    SIGNAL_TRANSITION_MOVED,
    SIGNAL_TRANSITION_ANGLE_CHANGED,
    SIGNAL_TRANSITION_NEW,
    SIGNAL_TRANSITION_ADDED,
    SIGNAL_TRANSITION_LOADED,
    SIGNAL_TRANSITION_REMOVED
)

from .wire import (  # NOQA
    SIGNAL_WIRE_SELECTED,
    SIGNAL_WIRE_P1_MOVED,
    SIGNAL_WIRE_P2_MOVED,
    SIGNAL_WIRE_REMOVED,
    SIGNAL_WIRE_ADDED,
    SIGNAL_WIRE_NEW,
    SIGNAL_WIRE_LOADED,
    SIGNAL_WIRE_LAYOUT_NEW,
    SIGNAL_WIRE_LAYOUT_ADDED,
    SIGNAL_WIRE_LAYOUT_MOVED,
    SIGNAL_WIRE_LAYOUT_LOADED,
    SIGNAL_WIRE_LAYOUT_REMOVED,
    SIGNAL_WIRE_LAYOUT_SELECTED
)
