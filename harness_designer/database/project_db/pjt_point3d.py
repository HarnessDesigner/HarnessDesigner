from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase

from ...geometry import point as _point


class PJTPoints3DTable(PJTTableBase):
    __table_name__ = 'pjt_points3d'

    def _table_needs_update(self) -> bool:
        from ..create_database import points3d

        return points3d.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import points3d

        points3d.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import points3d

        points3d.pjt_table.update_fields(self)

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

    def insert(self, x: float, y: float, z: float) -> "PJTPoint3D":
        db_id = PJTTableBase.insert(self, x=x, y=y, z=z)
        return PJTPoint3D(self, db_id, self.project_id)


class PJTPoint3D(PJTEntryBase):
    _table: PJTPoints3DTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_points3d': [self.db_id],
        }

        return packet

    @property
    def table(self) -> PJTPoints3DTable:
        return self._table

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

    @property
    def z(self) -> float:
        return self._table.select('z', id=self._db_id)[0][0]

    @z.setter
    def z(self, value: float):
        self._table.update(self._db_id, z=value)

    def _update_point(self, point: _point.Point):
        x, y, z = point.as_float

        self._table.update(self._db_id, x=x, y=y, z=z)

    _stored_point3d: _point.Point = None

    @property
    def point(self) -> _point.Point:
        if self._stored_point3d is None:
            self._stored_point3d = _point.Point(self.x, self.y, self.z, db_id=str(self.db_id) + '3d')
            self._stored_point3d.bind(self._update_point)

        return self._stored_point3d
