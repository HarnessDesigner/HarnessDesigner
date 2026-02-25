from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, HousingMixin, Visible3DMixin


if TYPE_CHECKING:
    from . import pjt_terminal as _pjt_terminal
    from ..global_db import seal as _seal


class PJTSealsTable(PJTTableBase):
    __table_name__ = 'pjt_seals'

    def __iter__(self) -> _Iterable["PJTSeal"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSeal(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTSeal":
        if isinstance(item, int):
            if item in self:
                return PJTSeal(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None, terminal_id: int | None) -> "PJTSeal":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id, terminal_id=terminal_id)

        return PJTSeal(self, db_id, self.project_id)


class PJTSeal(PJTEntryBase, Angle3DMixin, Position3DMixin,
              PartMixin, HousingMixin, Visible3DMixin):
    _table: PJTSealsTable = None

    @property
    def table(self) -> PJTSealsTable:
        return self._table

    @property
    def part(self) -> "_seal.Seal":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.seals_table[part_id]

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        db_id = self.terminal_id
        if db_id is None:
            return None

        return self._table.db.pjt_terminals_table[db_id]

    @property
    def terminal_id(self) -> int:
        return self._table.select('terminal_id', id=self._db_id)[0][0]

    @terminal_id.setter
    def terminal_id(self, value: int):
        self._table.update(self._db_id, terminal_id=value)
        self._process_callbacks()
