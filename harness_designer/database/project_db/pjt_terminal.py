from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from . import pjt_seal as _pjt_seal
from . import pjt_circuit as _pjt_circuit
from ..global_db import terminal as _terminal
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Angle2DMixin, Angle2DControl,
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    HousingMixin
)


from ... import logger as _logger

if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity

    from ...objects import terminal as _terminal_obj


class PJTTerminalsTable(PJTTableBase):
    __table_name__ = 'pjt_terminals'

    _control: "PJTTerminalControl" = None

    @property
    def control(self) -> "PJTTerminalControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTTerminalControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import terminals

        return terminals.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import terminals

        terminals.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import terminals

        terminals.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTTerminal"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTerminal(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTerminal":
        if isinstance(item, int):
            if item in self:
                return PJTTerminal(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position2d_id: int, position3d_id: int, cavity_id: int) -> "PJTTerminal":

        db_id = PJTTableBase.insert(self, part_id=part_id, cavity_id=cavity_id,
                                    point2d_id=position2d_id, point3d_id=position3d_id)

        return PJTTerminal(self, db_id, self.project_id)


class PJTTerminal(PJTEntryBase, Angle3DMixin, Angle2DMixin, Position3DMixin, NotesMixin,
                  Position2DMixin, PartMixin, Visible3DMixin, Visible2DMixin, NameMixin,
                  HousingMixin):

    _table: PJTTerminalsTable = None

    def build_monitor_packet(self):
        circuit = self.circuit
        cavity = self.cavity

        packet = {
            'pjt_terminals': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id]
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        if cavity is not None:
            self.merge_packet_data(cavity.build_monitor_packet(), packet)

        if circuit is not None:
            self.merge_packet_data(circuit.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_terminal_obj.Terminal":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_terminal_obj.Terminal"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def is_start(self) -> bool:
        value = bool(self._table.select('is_start', id=self._db_id)[0][0])
        if value and self.load:
            _logger.logger.warning('You cannot have a load set for the start terminal of a circuit')

            value = False
            self.is_start = False

        return value

    @is_start.setter
    def is_start(self, value: bool):
        if value and self.load:
            raise RuntimeError('You cannot have a load for '
                               'the start terminal of a circuit')

        if value:
            self.__check_for_other_starts()

        self._table.update(self._db_id, is_start=int(value))
        self._populate('is_start')

    def __check_for_other_starts(self):
        db_ids = self._table.select('db_id', circuit_id=self.circuit_id, is_start=1)
        for db_id in db_ids:
            if db_id[0] != self.db_id:
                _logger.logger.warning('A circuit cannot have multiple start points. setting '
                                       'other terminal so it is not a start point')

                self._table.update(db_id[0], is_start=0)

    @property
    def voltage_drop(self) -> float:
        if self.is_start:
            return 0.0

        return self._table.select('voltage_drop', id=self._db_id)[0][0]

    @voltage_drop.setter
    def voltage_drop(self, value: float):
        if self.is_start:
            raise RuntimeError('voltage from can only be applied '
                               'to the end terminal of a circuit')

        self._table.update(self._db_id, voltage_drop=value)
        self._populate('voltage_drop')

    @property
    def resistance(self) -> float:
        return self.part.resistance

    @property
    def volts(self) -> float:
        if not self.is_start:
            return 0.0

        return self._table.select('volts', id=self._db_id)[0][0]

    @volts.setter
    def volts(self, value: float):
        if self.is_start:
            raise RuntimeError('volts can only be applied to the start terminal '
                               'not the end terminals of a circuit')

        self._table.update(self._db_id, volts=value)
        self._populate('volts')

    @property
    def load(self) -> float:
        if self.is_start:
            return 0.0

        return self._table.select('load', id=self._db_id)[0][0]

    @load.setter
    def load(self, value: float):
        if self.is_start:
            raise RuntimeError('loads can only be applied to the end terminals '
                               'not the start terminals of a circuit')

        self._table.update(self._db_id, load=value)
        self._populate('load')

    @property
    def table(self) -> PJTTerminalsTable:
        return self._table

    _stored_cavity: "_pjt_cavity.PJTCavity" = None

    @property
    def cavity(self) -> "_pjt_cavity.PJTCavity":
        if self._stored_cavity is None and self._obj is not None:
            cavity_id = self.cavity_id

            if cavity_id is None:
                return None

            self._stored_cavity = self._table.db.pjt_cavities_table[cavity_id]
            self._stored_cavity.add_object(self._obj())

        return self._stored_cavity

    @property
    def cavity_id(self) -> int:
        return self._table.select('cavity_id', id=self._db_id)[0][0]

    @cavity_id.setter
    def cavity_id(self, value: int):
        self._stored_cavity = None

        self._table.update(self._db_id, cavity_id=value)
        self._populate('cavity_id')

    _stored_circuit: "_pjt_circuit.PJTCircuit" = None

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        if self._stored_circuit is None and self._obj is not None:
            circuit_id = self.circuit_id

            if circuit_id is None:
                return

            self._stored_circuit = self._table.db.pjt_circuits_table[circuit_id]
            self._stored_circuit.add_object(self._obj())

        return self._stored_circuit

    @property
    def circuit_id(self) -> int:
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int):
        self._stored_circuit = None

        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        db_ids = self._table.db.pjt_seals_table.select('id', terminal_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    _stored_part: "_terminal.Terminal" = None

    @property
    def part(self) -> "_terminal.Terminal":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.terminals_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTTerminalControl(wx.Notebook):

    def set_obj(self, db_obj: PJTTerminal):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)

        self.angle2d_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)

        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)

        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.is_start_ctrl.SetValue(False)
            self.voltage_drop_ctrl.SetValue(0.0)
            self.volts_ctrl.SetValue(0.0)
            self.load_ctrl.SetValue(0.0)

            self.is_start_ctrl.Enable(False)
            self.voltage_drop_ctrl.Enable(False)
            self.volts_ctrl.Enable(False)
            self.load_ctrl.Enable(False)

            self.seal_ctrl.set_obj(None)
            self.terminal_ctrl.set_obj(None)
            self.circuit_ctrl.set_obj(None)

        else:

            is_start = db_obj.is_start

            self.is_start_ctrl.SetValue(is_start)

            if is_start:
                self.voltage_drop_ctrl.Enable(True)
                self.volts_ctrl.Enable(True)
                self.voltage_drop_ctrl.SetValue(db_obj.voltage_drop)
                self.volts_ctrl.SetValue(db_obj.volts)

                self.load_ctrl.Enable(False)
                self.load_ctrl.SetValue(0.0)
            else:
                self.voltage_drop_ctrl.Enable(False)
                self.volts_ctrl.Enable(False)
                self.voltage_drop_ctrl.SetValue(0.0)
                self.volts_ctrl.SetValue(0.0)

                self.load_ctrl.Enable(True)
                self.load_ctrl.SetValue(db_obj.load)

            self.seal_ctrl.set_obj(db_obj.seal)
            self.terminal_ctrl.set_obj(db_obj.part)
            self.circuit_ctrl.set_obj(db_obj.circuit)

    def __init__(self, parent):
        self.db_obj: PJTTerminal = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        self.is_start_ctrl = _prop_grid.BoolProperty(general_page, 'Is Start')
        self.voltage_drop_ctrl = _prop_grid.FloatProperty(general_page, 'Allowed Voltage Drop', min_value=0.0, max_value=9999.99, increment=0.01, units='VDC/VAC')
        self.volts_ctrl = _prop_grid.FloatProperty(general_page, 'Volts', min_value=0.0, max_value=44000.00, increment=0.01, units='VDC/VAC')
        self.load_ctrl = _prop_grid.FloatProperty(general_page, 'Load', min_value=0.0, max_value=9999.99, increment=0.01, units='A')

        angle_page = _prop_grid.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        seal_page = _prop_grid.Category(self, 'Seal')
        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        circuit_page = _prop_grid.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.terminal_ctrl = _terminal.TerminalControl(part_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            seal_page,
            circuit_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
