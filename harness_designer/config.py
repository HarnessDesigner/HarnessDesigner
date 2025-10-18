from . import utils
from . database import config_db


class Config(type):
    __db__ = config_db.ConfigDB(utils.get_appdata())

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

        if item in cls.__table__:
            return cls.__table__[item]

        return type.__getattribute__(cls, item)

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
        Config.__db__.close()
