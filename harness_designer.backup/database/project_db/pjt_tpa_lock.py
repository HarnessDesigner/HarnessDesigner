from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
import uuid

from ...geometry import angle as _angle


if TYPE_CHECKING:
    from . import pjt_housing as _pjt_housing
    from . import pjt_point3d as _pjt_point3d

    from ..global_db import tpa_lock as _tpa_lock


class PJTTPALocksTable(PJTTableBase):
    __table_name__ = 'pjt_tpa_locks'

    def __iter__(self) -> _Iterable["PJTTPALock"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTPALock(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTPALock":
        if isinstance(item, int):
            if item in self:
                return PJTTPALock(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None) -> "PJTTPALock":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTTPALock(self, db_id, self.project_id)


class PJTTPALock(PJTEntryBase):
    _table: PJTTPALocksTable = None
    _angle_id: str = None

    @property
    def table(self) -> PJTTPALocksTable:
        return self._table

    @property
    def part(self) -> "_tpa_lock.TPALock":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cpa_locks_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()

    @property
    def housing(self) -> "_pjt_housing.PJTHousing":
        db_id = self.housing_id
        if db_id is None:
            return None

        return self._table.db.pjt_housings_table[db_id]

    @property
    def housing_id(self) -> int:
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @housing_id.setter
    def housing_id(self, value: int):
        self._table.update(self._db_id, housing_id=value)
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
