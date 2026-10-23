# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import check_types as _check_types


_registering = None


@_check_types.do
def start_registration(instance):
    global _registering

    if _registering is not None:
        raise RuntimeError('plugin registration conflict')

    _registering = instance


class _PluginMeta(type):

    @_check_types.do
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        global _registering

        if _registering is None:
            raise RuntimeError

        cls._registration = _registering


class Plugin(metaclass=_PluginMeta):
    _registration = None

