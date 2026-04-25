
from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from ..global_db import wire as _wire
from . import pjt_circuit as _pjt_circuit
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    StartStopPosition3DMixin, StartStopPosition3DControl,
    StartStopPosition2DMixin, StartStopPosition2DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl
)

from ...geometry import line as _line


if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire_marker as _pjt_wire_marker
    from ...geometry import point as _point

    from ...objects import wire as _wire_obj


class PJTWiresTable(PJTTableBase):
    __table_name__ = 'pjt_wires'

    _control: "PJTWireControl" = None

    @property
    def control(self) -> "PJTWireControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTWireControl(mainframe)
        cls._control.Show(False)

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


class PJTWire(PJTEntryBase, StartStopPosition3DMixin, PartMixin, StartStopPosition2DMixin,
              Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin):

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
        if self._stored_layer_view_position is None and self._obj is not None:
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
        self._populate('layer_view_position_id')

    @property
    def layer_id(self) -> int | None:
        return self._table.select('layer_id', id=self._db_id)[0][0]

    @layer_id.setter
    def layer_id(self, value: int | None):
        self._table.update(self._db_id, layer_id=value)
        self._populate('layer_id')

    @property
    def is_filler_wire(self) -> bool:
        return bool(self._table.select('is_filler_wire', id=self._db_id)[0][0])

    @is_filler_wire.setter
    def is_filler_wire(self, value: bool):
        self._table.update(self._db_id, is_filler_wire=int(value))
        self._populate('is_filler_wire')

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
        self._populate('circuit_id')

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


class PJTWireControl(wx.Notebook):

    def _update_position3d(self, _):
        self.length_mm_ctrl.SetValue(str(self.db_obj.length_mm))
        self.length_m_ctrl.SetValue(str(self.db_obj.length_m))
        self.length_ft_ctrl.SetValue(str(self.db_obj.length_ft))
        self.weight_g_ctrl.SetValue(str(self.db_obj.weight_g))
        self.weight_lb_ctrl.SetValue(str(self.db_obj.weight_lb))
        self.resistance_ctrl.SetValue(str(self.db_obj.resistance))

    def set_obj(self, db_obj: PJTWire):
        if self.db_obj is not None:
            self.db_obj.start_position3d.unbind(self._update_position3d)
            self.db_obj.stop_position3d.unbind(self._update_position3d)

        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.wire_ctrl.set_obj(None)
            self.circuit_ctrl.set_obj(None)

            self.is_filler_wire_ctrl.SetValue(False)
            self.is_filler_wire_ctrl.Enable(False)

            self.length_mm_ctrl.SetValue('')
            self.length_m_ctrl.SetValue('')
            self.length_ft_ctrl.SetValue('')
            self.weight_g_ctrl.SetValue('')
            self.weight_lb_ctrl.SetValue('')
            self.resistance_ctrl.SetValue('')

        else:
            self.wire_ctrl.set_obj(db_obj.part)
            self.circuit_ctrl.set_obj(db_obj.circuit)
            self.is_filler_wire_ctrl.SetValue(db_obj.is_filler_wire)
            self.is_filler_wire_ctrl.Enable(True)
            self.length_mm_ctrl.SetValue(str(db_obj.length_mm))
            self.length_m_ctrl.SetValue(str(db_obj.length_m))
            self.length_ft_ctrl.SetValue(str(db_obj.length_ft))
            self.weight_g_ctrl.SetValue(str(db_obj.weight_g))
            self.weight_lb_ctrl.SetValue(str(db_obj.weight_lb))
            self.resistance_ctrl.SetValue(str(db_obj.resistance))

            self.db_obj.start_position3d.bind(self._update_position3d)
            self.db_obj.stop_position3d.bind(self._update_position3d)

    def __init__(self, parent):
        self.db_obj: PJTWire = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        self.is_filler_wire_ctrl = _prop_grid.BoolProperty(general_page, 'Is Filler Wire')

        position_page = _prop_grid.Category(self, 'Position')

        self.position2d_ctrl = StartStopPosition2DControl(position_page)
        self.position3d_ctrl = StartStopPosition3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        info_page = _prop_grid.Category(self, 'Info')

        length_group = _prop_grid.Property(info_page, 'Length', orientation=wx.VERTICAL)

        self.length_mm_ctrl = _prop_grid.StringProperty(length_group, 'Millimeter', style=wx.TE_READONLY)
        self.length_m_ctrl = _prop_grid.StringProperty(length_group, 'Meter', style=wx.TE_READONLY)
        self.length_ft_ctrl = _prop_grid.StringProperty(length_group, 'Foot', style=wx.TE_READONLY)

        weight_group = _prop_grid.Property(info_page, 'Weight', orientation=wx.VERTICAL)

        self.weight_g_ctrl = _prop_grid.StringProperty(weight_group, 'Gram', style=wx.TE_READONLY)
        self.weight_lb_ctrl = _prop_grid.StringProperty(weight_group, 'Pound', style=wx.TE_READONLY)

        electrical_group = _prop_grid.Property(info_page, 'Electrical', orientation=wx.VERTICAL)

        self.resistance_ctrl = _prop_grid.StringProperty(electrical_group, 'Resistance', units='Ω', style=wx.TE_READONLY)

        circuit_page = _prop_grid.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.wire_ctrl = _wire.WireControl(part_page)

        for page in (
            general_page,
            info_page,
            position_page,
            visible_page,
            circuit_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
