
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from .mixins import Position3DMixin, Position2DMixin, Visible3DMixin, Visible2DMixin


if TYPE_CHECKING:
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


class PJTWireLayout(PJTEntryBase, Position3DMixin, Position2DMixin,
                    Visible3DMixin, Visible2DMixin):

    _table: PJTWireLayoutsTable = None

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        point_id = self.position3d_id
        db_ids = self._table.db.pjt_wires_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTWireLayoutsTable:
        return self._table

