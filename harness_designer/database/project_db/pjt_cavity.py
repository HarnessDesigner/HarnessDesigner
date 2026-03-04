
from typing import Iterable as _Iterable, TYPE_CHECKING

from . import PJTEntryBase, PJTTableBase
from .mixins import (Angle3DMixin, Angle2DMixin, Position3DMixin, Position2DMixin,
                     HousingMixin, PartMixin, NameMixin)


if TYPE_CHECKING:
    from . import pjt_seal as _pjt_seal
    from . import pjt_terminal as _pjt_terminal
    from ..global_db import cavity as _cavity

    from ...objects import cavity as _cavity_obj


class PJTCavitiesTable(PJTTableBase):
    __table_name__ = 'pjt_cavities'

    def __iter__(self) -> _Iterable["PJTCavity"]:

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCavity(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCavity":
        if isinstance(item, int):
            if item in self:
                return PJTCavity(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int) -> "PJTCavity":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTCavity(self, db_id, self.project_id)


class PJTCavity(PJTEntryBase, Angle3DMixin, Angle2DMixin, Position3DMixin,
                Position2DMixin, HousingMixin, PartMixin, NameMixin):

    _table: PJTCavitiesTable = None

    def get_object(self) -> "_cavity_obj.Cavity":
        return self._obj

    def set_object(self, obj: "_cavity_obj.Cavity"):
        self._obj = obj

    @property
    def table(self) -> PJTCavitiesTable:
        return self._table

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        terminal_ids = self._table.db.pjt_terminals_table.select('id', cavity_id=self._db_id)

        if not terminal_ids:
            return None

        return self._table.db.pjt_terminals_table[terminal_ids[0][0]]

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        seal_ids = self._table.db.pjt_seals_table.select('id', cavity_id=self._db_id)

        if not seal_ids:
            return None

        return self._table.db.pjt_seals_table[seal_ids[0][0]]

    @property
    def part(self) -> "_cavity.Cavity":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cavities_table[part_id]
