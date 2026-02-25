from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from ...wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_bundle as _pjt_bundle


class PJTBundleLayoutsTable(PJTTableBase):
    __table_name__ = 'pjt_bundle_layouts'

    def __iter__(self) -> _Iterable["PJTBundleLayout"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundleLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundleLayout":
        if isinstance(item, int):
            if item in self:
                return PJTBundleLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, coord_id: int, diameter: _decimal) -> "PJTBundleLayout":
        db_id = PJTTableBase.insert(self, coord_id=coord_id, diameter=float(diameter))

        return PJTBundleLayout(self, db_id, self.project_id)


class PJTBundleLayout(PJTEntryBase):
    _table: PJTBundleLayoutsTable = None

    @property
    def attached_bundles(self) -> list["_pjt_bundle.PJTBundle"]:
        res = []
        point_id = self.point3d_id
        db_ids = self._table.db.pjt_bundles_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)

        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTBundleLayoutsTable:
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
    def diameter(self) -> _decimal:
        diameter = self._table.select('diameter', id=self._db_id)[0][0]
        return _decimal(diameter)

    @diameter.setter
    def diameter(self, value: _decimal):
        self._table.update(self._db_id, diameter=float(value))
        self._process_callbacks()
