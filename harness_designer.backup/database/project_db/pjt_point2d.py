from typing import Iterable as _Iterable

import uuid

from . import PJTEntryBase, PJTTableBase

from ...wrappers.decimal import Decimal as _decimal
from ...geometry import point as _point


class PJTPoints2DTable(PJTTableBase):
    __table_name__ = 'pjt_points2d'

    def __iter__(self) -> _Iterable["PJTPoint2D"]:

        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint2D(self, db_id, self.project_id)
            yield point

    def __getitem__(self, item) -> "PJTPoint2D":
        if isinstance(item, int):
            if item in self:
                return PJTPoint2D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: float, y: float) -> "PJTPoint2D":
        db_id = PJTTableBase.insert(self, x=x, y=y)
        return PJTPoint2D(self, db_id, self.project_id)


class PJTPoint2D(PJTEntryBase):
    _table: PJTPoints2DTable = None
    _point_id: str = None

    @property
    def table(self) -> PJTPoints2DTable:
        return self._table

    @property
    def x(self) -> _decimal:
        return _decimal(self._table.select('x', id=self._db_id)[0][0])

    @x.setter
    def x(self, value: _decimal):
        self._table.update(self._db_id, x=float(value))
        self._process_callbacks()

    @property
    def y(self) -> _decimal:
        return _decimal(self._table.select('y', id=self._db_id)[0][0])

    @y.setter
    def y(self, value: _decimal):
        self._table.update(self._db_id, y=float(value))
        self._process_callbacks()

    @property
    def point(self) -> _point.Point:
        if self._point_id is None:
            self._point_id = str(uuid.uuid4())

        point = _point.Point(self.x, self.y, db_id=self._point_id)
        point.bind(self._update_point)
        return point

    def _update_point(self, point: _point.Point):
        x, y, z = point.as_float
        self._table.update(self._db_id, x=x, y=y)
        self._process_callbacks()
