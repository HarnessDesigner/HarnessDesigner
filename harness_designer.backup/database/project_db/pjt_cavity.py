
from typing import Iterable as _Iterable, TYPE_CHECKING

from . import PJTEntryBase, PJTTableBase
import uuid
from ...geometry import angle as _angle


if TYPE_CHECKING:
    from . import pjt_housing as _pjt_housing
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_point3d as _pjt_point3d
    from ..global_db import cavity as _cavity


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

    def insert(self, part_id: int, cavity_map_id: int, terminal_id: int, name: str) -> "PJTCavity":
        db_id = PJTTableBase.insert(self, part_id=part_id, cavity_map_id=cavity_map_id,
                                    terminal_id=terminal_id, name=name)

        return PJTCavity(self, db_id, self.project_id)


class PJTCavity(PJTEntryBase):
    _table: PJTCavitiesTable = None
    _angle_id: str = None

    @property
    def table(self) -> PJTCavitiesTable:
        return self._table

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)
        self._process_callbacks()

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
        self._process_callbacks()

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        terminal_ids = self._table.db.pjt_terminals_table.select('id', cavity_id=self._db_id)

        if not terminal_ids:
            return None

        return self._table.db.pjt_terminals_table[terminal_ids[0][0]]

    @property
    def part(self) -> "_cavity.Cavity":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cavities_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()

    def __update_angle(self, angle: _angle.Angle):
        self._table.update(self._db_id, quat=str(angle.as_quat))
        self._process_callbacks()

    @property
    def angle3d(self) -> _angle.Angle:
        if self._angle_id is None:
            self._angle_id = str(uuid.uuid4())

        quat = eval(self._table.select('quat', id=self._db_id)[0][0])
        angle = _angle.Angle.from_quat(quat, db_id=self._angle_id)
        angle.bind(self.__update_angle)
        return angle

    @property
    def point3d(self) -> "_pjt_point3d.PJTPoint3D":
        return self._table.db.pjt_points3d_table[self.point3d_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
        self._process_callbacks()
