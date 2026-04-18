from typing import Iterable as _Iterable, Union as _Union, TYPE_CHECKING

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    NameMixin,
    NotesMixin, NotesControl
)


from . import pjt_wire as _pjt_wire
from . import pjt_splice as _pjt_splice
from . import pjt_terminal as _pjt_terminal
from . import pjt_housing as _pjt_housing
from . import pjt_wire_service_loop as _pjt_wire_service_loop

from ...geometry import point as _point
from ...geometry.decimal import Decimal as _d
from ... import logger as _logger


if TYPE_CHECKING:
    from ...objects import circuit as _circuit_obj


class PJTCircuitsTable(PJTTableBase):
    __table_name__ = 'pjt_circuits'

    def _table_needs_update(self) -> bool:
        from ..create_database import circuits

        return circuits.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import circuits

        circuits.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import circuits

        circuits.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCircuit"]:

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCircuit(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCircuit":
        if isinstance(item, int):
            if item in self:
                return PJTCircuit(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, circuit_num: int) -> "PJTCircuit":
        db_id = PJTTableBase.insert(self, circuit_num=circuit_num)

        return PJTCircuit(self, db_id, self.project_id)


class _Set:

    def __init__(self, args: list):
        for arg in args:
            count = args.count(arg)
            while count > 1:
                index = args.index(arg, len(args) - 1, args.index(arg))
                args.pop(index)
                count = args.count(arg)

        self.items = args

    def intersection(self, args: list):
        new_args = []

        for arg in args:
            if arg in self.items and arg not in new_args:
                new_args.append(arg)

        return _Set(new_args)

    def __iter__(self):
        return iter(self.items)

    def __str__(self):
        def _iter(ls, indent=''):
            line = []

            for item in ls:
                if isinstance(item, list):
                    line.append(_iter(item, indent + '  '))
                else:
                    line.append(f'{indent}  {str(item)}')
            line = ',\n'.join(line)
            return f'{indent}[' + '\n' + line + '\n' + f'{indent}]'

        return _iter(self.items)


class PJTCircuit(PJTEntryBase, NameMixin, NotesMixin):
    _table: PJTCircuitsTable = None

    def build_monitor_packet(self):

        packet = {
            'pjt_circuits': [self.db_id],
        }

        return packet

    def get_object(self) -> "_circuit_obj.Circuit":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_circuit_obj.Circuit"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def volts(self) -> float:
        terminal = self.start_terminal
        if terminal is None:
            return 0.0

        return terminal.volts

    @property
    def resistance(self) -> float:
        resistance = _d(0)

        for terminal in self.terminals:
            resistance += _d(terminal.resistance)

        for splice in self.splices:
            resistance += _d(splice.resistance)

        for wire in self.wires:
            resistance += _d(wire.resistance)

        for loop in self.wire_service_loops:
            resistance += _d(loop.resistance)

        return float(resistance)

    @property
    def start_terminal(self) -> _pjt_terminal.PJTTerminal:
        db_ids = self._table.db.pjt_terminals_table.select('db_id', is_start=1, circuit_id=self.db_id)
        if db_ids:
            return self._table.db.pjt_terminals_table[db_ids[0][0]]

    @property
    def voltage_drop(self) -> float:
        drop = 0.0

        for terminal in self.load_terminals:
            drop = max(terminal.voltage_drop, drop)

        return drop

    @property
    def load_terminals(self) -> list[_pjt_terminal.PJTTerminal]:
        res = []
        db_ids = self._table.db.pjt_terminals_table.select('db_id', is_start=0, circuit_id=self.db_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_terminals_table[db_id[0]])

        return res

    @property
    def circuit_map(self):

        def iter_objs(obj, point: "_point.Point"):
            res = []

            if isinstance(obj, _pjt_terminal.PJTTerminal):
                if not obj.is_start:
                    return [obj]

                db_ids = list(obj.table.db.pjt_wires_table.select('db_id', start_point3d_id=int(point.db_id)))

                if not db_ids:
                    return [obj]

                elif len(db_ids) > 1:
                    wires = []
                    for db_id in db_ids:
                        wire = obj.table.db.pjt_wires_table[db_id[0]]
                        wires.append(iter_objs(wire, wire.stop_position3d))

                    result = _Set(wires[0])
                    for s in wires[1:]:
                        result = result.intersection(s)

                    common_obj = list(result)[0]
                    max_trace_len = 0

                    for trace in wires:
                        max_trace_len = max(len(trace[:trace.index(common_obj)]), max_trace_len)

                    for i, trace in enumerate(wires):
                        trace = trace[:trace.index(common_obj)]
                        trace_len = len(trace)

                        while trace_len < max_trace_len:
                            trace.insert(1, None)
                            trace_len = len(trace)
                        wires[i] = trace

                    res.append(wires)
                    res.insert(0, obj)

                    if isinstance(common_obj, _pjt_terminal.PJTTerminal):
                        res.append(common_obj)
                    elif isinstance(common_obj, _pjt_splice.PJTSplice):
                        res.extend(iter_objs(common_obj, common_obj.stop_position3d))
                    else:
                        raise RuntimeError(str(common_obj))

                    return res
                else:
                    wire = obj.table.db.pjt_wires_table[db_ids[0][0]]
                    res.extend(iter_objs(wire, wire.stop_position3d))
                    res.insert(0, obj)
                    return res

            elif isinstance(obj, _pjt_wire.PJTWire):
                db_ids = list(obj.table.db.pjt_terminals_table.select(
                    'db_id', circuit_id=self.db_id, point3d_id=int(point.db_id)))

                for db_id in db_ids:
                    terminal = obj.table.db.pjt_terminals_table[db_id[0]]
                    res.append(terminal)

                if res:
                    res.insert(0, obj)
                    return res

                db_ids = obj.table.db.pjt_wires_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=int(point.db_id))

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    res.extend(iter_objs(wire, wire.stop_position3d))

                db_ids = obj.table.db.pjt_wire_service_loops_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=int(point.db_id))

                for db_id in db_ids:
                    loop = obj.table.db.pjt_wire_service_loops_table[db_id[0]]
                    res.extend(iter_objs(loop, loop.stop_position3d))

                db_ids = obj.table.db.pjt_splices_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=int(point.db_id))

                for db_id in db_ids:
                    splice = obj.table.db.pjt_splices_table[db_id[0]]
                    res.extend(iter_objs(splice, splice.stop_position3d))

                res.insert(0, obj)

                return res

            elif isinstance(obj, _pjt_splice.PJTSplice):
                db_ids = obj.table.db.pjt_wires_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=obj.branch_position3d_id)
                wires = []

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    wires.append(iter_objs(wire, wire.stop_position3d))

                res.append(wires[:])
                wires = []
                db_ids = obj.table.db.pjt_wires_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=int(point.db_id))

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    wires.append(iter_objs(wire, wire.stop_position3d))

                if len(wires) > 1:
                    result = _Set(wires[0])
                    for s in wires[1:]:
                        result = result.intersection(s)

                    _logger.logger.database('SEARCH RESULT:', result)
                    # common_obj = list(result)[0]

                    raise RuntimeError

                elif len(wires):
                    res.extend(wires[0])

                res.insert(0, obj)

                return res

            elif isinstance(obj, _pjt_wire_service_loop.PJTWireServiceLoop):
                db_ids = list(obj.table.db.pjt_wires_table.select(
                    'db_id', circuit_id=self.db_id, start_point3d_id=int(point.db_id)))

                db_ids.extend(list(obj.table.db.pjt_wires_table.select(
                    'db_id', circuit_id=self.db_id, stop_point3d_id=int(point.db_id))))

                if not db_ids:
                    return [obj]

                wire = obj.table.db.pjt_wires_table[db_ids[0][0]]
                w_start_point = wire.start_position3d

                if w_start_point == point:
                    res.extend(iter_objs(wire, wire.stop_position3d))
                else:
                    res.extend(iter_objs(wire, w_start_point))

                res.insert(0, obj)
                return res
            else:
                raise RuntimeError('sanity check')

        t = self.start_terminal
        return iter_objs(t, t.position3d)

    def get_circuit_end_terminals(
        self, target: _Union[_pjt_terminal.PJTTerminal, _pjt_wire.PJTWire, _pjt_splice.PJTSplice,
                             _pjt_wire_service_loop.PJTWireServiceLoop]) -> list[_pjt_terminal.PJTTerminal]:

        circuit_map = self.circuit_map

        def _iter_list(f_list):
            terms = []

            for item in f_list:
                if isinstance(item, list):
                    terms.extend(_iter_list(item))
                elif isinstance(item, _pjt_terminal.PJTTerminal):
                    terms.append(item)

            return terms

        def _iter_map(objs, obj_found=False):
            res = []

            for obj in objs:
                if isinstance(obj, list):
                    found_objs, obj_found = _iter_map(obj, obj_found)

                    if obj_found:
                        res.extend(found_objs)
                else:
                    if obj == target:
                        obj_found = True

                    if obj_found is True:
                        res.append(obj)

            return res, obj_found

        f_objs, found = _iter_map(circuit_map)

        if not found:
            raise RuntimeError('sanity check')

        terminals = _iter_list(f_objs)
        return terminals

    def get_circuit(self, target: _Union[_pjt_terminal.PJTTerminal, _pjt_wire.PJTWire, _pjt_splice.PJTSplice,
                                         _pjt_wire_service_loop.PJTWireServiceLoop]) -> list:

        circuit_map = self.circuit_map

        def _iter_map(objs):
            res = []

            for obj in objs:
                if isinstance(obj, list):
                    found_objs = _iter_map(obj)

                    if found_objs is not None:
                        res.extend(found_objs)
                        return res
                else:
                    res.append(obj)
                    if obj == target:
                        return res

        ret = _iter_map(circuit_map)
        if ret is None:
            raise RuntimeError('sanity check')

        return ret

    @property
    def table(self) -> PJTCircuitsTable:
        return self._table

    @property
    def circuit_num(self) -> int:
        return self._table.select('circuit_num', id=self._db_id)[0][0]

    @circuit_num.setter
    def circuit_num(self, value: int):
        self._table.update(self._db_id, circuit_num=value)
        self._populate('circuit_num')

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)
        self._populate('description')

    @property
    def total_circuit_load(self) -> float:
        resistance = sum([wire.resistance for wire in self.wires])
        resistance += sum([splice.resistance for splice in self.splices])
        resistance += sum([loop.resistance for loop in self.wire_service_loops])
        resistance += sum([terminal.resistance for terminal in self.terminals])

        load = sum([terminal.load for terminal in self.terminals if not terminal.is_start])
        volts = self.start_terminal.volts

        return (volts / resistance) + load

    @property
    def total_circuit_weight_g(self) -> float:
        return self.terminal_weight_g + self.wire_weight_g + self.splice_weight_g

    @property
    def total_circuit_weight_lb(self) -> float:
        return self.terminal_weight_lb + self.wire_weight_lb + self.splice_weight_lb

    @property
    def wire_length_mm(self) -> float:
        wire_length = sum([wire.length_mm for wire in self.wires])
        wire_length += sum([loop.length_mm for loop in self.wire_service_loops])
        return wire_length

    @property
    def wire_length_m(self) -> float:
        return self.wire_length_mm / 1000.0

    @property
    def wire_length_ft(self) -> float:
        return self.wire_length_m * 3.28084

    @property
    def wire_weight_g(self) -> float:
        wire_weight = sum([wire.weight_g for wire in self.wires])
        wire_weight += sum([loop.weight_g for loop in self.wire_service_loops])
        return wire_weight

    @property
    def wire_weight_lb(self) -> float:
        return sum([wire.weight_lb for wire in self.wires])

    @property
    def terminal_weight_g(self) -> float:
        return sum([terminal.part.weight for terminal in self.terminals])

    @property
    def terminal_weight_lb(self) -> float:
        weight_g = self.terminal_weight_g
        return weight_g * 0.00220462

    @property
    def splice_weight_g(self) -> float:
        return sum([splice.part.weight for splice in self.splices])

    @property
    def splice_weight_lb(self) -> float:
        weight_g = self.splice_weight_g
        return weight_g * 0.00220462

    @property
    def wires(self) -> list[_pjt_wire.PJTWire]:
        res = []
        for wire_id in self._table.db.pjt_wires_table.select('id', circuit_id=self._db_id):
            res.append(self._table.db.pjt_wires_table[wire_id[0]])

        return res

    @property
    def wire_service_loops(self) -> list[_pjt_wire_service_loop.PJTWireServiceLoop]:
        res = []
        for wire_id in self._table.db.pjt_wire_service_loops_table.select('id', circuit_id=self._db_id):
            res.append(self._table.db.pjt_wire_service_loops_table[wire_id[0]])

        return res

    @property
    def splices(self) -> list[_pjt_splice.PJTSplice]:
        res = []
        for wire_id in self._table.db.pjt_splices_table.select('id', circuit_id=self._db_id):
            res.append(self._table.db.pjt_splices_table[wire_id[0]])

        return res

    @property
    def terminals(self) -> list[_pjt_terminal.PJTTerminal]:
        res = []
        for wire_id in self._table.db.pjt_terminals_table.select('id', circuit_id=self._db_id):
            res.append(self._table.db.pjt_terminals_table[wire_id[0]])

        return res

    @property
    def housings(self) -> list[_pjt_housing.PJTHousing]:
        res = []
        for wire_id in self._table.db.pjt_housings_table.select('id', circuit_id=self._db_id):
            res.append(self._table.db.pjt_housings_table[wire_id[0]])

        return res


