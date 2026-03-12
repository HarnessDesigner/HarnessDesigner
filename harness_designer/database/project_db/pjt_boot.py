from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, HousingMixin, Visible3DMixin, NameMixin


if TYPE_CHECKING:
    from ..global_db import boot as _boot
    from ...objects import boot as _boot_obj


class PJTBootsTable(PJTTableBase):
    __table_name__ = 'pjt_boots'

    def _table_needs_update(self) -> bool:
        from ..create_database import boots

        return boots.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import boots

        boots.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import boots

        boots.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTBoot"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBoot(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBoot":
        if isinstance(item, int):
            if item in self:
                return PJTBoot(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None) -> "PJTBoot":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTBoot(self, db_id, self.project_id)


class PJTBoot(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
              HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTBootsTable = None

    def get_object(self) -> "_boot_obj.Boot":
        return self._obj

    def set_object(self, obj: "_boot_obj.Boot"):
        self._obj = obj

    @property
    def table(self) -> PJTBootsTable:
        return self._table

    @property
    def part(self) -> "_boot.Boot":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.boots_table[part_id]
