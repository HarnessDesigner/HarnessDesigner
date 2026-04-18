from typing import TYPE_CHECKING, Iterable as _Iterable

import math
import numpy as np
import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .pjt_bases import PJTEntryBase, PJTTableBase
from ..global_db import wire as _wire
from .mixins import (
    Angle3DMixin, Angle3DControl,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin,  NotesControl
)


if TYPE_CHECKING:
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire as _pjt_wire

    from ...objects import wire_service_loop as _wire_service_loop_obj


class PJTWireServiceLoopsTable(PJTTableBase):
    __table_name__ = 'pjt_wire_service_loops'

    _control: "PJTWireServiceLoopControl" = None

    @property
    def control(self) -> "PJTWireServiceLoopControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTWireServiceLoopControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import wire_service_loops

        return wire_service_loops.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.update_fields(self)

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
                         PartMixin, Visible3DMixin, NotesMixin, NameMixin):

    _table: PJTWireServiceLoopsTable = None

    def build_monitor_packet(self):
        circuit = self.circuit

        packet = {
            'pjt_wire_service_loops': [self.db_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d],
        }

        if circuit is not None:
            self.merge_packet_data(circuit.build_monitor_packet(), packet)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_service_loop_obj.WireServiceLoop":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_wire_service_loop_obj.WireServiceLoop"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=start_position_id)[0][0]

        stop_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_terminals_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_terminals_table[stop_position_ids[0][0]]

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_wires_table.select(
            'id', wire_point3d_id=start_position_id)[0][0]

        stop_position_ids = self.table.db.pjt_wires_table.select(
            'id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_wires_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_wires_table[stop_position_ids[0][0]]

    @property
    def length_mm(self) -> float:
        diameter = self.part.od_mm
        pitch = diameter + diameter * 0.15
        height = diameter + diameter * 0.15

        length = ((height / pitch) *
                  math.sqrt(math.pow(math.pi * diameter, 2.0) +
                            math.pow(pitch, 2.0)))
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

    _stored_circuit: "_pjt_circuit.PJTCircuit" = None

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        if self._stored_circuit is None and self._obj is not None:
            circuit_id = self.circuit_id

            if circuit_id is None:
                return None

            self._stored_circuit = self._table.db.pjt_circuits_table[circuit_id]
            self._stored_circuit.add_object(self._obj())

        return self._stored_circuit

    @property
    def circuit_id(self) -> int | None:
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int | None):
        if value is None:
            self._stored_circuit = None

        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    @property
    def is_visible(self) -> bool:
        return bool(self._table.select('is_visible', id=self._db_id)[0][0])

    @is_visible.setter
    def is_visible(self, value: bool):
        self._table.update(self._db_id, is_visible=int(value))
        self._populate('is_visible')

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


class PJTWireServiceLoopControl(wx.Notebook):

    def set_obj(self, db_obj: PJTWireServiceLoop):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.wire_ctrl.set_obj(None)
            self.circuit_ctrl.set_obj(None)

        else:
            self.wire_ctrl.set_obj(db_obj.part)
            self.circuit_ctrl.set_obj(db_obj.circuit)


    def __init__(self, parent):
        self.db_obj: PJTWireServiceLoop = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        angle_page = _prop_grid.Category(self, 'Angle')
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position3d_ctrl = StartStopPosition3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)

        circuit_page = _prop_grid.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.wire_ctrl = _wire.WireControl(part_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            circuit_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