class PJTCircuitControl(wx.Notebook):

    def _on_circuit_num(self, evt):
        num = evt.GetValue()

        try:
            num = int(num)
        except ValueError:
            self.circuit_num_ctrl.SetValue('')
            return

        self.db_obj.table.execute(f'SELECT id FROM pjt_circuits WHERE circuit_num={num} AND project_id={self.db_obj.project_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id = rows[0]

        else:
            db_obj = self.db_obj.table.insert(num)
            name = self.name_ctrl.GetValue()
            db_id = db_obj.db_id

            if name not in self.name_choices:
                self.name_choices.append(name)
                self.name_choices.sort()

                self.name_ctrl.SetItems(self.name_choices)
                self.name_ctrl.SetValue(name)
            else:
                name = ''

            self.name_ctrl.SetValue('')

            db_obj.description = self.description_ctrl.GetValue()

            self.circuit_choices.append(str(num))
            self.circuit_num_ctrl.SetItems(self.circuit_choices)
            self.circuit_num_ctrl.SetValue(str(num))

            self.name_choices.append(name)

        self._parent.set_circuit(db_id)

    def _on_description(self, evt):
        value = evt.GetValue()
        self.db_obj.description = value

    def _on_name(self, evt):
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM pjt_circuits WHERE name="{name}" AND project_id={self.db_obj.project_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id = rows[0]

        else:
            self.db_obj.table.execute(f'SELECT circuit_num FROM pjt_circuits WHERE  project_id={self.db_obj.project_id};')
            rows = self.db_obj.table.fetchall()
            if rows:
                circuit_num = max([row[0] for row in rows])
            else:
                circuit_num = -1

            circuit_num += 1

            db_obj = self.db_obj.table.insert(circuit_num)
            db_obj.name = name
            db_id = db_obj.db_id
            db_obj.name = name
            db_obj.description = self.description_ctrl.GetValue()

            self.name_choices.append(name)
            self.name_choices.sort()

            self.name_ctrl.SetItems(self.name_choices)
            self.name_ctrl.SetValue(name)

            self.circuit_choices.append(str(circuit_num))
            value = self.circuit_num_ctrl.GetValue()
            self.circuit_num_ctrl.SetItems(self.circuit_choices)
            self.circuit_num_ctrl.SetValue(value)

        self._parent.set_circuit(db_id)

    def set_obj(self, db_obj: PJTCircuit):
        self.db_obj = db_obj

        self.notes_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.name_choices = []
            self.name_ctrl.SetItems([])
            self.name_ctrl.SetValue('')

            self.circuit_choices = []
            self.circuit_num_ctrl.SetItems([])
            self.circuit_num_ctrl.SetValue('')

            self.description_ctrl.SetValue('')
            self.voltage_drop_ctrl.SetValue('')
            self.voltage_ctrl.SetValue('')
            self.total_circuit_resistance_ctrl.SetValue('')
            self.total_circuit_load_ctrl.SetValue('')
            self.total_circuit_weight_g_ctrl.SetValue('')
            self.total_circuit_weight_lb_ctrl.SetValue('')
            self.wire_length_mm_ctrl.SetValue('')
            self.wire_length_m_ctrl.SetValue('')
            self.wire_length_ft_ctrl.SetValue('')
            self.wire_weight_g_ctrl.SetValue('')
            self.wire_weight_lb_ctrl.SetValue('')
            self.terminal_weight_g_ctrl.SetValue('')
            self.terminal_weight_lb_ctrl.SetValue('')
            self.splice_weight_g_ctrl.SetValue('')
            self.splice_weight_lb_ctrl.SetValue('')

        else:
            self.name_ctrl.SetValue(db_obj.name)
            self.circuit_num_ctrl.SetValue(str(db_obj.circuit_num))
            self.description_ctrl.SetValue(db_obj.description)
            self.voltage_drop_ctrl.SetValue(str(db_obj.voltage_drop))
            self.voltage_ctrl.SetValue(str(db_obj.volts))
            self.total_circuit_resistance_ctrl.SetValue(str(db_obj.resistance))
            self.total_circuit_load_ctrl.SetValue(str(db_obj.total_circuit_load))
            self.total_circuit_weight_g_ctrl.SetValue(str(db_obj.total_circuit_weight_g))
            self.total_circuit_weight_lb_ctrl.SetValue(str(db_obj.total_circuit_weight_lb))
            self.wire_length_mm_ctrl.SetValue(str(db_obj.wire_length_mm))
            self.wire_length_m_ctrl.SetValue(str(db_obj.wire_length_m))
            self.wire_length_ft_ctrl.SetValue(str(db_obj.wire_length_ft))
            self.wire_weight_g_ctrl.SetValue(str(db_obj.wire_weight_g))
            self.wire_weight_lb_ctrl.SetValue(str(db_obj.wire_weight_lb))
            self.terminal_weight_g_ctrl.SetValue(str(db_obj.terminal_weight_g))
            self.terminal_weight_lb_ctrl.SetValue(str(db_obj.terminal_weight_lb))
            self.splice_weight_g_ctrl.SetValue(str(db_obj.splice_weight_g))
            self.splice_weight_lb_ctrl.SetValue(str(db_obj.splice_weight_lb))

    def __init__(self, parent):
        self._parent = parent
        self.db_obj: PJTCircuit = None
        self.name_choices: list[str] = []
        self.circuit_choices: list[str] = []

        wx.Notebook.__init__(parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.name_ctrl = _prop_grid.ComboBoxProperty(general_page, 'Name', '', [])
        self.circuit_num_ctrl = _prop_grid.ComboBoxProperty(general_page, 'Circuit Number', '', [])
        self.description_ctrl = _prop_grid.LongStringProperty(general_page, 'Description', '')
        self.notes_ctrl = NotesControl(general_page)

        self.name_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name)
        self.circuit_num_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_circuit_num)
        self.description_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_description)

        info_page = _prop_grid.Category(self, 'Info')

        electrical_group = _prop_grid.Property(info_page, 'Electrical', orientation=wx.VERTICAL)
        self.voltage_ctrl = _prop_grid.StringProperty(electrical_group, 'Voltage', '', units='V', style=wx.TE_READONLY)
        self.voltage_drop_ctrl = _prop_grid.StringProperty(electrical_group, 'Voltage', '', units='V', style=wx.TE_READONLY)
        self.total_circuit_load_ctrl = _prop_grid.StringProperty(electrical_group, 'Total Circuit Load', '', units='ma', style=wx.TE_READONLY)
        self.total_circuit_resistance_ctrl = _prop_grid.StringProperty(electrical_group, 'Total Circuit Resistance', '', units='Ω', style=wx.TE_READONLY)

        total_weight_group = _prop_grid.Property(info_page, 'Total Circuit Weight', orientation=wx.VERTICAL)
        self.total_circuit_weight_g_ctrl = _prop_grid.StringProperty(total_weight_group, 'Grams', '', style=wx.TE_READONLY)
        self.total_circuit_weight_lb_ctrl = _prop_grid.StringProperty(total_weight_group, 'Pounds', '', style=wx.TE_READONLY)

        wire_length_group = _prop_grid.Property(info_page, 'Total Wire Length', orientation=wx.VERTICAL)
        self.wire_length_mm_ctrl = _prop_grid.StringProperty(wire_length_group, 'Millimeters', '', style=wx.TE_READONLY)
        self.wire_length_m_ctrl = _prop_grid.StringProperty(wire_length_group, 'Meters', '', style=wx.TE_READONLY)
        self.wire_length_ft_ctrl = _prop_grid.StringProperty(wire_length_group, 'Feet', '', style=wx.TE_READONLY)

        wire_weight_group = _prop_grid.Property(info_page, 'Total Wire Weight', orientation=wx.VERTICAL)
        self.wire_weight_g_ctrl = _prop_grid.StringProperty(wire_weight_group, 'Grams', '', style=wx.TE_READONLY)
        self.wire_weight_lb_ctrl = _prop_grid.StringProperty(wire_weight_group, 'Pounds', '', style=wx.TE_READONLY)

        terminal_weight_group = _prop_grid.Property(info_page, 'Total Terminal Weight', orientation=wx.VERTICAL)

        self.terminal_weight_g_ctrl = _prop_grid.StringProperty(terminal_weight_group, 'Grams', '', style=wx.TE_READONLY)
        self.terminal_weight_lb_ctrl = _prop_grid.StringProperty(terminal_weight_group, 'Pounds', '', style=wx.TE_READONLY)

        splice_weight_group = _prop_grid.Property(info_page, 'Total Splice Weight', orientation=wx.VERTICAL)
        self.splice_weight_g_ctrl = _prop_grid.StringProperty(splice_weight_group, 'Grams', '', style=wx.TE_READONLY)
        self.splice_weight_lb_ctrl = _prop_grid.StringProperty(splice_weight_group, 'Pounds', '', style=wx.TE_READONLY)
