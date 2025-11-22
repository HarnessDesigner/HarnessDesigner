from . import utils
from . database import config_db


class Config(type):
    __db__ = config_db.ConfigDB(utils.get_appdata())
    __classes__ = []

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        Config.__classes__.append(cls)

    def _save(cls):
        for key in dir(cls):
            if key.startswith('_'):
                continue

            value = getattr(cls, key)
            if callable(value):
                continue

            cls.__table__[key] = value

    @property
    def __table_name__(cls):
        name = f'{cls.__module__.split(".", 1)[-1]}_{cls.__qualname__}'
        return name.replace(".", "_")

    @property
    def __table__(cls):
        return Config.__db__[cls.__table_name__]

    def __getitem__(cls, item):
        return getattr(cls, item)

    def __getattribute__(cls, item):
        if item.startswith('_'):
            return type.__getattribute__(cls, item)

        value = type.__getattribute__(cls, item)
        if callable(value):
            return value

        if item in cls.__table__:
            return cls.__table__[item]

        return value

    def __setitem__(cls, key, value):
        setattr(cls, key, value)

    def __setattr__(cls, key, value):
        type.__setattr__(cls, key, value)

        if not key.startswith('_'):
            cls.__table__[key] = value

    def __delitem__(cls, key):
        delattr(cls, key)

    def __delattr__(cls, item):
        if item in cls.__table__:
            del cls.__table__[item]

        type.__delattr__(cls, item)

    @staticmethod
    def close():
        for cls in Config.__classes__:
            cls._save()

        Config.__db__.close()
