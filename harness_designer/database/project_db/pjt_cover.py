from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, HousingMixin, Visible3DMixin


if TYPE_CHECKING:
    from ..global_db import cover as _cover


class PJTCoversTable(PJTTableBase):
    __table_name__ = 'pjt_covers'

    def __iter__(self) -> _Iterable["PJTCover"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCover(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCover":
        if isinstance(item, int):
            if item in self:
                return PJTCover(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None) -> "PJTCover":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTCover(self, db_id, self.project_id)


class PJTCover(PJTEntryBase, Angle3DMixin, Position3DMixin,
               PartMixin, HousingMixin, Visible3DMixin):

    _table: PJTCoversTable = None

    @property
    def table(self) -> PJTCoversTable:
        return self._table

    @property
    def part(self) -> "_cover.Cover":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.covers_table[part_id]
