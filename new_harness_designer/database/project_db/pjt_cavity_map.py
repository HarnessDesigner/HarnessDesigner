from typing import Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase


class PJTCavityMapsTable(PJTTableBase):
    __table_name__ = 'pjt_cavity_maps'

    def __iter__(self) -> _Iterable["PJTCavityMap"]:

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCavityMap(self, db_id, self.project_id)

    def insert(self, part_id: int, housing_id: int) -> "PJTCavityMap":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTCavityMap(self, db_id, self.project_id)


class PJTCavityMap(PJTEntryBase):
    _table: PJTCavityMapsTable = None

    @property
    def housing(self) -> "_pjt_housing.PJTHousing":
        housing_id = self.housing_id
        return self._table.db.pjt_housings_table[housing_id]

    @property
    def housing_id(self) -> int:
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @housing_id.setter
    def housing_id(self, value: int):
        self._table.update(self._db_id, housing_id=value)

    @property
    def part(self) -> "_cavity_map.CavityMap":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cavity_maps_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)


from . import pjt_cavity as _pjt_cavity  # NOQA
from . import pjt_housing as _pjt_housing  # NOQA
