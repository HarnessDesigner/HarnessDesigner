
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase

if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_wire as _pjt_wire


class PJTWireLayoutsTable(PJTTableBase):
    __table_name__ = 'pjt_wire_layouts'

    def __iter__(self) -> _Iterable["PJTWireLayout"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireLayout":
        if isinstance(item, int):
            if item in self:
                return PJTWireLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point_id: int) -> "PJTWireLayout":
        db_id = PJTTableBase.insert(self, point_id=point_id)
        return PJTWireLayout(self, db_id, self.project_id)


class PJTWireLayout(PJTEntryBase):
    _table: PJTWireLayoutsTable = None

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        point_id = self.point3d_id
        db_ids = self._table.db.pjt_wires_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTWireLayoutsTable:
        return self._table

    @property
    def point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point3d_id = self.point3d_id
        return self._table.db.pjt_points3d_table[point3d_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
        self._process_callbacks()

    @property
    def point2d(self) -> "_pjt_point2d.PJTPoint2D":
        point2d_id = self.point2d_id
        return self._table.db.pjt_points2d_table[point2d_id]

    @property
    def point2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    def point2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)
        self._process_callbacks()
