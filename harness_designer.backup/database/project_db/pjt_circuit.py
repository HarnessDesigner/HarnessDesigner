from typing import Iterable as _Iterable, Union as _Union

from . import PJTEntryBase, PJTTableBase

from ...wrappers.decimal import Decimal as _decimal

from . import pjt_wire as _pjt_wire
from . import pjt_splice as _pjt_splice
from . import pjt_terminal as _pjt_terminal
from . import pjt_housing as _pjt_housing
from . import pjt_wire_service_loop as _pjt_wire_service_loop
from . import pjt_point3d as _pjt_point3d


class PJTCircuitsTable(PJTTableBase):
    __table_name__ = 'pjt_circuits'

    def __iter__(self) -> _Iterable["PJTCircuit"]:

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCircuit(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCircuit":
        if isinstance(item, int):
            if item in self:
                return PJTCircuit(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, circuit_num: int, name: str, description: str, volts: _decimal,
               load: _decimal, voltage_drop: _decimal) -> "PJTCircuit":

        db_id = PJTTableBase.insert(self, circuit_num=circuit_num,
                                    name=name, description=description, volts=float(volts),
                                    load=float(load), voltage_drop=float(voltage_drop))

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


class PJTCircuit(PJTEntryBase):
    _table: PJTCircuitsTable = None

    @property
    def start_terminal(self) -> _pjt_terminal.PJTTerminal:
        db_ids = self._table.db.pjt_terminals_table.select('db_id', is_start=1, circuit_id=self.db_id)
        if db_ids:
            return self._table.db.pjt_terminals_table[db_ids[0][0]]

    @property
    def load_terminals(self) -> list[_pjt_terminal.PJTTerminal]:
        res = []
        db_ids = self._table.db.pjt_terminals_table.select('db_id', is_start=0, circuit_id=self.db_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_terminals_table[db_id[0]])

        return res

    @property
    def circuit_map(self):

        def iter_objs(obj, point: "_pjt_point3d.PJTPoint3D"):
            res = []

            if isinstance(obj, _pjt_terminal.PJTTerminal):
                if not obj.is_start:
                    return [obj]

                db_ids = list(obj.table.db.pjt_wires_table.select('db_id', start_point3d_id=point.db_id))

                if not db_ids:
                    return [obj]

                elif len(db_ids) > 1:
                    wires = []
                    for db_id in db_ids:
                        wire = obj.table.db.pjt_wires_table[db_id[0]]
                        wires.append(iter_objs(wire, wire.stop_point3d))

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
                        res.extend(iter_objs(common_obj, common_obj.stop_point3d))
                    else:
                        raise RuntimeError(str(common_obj))

                    return res
                else:
                    wire = obj.table.db.pjt_wires_table[db_ids[0][0]]
                    res.extend(iter_objs(wire, wire.stop_point3d))
                    res.insert(0, obj)
                    return res

            elif isinstance(obj, _pjt_wire.PJTWire):
                db_ids = list(obj.table.db.pjt_terminals_table.select('db_id', circuit_id=self.db_id, point3d_id=point.db_id))

                for db_id in db_ids:
                    terminal = obj.table.db.pjt_terminals_table[db_id[0]]
                    res.append(terminal)

                if res:
                    res.insert(0, obj)
                    return res

                db_ids = obj.table.db.pjt_wires_table.select('db_id', circuit_id=self.db_id, start_point3d_id=point.db_id)

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    res.extend(iter_objs(wire, wire.stop_point3d))

                db_ids = obj.table.db.pjt_wire_service_loops_table.select('db_id', circuit_id=self.db_id, start_point3d_id=point.db_id)

                for db_id in db_ids:
                    loop = obj.table.db.pjt_wire_service_loops_table[db_id[0]]
                    res.extend(iter_objs(loop, loop.stop_point3d))

                db_ids = obj.table.db.pjt_splices_table.select('db_id', circuit_id=self.db_id, start_point3d_id=point.db_id)

                for db_id in db_ids:
                    splice = obj.table.db.pjt_splices_table[db_id[0]]
                    res.extend(iter_objs(splice, splice.stop_point3d))

                res.insert(0, obj)

                return res

            elif isinstance(obj, _pjt_splice.PJTSplice):
                db_ids = obj.table.db.pjt_wires_table.select('db_id', circuit_id=self.db_id, start_point3d_id=obj.branch_point3d_id)
                wires = []

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    wires.append(iter_objs(wire, wire.stop_point3d))

                res.append(wires[:])
                wires = []
                db_ids = obj.table.db.pjt_wires_table.select('db_id', circuit_id=self.db_id, start_point3d_id=point.db_id)

                for db_id in db_ids:
                    wire = obj.table.db.pjt_wires_table[db_id[0]]
                    wires.append(iter_objs(wire, wire.stop_point3d))

                if len(wires) > 1:
                    result = _Set(wires[0])
                    for s in wires[1:]:
                        result = result.intersection(s)

                    print(result)
                    # common_obj = list(result)[0]

                    raise RuntimeError

                elif len(wires):
                    res.extend(wires[0])

                res.insert(0, obj)

                return res

            elif isinstance(obj, _pjt_wire_service_loop.PJTWireServiceLoop):
                db_ids = list(obj.table.db.pjt_wires_table.select('db_id', circuit_id=self.db_id, start_point3d_id=point.db_id))
                db_ids.extend(list(obj.table.db.pjt_wires_table.select('db_id', circuit_id=self.db_id, stop_point3d_id=point.db_id)))

                if not db_ids:
                    return [obj]

                wire = obj.table.db.pjt_wires_table[db_ids[0][0]]
                w_start_point = wire.start_point3d

                if w_start_point == point:
                    res.extend(iter_objs(wire, wire.stop_point3d))
                else:
                    res.extend(iter_objs(wire, w_start_point))

                res.insert(0, obj)
                return res
            else:
                raise RuntimeError('sanity check')

        t = self.start_terminal
        return iter_objs(t, t.point3d)

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
        self._process_callbacks()

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)
        self._process_callbacks()

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)
        self._process_callbacks()

    @property
    def total_circuit_load(self) -> _decimal:
        resistance = sum([wire.resistance for wire in self.wires])
        resistance += sum([splice.resistance for splice in self.splices])
        resistance += sum([loop.resistance for loop in self.wire_service_loops])
        resistance += sum([terminal.resistance for terminal in self.terminals])

        load = sum([terminal.load for terminal in self.terminals if not terminal.is_start])
        volts = self.start_terminal.volts

        return (volts / resistance) + load

    @property
    def total_circuit_weight_g(self) -> _decimal:
        return self.terminal_weight_g + self.wire_weight_g + self.splice_weight_g

    @property
    def total_circuit_weight_lb(self) -> _decimal:
        return self.terminal_weight_lb + self.wire_weight_lb + self.splice_weight_lb

    @property
    def wire_length_mm(self) -> _decimal:
        wire_length = sum([wire.length_mm for wire in self.wires])
        wire_length += sum([loop.length_mm for loop in self.wire_service_loops])
        return wire_length

    @property
    def wire_length_m(self) -> _decimal:
        return self.wire_length_mm / _decimal(1000.0)

    @property
    def wire_length_ft(self) -> _decimal:
        return self.wire_length_m * _decimal(3.28084)

    @property
    def wire_weight_g(self) -> _decimal:
        wire_weight = sum([wire.weight_g for wire in self.wires])
        wire_weight += sum([loop.weight_g for loop in self.wire_service_loops])
        return wire_weight

    @property
    def wire_weight_lb(self) -> _decimal:
        return sum([wire.weight_lb for wire in self.wires])

    @property
    def terminal_weight_g(self) -> _decimal:
        return sum([terminal.part.weight for terminal in self.terminals])

    @property
    def terminal_weight_lb(self) -> _decimal:
        weight_g = self.terminal_weight_g
        return weight_g * _decimal(0.00220462)

    @property
    def splice_weight_g(self) -> _decimal:
        return sum([splice.part.weight for splice in self.splices])

    @property
    def splice_weight_lb(self) -> _decimal:
        weight_g = self.splice_weight_g
        return weight_g * _decimal(0.00220462)

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
