
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase

from ...wrappers.decimal import Decimal as _decimal
from ...geometry import line as _line

if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_wire_marker as _pjt_wire_marker
    from ..global_db import wire as _wire


class PJTWiresTable(PJTTableBase):
    __table_name__ = 'pjt_wires'

    def __iter__(self) -> _Iterable["PJTWire"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWire(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWire":
        if isinstance(item, int):
            if item in self:
                return PJTWire(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, circuit_id: int, start_point3d_id: int | None, stop_point3d_id: int | None,
               start_point2d_id: int | None, stop_point2d_id: int | None, is_visible: bool,
               layer_view_point_id: int | None, layer_id: int | None, is_filler_wire: bool) -> "PJTWire":

        db_id = PJTTableBase.insert(self, part_id=part_id, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
                                    start_point2d_id=start_point2d_id, stop_point2d_id=stop_point2d_id,
                                    is_visible=int(is_visible), layer_view_point_id=layer_view_point_id,
                                    layer_id=layer_id, is_filler_wire=int(is_filler_wire))

        return PJTWire(self, db_id, self.project_id)


class PJTWire(PJTEntryBase):
    _table: PJTWiresTable = None

    @property
    def wire_markers(self) -> list["_pjt_wire_marker.PJTWireMarker"]:
        db_ids = self._table.db.pjt_wire_markers_table.select('id', wire_id=self.db_id)
        res = []
        for db_id in db_ids:
            res.append(self._table.db.pjt_wire_markers_table[db_id[0]])

        return res

    @property
    def layer_view_point(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.layer_view_point_id
        return self._table.db.pjt_points2d_table[point_id]

    @property
    def layer_view_point_id(self) -> int:
        return self._table.select('layer_view_point_id', id=self._db_id)[0][0]

    @layer_view_point_id.setter
    def layer_view_point_id(self, value: int):
        self._table.update(self._db_id, layer_view_point_id=value)
        self._process_callbacks()

    @property
    def layer_id(self) -> int | None:
        return self._table.select('layer_id', id=self._db_id)[0][0]

    @layer_id.setter
    def layer_id(self, value: int | None):
        self._table.update(self._db_id, layer_id=value)
        self._process_callbacks()

    @property
    def is_filler_wire(self) -> bool:
        return bool(self._table.select('is_filler_wire', id=self._db_id)[0][0])

    @is_filler_wire.setter
    def is_filler_wire(self, value: bool):
        self._table.update(self._db_id, is_filler_wire=int(value))
        self._process_callbacks()

    @property
    def length_mm(self) -> _decimal:
        return _line.Line(self.start_point3d, self.stop_point3d).length()

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
        length = _line.Line(self.start_point3d, self.stop_point3d).length()
        return resistance * length

    @property
    def table(self) -> PJTWiresTable:
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
    def start_point2d(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.start_point2d_id
        if point_id is None:
            return None

        return self._table.db.pjt_points2d_table[point_id]

    @property
    def start_point2d_id(self) -> int:
        return self._table.select('start_point2d_id', id=self._db_id)[0][0]

    @start_point2d_id.setter
    def start_point2d_id(self, value: int):
        self._table.update(self._db_id, start_point2d_id=value)
        self._process_callbacks()

    @property
    def stop_point2d(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.stop_point2d_id
        if point_id is None:
            return None

        return self._table.db.pjt_points2d_table[point_id]

    @property
    def stop_point2d_id(self) -> int:
        return self._table.select('stop_point2d_id', id=self._db_id)[0][0]

    @stop_point2d_id.setter
    def stop_point2d_id(self, value: int):
        self._table.update(self._db_id, stop_point2d_id=value)
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

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()
