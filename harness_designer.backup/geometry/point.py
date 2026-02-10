from typing import Self, Callable, Iterable, Union
import weakref

import sys

from ..wrappers.decimal import Decimal as _decimal
from wxOpenGL.geometry import point as _point


class PointMeta(type):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, x: _decimal, y: _decimal, z: _decimal | None = None,
                 db_id: int | None = None):

        if db_id is not None:
            if db_id not in cls._instances:
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)

            elif cls._instances[db_id]() is None:
                # Handle edge case where a reference has been removed
                # but the reference object has not yet been removed from
                # the dict. We have to make sure that we delete the key
                # before adding the object again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)
            else:
                instance = cls._instances[db_id]()
        else:
            instance = super().__call__(x, y, z, db_id)

        return instance


class Point(_point.Point, metaclass=PointMeta):

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None, 
                 db_id: int | None = None):

        self.db_id = db_id

        super().__init__(x, y, z)


ZERO_POINT = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))


__original_point__ = _point.Point

_point.Point = Point

sys.modules['wxOpenGL.geometry.point'].Point = Point
