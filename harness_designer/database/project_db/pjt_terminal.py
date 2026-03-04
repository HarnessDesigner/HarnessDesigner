from typing import TYPE_CHECKING, Iterable as _Iterable

import numpy as np

from .pjt_bases import PJTEntryBase, PJTTableBase

from .mixins import (Angle3DMixin, Angle2DMixin, Position3DMixin, Position2DMixin,
                     PartMixin, Visible3DMixin, Visible2DMixin, NameMixin)


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_seal as _pjt_seal

    from ..global_db import terminal as _terminal

    from ...objects import terminal as _terminal_obj


class PJTTerminalsTable(PJTTableBase):
    __table_name__ = 'pjt_terminals'

    def __iter__(self) -> _Iterable["PJTTerminal"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTerminal(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTerminal":
        if isinstance(item, int):
            if item in self:
                return PJTTerminal(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, cavity_id: int, circuit_id: int,
               point3d_id: int, point2d_id: int, angle: float,
               quat: np.ndarray, is_start: bool, volts: float,
               load: float, voltage_drop: float) -> "PJTTerminal":

        db_id = PJTTableBase.insert(self, part_id=part_id, cavity_id=cavity_id,
                                    circuit_id=circuit_id, point3d_id=point3d_id,
                                    point2d_id=point2d_id, angle=float(angle),
                                    quat=str(quat.tolist()), is_start=int(is_start),
                                    volts=float(volts), load=float(load),
                                    voltage_drop=float(voltage_drop))

        return PJTTerminal(self, db_id, self.project_id)


class PJTTerminal(PJTEntryBase, Angle3DMixin, Angle2DMixin, Position3DMixin,
                  Position2DMixin, PartMixin, Visible3DMixin, Visible2DMixin, NameMixin):

    _table: PJTTerminalsTable = None

    def get_object(self) -> "_terminal_obj.Terminal":
        return self._obj

    def set_object(self, obj: "_terminal_obj.Terminal"):
        self._obj = obj

    @property
    def is_start(self) -> bool:
        value = bool(self._table.select('is_start', id=self._db_id)[0][0])
        if value and self.load:
            print('You cannot have a load set for the start terminal of a circuit')

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
        self._process_callbacks()

    def __check_for_other_starts(self):
        db_ids = self._table.select('db_id', circuit_id=self.circuit_id, is_start=1)
        for db_id in db_ids:
            if db_id[0] != self.db_id:
                print('A circuit cannot have multiple start points. setting '
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
        self._process_callbacks()

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
        self._process_callbacks()

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
        self._process_callbacks()

    @property
    def table(self) -> PJTTerminalsTable:
        return self._table

    @property
    def cavity(self) -> "_pjt_cavity.PJTCavity":
        cavity_id = self.cavity_id
        return self._table.db.pjt_cavities_table[cavity_id]

    @property
    def cavity_id(self) -> int:
        return self._table.select('cavity_id', id=self._db_id)[0][0]

    @cavity_id.setter
    def cavity_id(self, value: int):
        self._table.update(self._db_id, cavity_id=value)
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
    def seal(self) -> "_pjt_seal.PJTSeal":
        db_ids = self._table.db.pjt_seals_table.select('id', terminal_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    def part(self) -> "_terminal.Terminal":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.terminals_table[part_id]
