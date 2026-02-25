from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import angle as _angle
import uuid

if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_cover as _pjt_cover
    from . import pjt_tpa_lock as _pjt_tpa_lock
    from . import pjt_cpa_lock as _pjt_cpa_lock
    from . import pjt_seal as _pjt_seal
    from . import pjt_boot as _pjt_boot
    from . import pjt_accessory as _pjt_accessory

    from ..global_db import housing as _housing


class PJTHousingsTable(PJTTableBase):
    __table_name__ = 'pjt_housings'

    def __iter__(self) -> _Iterable["PJTHousing"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTHousing(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTHousing":
        if isinstance(item, int):
            if item in self:
                return PJTHousing(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str, point3d_id: int, point2d_id: int,
               angle3d: _angle.Angle, angle2d: _decimal) -> "PJTHousing":

        db_id = PJTTableBase.insert(self, part_id=part_id, name=name, point3d_id=point3d_id,
                                    point2d_id=point2d_id, angle3d=str(list(angle3d.as_float)),
                                    angle2d=float(angle2d))

        return PJTHousing(self, db_id, self.project_id)


class PJTHousing(PJTEntryBase):
    _table: PJTHousingsTable = None
    _angle_id: str = None

    @property
    def table(self) -> PJTHousingsTable:
        return self._table

    @property
    def cavities(self) -> list["_pjt_cavity.PJTCavity"]:
        cavities = [None] * self.part.num_pins

        cavity_ids = self._table.db.pjt_cavities_table.select(
            'id', cavity_map_id=self._db_id)

        for cavity_id in cavity_ids:
            cavity = _pjt_cavity.PJTCavity(
                self._table.db.pjt_cavities_table, cavity_id[0], self.project_id)

            cavities[cavity.part.idx] = cavity

        return cavities

    def add_cavity(self, index, name):
        cavities = self.cavities
        assert cavities[index] is None, 'Sanity Check'

        part = self.part
        cavity_part = part.cavities[index]

        if name is None:
            name = cavity_part.name

        cavity = self._table.db.pjt_cavities_table.insert(
            part_id=cavity_part.db_id, cavity_map_id=self._db_id,
            name=name, terminal_id=None)

        self._process_callbacks()
        return cavity

    @property
    def point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point_id = self.point3d_id
        if point_id is None:
            return None

        return self._table.db.pjt_points3d_table[point_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
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
    def angle2d(self) -> _decimal:
        return _decimal(self._table.select('angle2d', id=self._db_id)[0][0])

    @angle2d.setter
    def angle2d(self, value: _decimal):
        self._table.update(self._db_id, angle2d=float(value))
        self._process_callbacks()

    @property
    def point2d(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.point2d_id
        if point_id is None:
            return None

        return self._table.db.pjt_points2d_table[point_id]

    @property
    def point2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    def point2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)
        self._process_callbacks()

    @property
    def seals(self) -> list["_pjt_seal.PJTSeal"]:
        res = []
        db_ids = self._table.db.pjt_seals_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            res.append(seal)

        return res

    @property
    def cpa_locks(self) -> list["_pjt_cpa_lock.PJTCPALock"]:
        res = []
        db_ids = self._table.db.pjt_cpa_locks_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                cpa_lock = self._table.db.pjt_cpa_locks_table[db_id[0]]
            except IndexError:
                continue

            res.append(cpa_lock)

        return res

    @property
    def tpa_locks(self) -> list["_pjt_tpa_lock.PJTTPALock"]:
        res = []
        db_ids = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                tpa_lock = self._table.db.pjt_tpa_locks_table[db_id[0]]
            except IndexError:
                continue

            res.append(tpa_lock)
        return res

    @property
    def cover(self) -> "_pjt_cover.PJTCover":
        db_ids = self._table.db.pjt_covers_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                cover = self._table.db.pjt_covers_table[db_id[0]]
            except IndexError:
                continue

            return cover

    @property
    def boot(self) -> "_pjt_boot.PJTBoot":
        db_ids = self._table.db.pjt_boots_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                boot = self._table.db.pjt_boots_table[db_id[0]]
            except IndexError:
                continue

            return boot

    @property
    def accessories(self) -> list["_pjt_accessory.PJTAccessory"]:
        res = []
        db_ids = self._table.db.pjt_accessories_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                accessory = self._table.db.pjt_accessories_table[db_id]
            except IndexError:
                continue

            res.append(accessory)
        return res

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def part(self) -> "_housing.Housing":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.housings_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
