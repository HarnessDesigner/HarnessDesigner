
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from ...wrappers.decimal import Decimal as _decimal


if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_wire as _pjt_wire

    from ..global_db import splice as _splice


class PJTSplicesTable(PJTTableBase):
    __table_name__ = 'pjt_splices'

    def __iter__(self) -> _Iterable["PJTSplice"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSplice(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTSplice":
        if isinstance(item, int):
            if item in self:
                return PJTSplice(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, circuit_id: int, start_point3d_id: int, stop_point3d_id: int,
               branch_point3d_id: int, point2d_id: int) -> "PJTSplice":

        db_id = PJTTableBase.insert(self, part_id=part_id, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
                                    branch_point3d_id=branch_point3d_id, point2d_id=point2d_id)

        return PJTSplice(self, db_id, self.project_id)


class PJTSplice(PJTEntryBase):
    _table: PJTSplicesTable = None

    @property
    def table(self) -> PJTSplicesTable:
        return self._table

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        db_ids = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.start_point3d_id)

        for db_id in db_ids:
            return self._table.db.pjt_wires_table[db_id[0]]

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        db_ids = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.branch_point3d_id)

        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def start_point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point_id = self.start_point3d_id
        return self._table.db.pjt_points3d_table[point_id]

    @property
    def start_point3d_id(self) -> int:
        return self._table.select('start_point3d_id', id=self._db_id)[0][0]

    @start_point3d_id.setter
    def start_point3d_id(self, value: int):
        self._table.update(self._db_id, start_point3d_id=value)
        self._process_callbacks()

    @property
    def stop_point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point_id = self.stop_point3d_id
        return self._table.db.pjt_points3d_table[point_id]

    @property
    def stop_point3d_id(self) -> int:
        return self._table.select('stop_point3d_id', id=self._db_id)[0][0]

    @stop_point3d_id.setter
    def stop_point3d_id(self, value: int):
        self._table.update(self._db_id, stop_point3d_id=value)
        self._process_callbacks()

    @property
    def branch_point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point_id = self.branch_point3d_id
        return self._table.db.pjt_points3d_table[point_id]

    @property
    def branch_point3d_id(self) -> int:
        return self._table.select('branch_point3d_id', id=self._db_id)[0][0]

    @branch_point3d_id.setter
    def branch_point3d_id(self, value: int):
        self._table.update(self._db_id, point33d_id=value)
        self._process_callbacks()

    @property
    def point2d(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.point2d_id
        return self._table.db.pjt_points2d_table[point_id]

    @property
    def point2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    def point2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)
        self._process_callbacks()

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        circuit_id = self.circuit_id
        return self._table.db.pjt_circuits_table[circuit_id]

    @property
    def circuit_id(self) -> int:
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int):
        self._table.update(self._db_id, circuit_id=value)
        self._process_callbacks()

    @property
    def resistance(self) -> _decimal:
        return self.part.resistance

    @property
    def part(self) -> "_splice.Splice":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.splices_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()
