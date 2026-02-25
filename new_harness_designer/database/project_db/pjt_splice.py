
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from .mixins import PartMixin, StartStopPosition3DMixin, Visible3DMixin, Visible2DMixin
from ...geometry import point as _point


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


class PJTSplice(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, Visible2DMixin):

    _table: PJTSplicesTable = None

    @property
    def table(self) -> PJTSplicesTable:
        return self._table

    @property
    def wires(self) -> list[list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"]]:
        start_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.start_position3d_id)
        start_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.start_position3d_id)

        stop_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.stop_position3d_id)
        stop_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.stop_position3d_id)

        branch_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.branch_position3d_id)
        branch_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.branch_position3d_id)

        def _get_wires(rows):
            ret_ = []
            for row in rows:
                ret_.append(self._table.db.pjt_wires_table[row[0]])

            return ret_

        start_wires = _get_wires(start_db_ids1)
        start_wires.extend(_get_wires(start_db_ids2))

        stop_wires = _get_wires(stop_db_ids1)
        stop_wires.extend(_get_wires(stop_db_ids2))

        branch_wires = _get_wires(branch_db_ids1)
        branch_wires.extend(_get_wires(branch_db_ids2))

        return [start_wires, stop_wires, branch_wires]

    def _update_branch_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def branch_position3d(self) -> _point.Point:
        point_id = self.branch_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self._update_branch_position3d)
            return point

    @property
    def branch_position3d_id(self) -> int:
        point_id = self._table.select('branch_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.branch_position3d_id = point_id

        return point_id

    @branch_position3d_id.setter
    def branch_position3d_id(self, value: int):
        self._table.update(self._db_id, branch_point3d_id=value)

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
    def resistance(self) -> float:
        return self.part.resistance

    @property
    def part(self) -> "_splice.Splice":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.splices_table[part_id]
