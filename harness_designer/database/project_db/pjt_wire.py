
from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from wx import propgrid as wxpg

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import StartStopPosition3DMixin, PartMixin, Visible3DMixin, Visible2DMixin, NameMixin
from ...geometry import line as _line


if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_wire_marker as _pjt_wire_marker
    from ..global_db import wire as _wire
    from ...geometry import point as _point

    from ...objects import wire as _wire_obj


class PJTWiresTable(PJTTableBase):
    __table_name__ = 'pjt_wires'

    def _table_needs_update(self) -> bool:
        from ..create_database import wires

        return wires.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import wires

        wires.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import wires

        wires.pjt_table.update_fields(self)

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


class PJTWire(PJTEntryBase, StartStopPosition3DMixin, PartMixin,
              Visible3DMixin, Visible2DMixin, NameMixin):

    _table: PJTWiresTable = None

    def build_monitor_packet(self):
        layer_view_position_id = self.layer_view_position_id

        start_position2d_id = self.start_position2d_id
        stop_position2d_id = self.stop_position2d_id

        start_position3d_id = self.start_position3d_id
        stop_position3d_id = self.stop_position3d_id

        packet = {
            'pjt_wires': [self.db_id],
            'wires': [self.part_id]
        }

        if None not in (start_position3d_id, stop_position3d_id):
            packet['pjt_points3d'] = [start_position3d_id, stop_position3d_id]

        if None not in (start_position2d_id, stop_position2d_id):
            packet['pjt_points2d'] = [start_position2d_id, stop_position2d_id]

        if layer_view_position_id is not None:
            if 'pjt_points2d' not in packet:
                packet['pjt_points2d'] = []

            packet['pjt_points2d'].append(layer_view_position_id)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_obj.Wire":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_wire_obj.Wire"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def terminals(self) -> list["_pjt_terminal.PJTTerminal"]:
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=start_position_id)[0][0]
        stop_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=stop_position_id)[0][0]

        res = []

        if start_position_ids:
            res.append(self.table.db.pjt_terminals_table[start_position_ids[0][0]])

        if stop_position_ids:
            res.append(self.table.db.pjt_terminals_table[stop_position_ids[0][0]])

        return res

    @property
    def wire_markers(self) -> list["_pjt_wire_marker.PJTWireMarker"]:
        db_ids = self._table.db.pjt_wire_markers_table.select('id', wire_id=self.db_id)
        res = []
        for db_id in db_ids:
            res.append(self._table.db.pjt_wire_markers_table[db_id[0]])

        return res

    _stored_layer_view_position: "_pjt_point2d.PJTPoint2D" = None

    @property
    def layer_view_position(self) -> "_point.Point":
        if self._stored_layer_view_point is None and self._obj is not None:
            point_id = self.layer_view_position_id

            if point_id is None:
                return

            self._stored_layer_view_position = self._table.db.pjt_points2d_table[point_id]
            self._stored_layer_view_position.add_object(self._obj())

        return self._stored_layer_view_position.point

    @property
    def layer_view_position_id(self) -> int:
        return self._table.select('layer_view_point_id', id=self._db_id)[0][0]

    @layer_view_position_id.setter
    def layer_view_position_id(self, value: int):
        self._stored_layer_view_position = None

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
    def length_mm(self) -> float:
        return _line.Line(self.start_position3d, self.stop_position3d).length()

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
        length = _line.Line(self.start_position3d, self.stop_position3d).length()
        return resistance * length

    @property
    def table(self) -> PJTWiresTable:
        return self._table

    _stored_start_position2d: "_pjt_point2d.PJTPoint2D" = None

    @property
    def start_position2d(self) -> "_point.Point":
        if self._stored_start_position2d is None and self._obj is not None:
            point_id = self.start_position2d_id

            if point_id is None:
                return None

            self._stored_start_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_start_position2d.add_object(self._obj())

        return self._stored_start_position2d.point

    @property
    def start_position2d_id(self) -> int:
        return self._table.select('start_point2d_id', id=self._db_id)[0][0]

    @start_position2d_id.setter
    def start_position2d_id(self, value: int):
        self._stored_start_position2d = None
        self._table.update(self._db_id, start_point2d_id=value)
        self._process_callbacks()

    _stored_stop_position2d: "_pjt_point2d.PJTPoint2D" = None

    @property
    def stop_position2d(self) -> "_point.Point":
        if self._stored_stop_position2d is None and self._obj is not None:
            point_id = self.stop_position2d_id

            if point_id is None:
                return None

            self._stored_stop_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_stop_position2d.add_object(self._obj())

        return self._stored_stop_position2d.point

    @property
    def stop_position2d_id(self) -> int:
        return self._table.select('stop_point2d_id', id=self._db_id)[0][0]

    @stop_position2d_id.setter
    def stop_position2d_id(self, value: int):
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

    _stored_part: "_wire.Wire" = None

    @property
    def part(self) -> "_wire.Wire":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None
        
            self._stored_part = self._table.db.global_db.wires_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def propgrid(self) -> wxpg.PGProperty:
        group = wxpg.PropertyCategory('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid
        angle_prop = self._angle3d_propgrid
        position_prop = self._position3d_propgrid
        housing_prop = self._housing_propgrid
        visible_prop = self._visible3d_propgrid

        group.AppendChild(name_prop)
        group.AppendChild(notes_prop)
        group.AppendChild(angle_prop)
        group.AppendChild(position_prop)
        group.AppendChild(visible_prop)
        group.AppendChild(housing_prop)

        part_prop = self._part_propgrid

        return group, part_prop
