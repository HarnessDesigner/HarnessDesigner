from typing import Iterable as _Iterable

import uuid

from . import PJTEntryBase, PJTTableBase

from ...wrappers.decimal import Decimal as _decimal
from ...geometry import point as _point


class PJTPoints3DTable(PJTTableBase):
    __table_name__ = 'pjt_points3d'

    def __iter__(self) -> _Iterable["PJTPoint3D"]:
        for db_id in PJTTableBase.__iter__(self):
                point = PJTPoint3D(self, db_id, self.project_id)
                yield point

    def __getitem__(self, item) -> "PJTPoint3D":
        if isinstance(item, int):
            if item in self:
                return PJTPoint3D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: _decimal, y: _decimal, z: _decimal) -> "PJTPoint3D":
        db_id = PJTTableBase.insert(self, x=float(x), y=float(y), z=float(z))
        return PJTPoint3D(self, db_id, self.project_id)


class PJTPoint3D(PJTEntryBase):
    _table: PJTPoints3DTable = None
    _point_id: str = None

    @property
    def table(self) -> PJTPoints3DTable:
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
    def z(self) -> _decimal:
        return _decimal(self._table.select('z', id=self._db_id)[0][0])

    @z.setter
    def z(self, value: _decimal):
        self._table.update(self._db_id, z=float(value))
        self._process_callbacks()

    def _update_point(self, point: _point.Point):
        x, y, z = point.as_float
        self._table.update(self._db_id, x=x, y=y, z=z)
        self._process_callbacks()

    @property
    def point(self) -> _point.Point:
        if self._point_id is None:
            self._point_id = str(uuid.uuid4())

        point = _point.Point(self.x, self.y, self.z, db_id=self._point_id)
        point.bind(self._update_point)

        return point
