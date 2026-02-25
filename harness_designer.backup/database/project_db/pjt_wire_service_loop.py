from typing import TYPE_CHECKING, Iterable as _Iterable

import math
import numpy as np
import uuid

from . import PJTEntryBase, PJTTableBase

from ...wrappers.decimal import Decimal as _decimal
from ...geometry import angle as _angle

if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_circuit as _pjt_circuit

    from ..global_db import wire as _wire


class PJTWireServiceLoopsTable(PJTTableBase):
    __table_name__ = 'pjt_wire_service_loops'

    def __iter__(self) -> _Iterable["PJTWireServiceLoop"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireServiceLoop(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireServiceLoop":
        if isinstance(item, int):
            if item in self:
                return PJTWireServiceLoop(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, start_point3d_id: int, stop_point3d_id: int, part_id: int,
               circuit_id: int, is_visible: bool, quat: np.ndarray) -> "PJTWireServiceLoop":

        db_id = PJTTableBase.insert(self, part_id=part_id, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id,
                                    stop_point3d_id=stop_point3d_id,
                                    quat=str(quat.tolist()),
                                    is_visible=int(is_visible))

        return PJTWireServiceLoop(self, db_id, self.project_id)


class PJTWireServiceLoop(PJTEntryBase):
    _table: PJTWireServiceLoopsTable = None
    _angle_id: str = None

    @property
    def length_mm(self) -> _decimal:
        diameter = self.part.od_mm
        pitch = diameter + diameter * _decimal(0.15)
        height = diameter + diameter * _decimal(0.15)

        length = (height / pitch) * _decimal(math.sqrt(math.pow(math.pi * diameter, _decimal(2.0)) + math.pow(pitch, _decimal(2.0))))
        length += diameter

        return length

    @property
    def length_m(self) -> _decimal:
        return self.length_mm / _decimal(1000.0)

    @property
    def length_ft(self) -> _decimal:
        return self.length_m * _decimal(3.28084)

    @property
    def weight_g(self) -> _decimal:
        return self.part.weight_g_m * self.length_m

    @property
    def weight_lb(self) -> _decimal:
        return self.part.weight_lb_ft * self.length_ft

    @property
    def resistance(self) -> _decimal:
        resistance = self.part.resistance_1km

        # resistance per millimeter
        resistance /= _decimal(1000000.0)

        return resistance * self.length_mm

    @property
    def table(self) -> PJTWireServiceLoopsTable:
        return self._table

    @property
    def start_point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point_id = self.start_point3d_id

        if point_id is None:
            return None

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

        if point_id is None:
            return None

        return self._table.db.pjt_points3d_table[point_id]

    @property
    def stop_point3d_id(self) -> int:
        return self._table.select('stop_point3d_id', id=self._db_id)[0][0]

    @stop_point3d_id.setter
    def stop_point3d_id(self, value: int):
        self._table.update(self._db_id, stop_point3d_id=value)
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
    def is_visible(self) -> bool:
        return bool(self._table.select('is_visible', id=self._db_id)[0][0])

    @is_visible.setter
    def is_visible(self, value: bool):
        self._table.update(self._db_id, is_visible=int(value))
        self._process_callbacks()

    @property
    def part(self) -> "_wire.Wire":
        part_id = self.part_id

        if part_id is None:
            return None

        return self._table.db.global_db.wires_table[part_id]

    def __update_angle(self, angle: _angle.Angle):
        self._table.update(self._db_id, quat=str(angle.as_quat))
        self._process_callbacks()

    @property
    def angle3d(self) -> _angle.Angle:
        if self._angle_id is None:
            self._angle_id = str(uuid.uuid4())

        quat = eval(self._table.select('quat', id=self._db_id)[0][0])
        angle = _angle.Angle.from_quat(quat, db_id=self._angle_id)
        angle.bind(self.__update_angle)
        return angle

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()
