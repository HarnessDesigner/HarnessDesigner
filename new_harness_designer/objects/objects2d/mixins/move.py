

from ....geometry import point as _point
from ....geometry import line as _line
from ....wrappers.decimal import Decimal as _decimal


class MoveMixin:
    _parent = None
    _db_obj = None

    _position: _point.Point = None

    @property
    def position(self) -> _point.Point:
        return self._position


