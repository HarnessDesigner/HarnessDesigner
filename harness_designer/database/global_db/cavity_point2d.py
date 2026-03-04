from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase


from ...geometry import point as _point


class CavityPoints2DTable(TableBase):
    __table_name__ = 'cavity_points2d'

    def __iter__(self) -> _Iterable["CavityPoint2D"]:
        for db_id in TableBase.__iter__(self):
            yield CavityPoint2D(self, db_id)

    def __getitem__(self, item) -> "CavityPoint2D":
        if isinstance(item, int):
            if item in self:
                return CavityPoint2D(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: float, y: float) -> "CavityPoint2D":
        db_id = TableBase.insert(self, x=x, y=y)
        return CavityPoint2D(self, db_id)


class CavityPoint2D(EntryBase):
    _table: CavityPoints2DTable = None

    @property
    def point(self) -> _point.Point:
        return _point.Point(self.x, self.y, None)

    @property
    def x(self) -> float:
        return self._table.select('x', id=self._db_id)[0][0]

    @x.setter
    def x(self, value: float):
        self._table.update(self._db_id, x=value)

    @property
    def y(self) -> float:
        return self._table.select('y', id=self._db_id)[0][0]

    @y.setter
    def y(self, value: float):
        self._table.update(self._db_id, y=value)
