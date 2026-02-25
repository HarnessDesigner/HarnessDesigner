
from typing import Iterable as _Iterable

from .import EntryBase, TableBase


from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal


class CavityPoints3DTable(TableBase):
    __table_name__ = 'cavity_points3d'

    def __iter__(self) -> _Iterable["CavityPoint3D"]:
        for db_id in TableBase.__iter__(self):
            yield CavityPoint3D(self, db_id)

    def __getitem__(self, item) -> "CavityPoint3D":
        if isinstance(item, int):
            if item in self:
                return CavityPoint3D(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: _decimal, y: _decimal) -> "CavityPoint3D":
        db_id = TableBase.insert(self, x=x, y=y)
        return CavityPoint3D(self, db_id)


class CavityPoint3D(EntryBase):
    _table: CavityPoints3DTable = None

    @property
    def point(self) -> _point.Point:
        return _point.Point(self.x, self.y, self.z)
    
    @property
    def x(self) -> _decimal:
        return _decimal(self._table.select('x', id=self._db_id)[0][0])

    @x.setter
    def x(self, value: _decimal):
        self._table.update(self._db_id, x=float(value))

    @property
    def y(self) -> _decimal:
        return _decimal(self._table.select('y', id=self._db_id)[0][0])

    @y.setter
    def y(self, value: _decimal):
        self._table.update(self._db_id, y=float(value))

    @property
    def z(self) -> _decimal:
        return _decimal(self._table.select('z', id=self._db_id)[0][0])

    @z.setter
    def z(self, value: _decimal):
        self._table.update(self._db_id, z=float(value))
