from typing import TYPE_CHECKING, Iterable as _Iterable

import math
import numpy as np

from .pjt_bases import PJTEntryBase, PJTTableBase

from .mixins import Angle3DMixin, StartStopPosition3DMixin, PartMixin, Visible3DMixin, Visible2DMixin, NameMixin


if TYPE_CHECKING:
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire as _pjt_wire

    from ..global_db import wire as _wire

    from ...objects import wire_service_loop as _wire_service_loop_obj


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


class PJTWireServiceLoop(PJTEntryBase, Angle3DMixin, StartStopPosition3DMixin,
                         PartMixin, Visible3DMixin, Visible2DMixin, NameMixin):

    _table: PJTWireServiceLoopsTable = None

    def get_object(self) -> "_wire_service_loop_obj.WireServiceLoop":
        return self._obj

    def set_object(self, obj: "_wire_service_loop_obj.WireServiceLoop"):
        self._obj = obj

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=start_position_id)[0][0]
        stop_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_terminals_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_terminals_table[stop_position_ids[0][0]]

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_wires_table.select('id', wire_point3d_id=start_position_id)[0][0]
        stop_position_ids = self.table.db.pjt_wires_table.select('id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_wires_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_wires_table[stop_position_ids[0][0]]

    @property
    def length_mm(self) -> float:
        diameter = self.part.od_mm
        pitch = diameter + diameter * 0.15
        height = diameter + diameter * 0.15

        length = (height / pitch) * math.sqrt(math.pow(math.pi * diameter, 2.0) + math.pow(pitch, 2.0))
        length += diameter

        return length

    @property
    def length_m(self) -> float:
        return self.length_mm / 1000.0

    @property
    def length_ft(self) -> float:
        return self.length_m * 3.28084

    @property
    def weight_g(self) -> float:
        return self.part.weight_g_m * self.length_m

    @property
    def weight_lb(self) -> float:
        return self.part.weight_lb_ft * self.length_ft

    @property
    def resistance(self) -> float:
        resistance = self.part.resistance_1km

        # resistance per millimeter
        resistance /= 1000000.0

        return resistance * self.length_mm

    @property
    def table(self) -> PJTWireServiceLoopsTable:
        return self._table

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
