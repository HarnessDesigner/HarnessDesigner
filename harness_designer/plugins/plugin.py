# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

_registering = None


def start_registration(instance):
    global _registering

    if _registering is not None:
        raise RuntimeError('plugin registration conflict')

    _registering = instance


class _PluginMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        global _registering

        if _registering is None:
            raise RuntimeError

        cls._registration = _registering


class Plugin(metaclass=_PluginMeta):
    _registration = None

