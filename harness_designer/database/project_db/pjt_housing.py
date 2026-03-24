from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point

from .mixins import (Angle3DMixin, Angle2DMixin, Position3DMixin, Position2DMixin,
                     NameMixin, PartMixin, Visible3DMixin, Visible2DMixin)


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_cover as _pjt_cover
    from . import pjt_tpa_lock as _pjt_tpa_lock
    from . import pjt_cpa_lock as _pjt_cpa_lock
    from . import pjt_seal as _pjt_seal
    from . import pjt_boot as _pjt_boot
    from . import pjt_accessory as _pjt_accessory

    from ..global_db import housing as _housing

    from ...objects import housing as _housing_obj


class PJTHousingsTable(PJTTableBase):
    __table_name__ = 'pjt_housings'

    def _table_needs_update(self) -> bool:
        from ..create_database import housings

        return housings.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import housings

        housings.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import housings

        housings.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTHousing"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTHousing(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTHousing":
        if isinstance(item, int):
            if item in self:
                return PJTHousing(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d: "_point.Point" = None, position2d: "_point.Point" = None) -> "PJTHousing":
        if position2d is None:
            position2d = _point.Point(0, 0)

        if position3d is None:
            position3d = _point.Point(0.0, 0.0, 0.0)

        x, y = position3d.as_float[:-1]
        pos2d = self.db.pjt_points2d_table.insert(x, y)

        x, y, z = position3d.as_float
        pos3d = self.db.pjt_points3d_table.insert(x, y, z)

        db_id = PJTTableBase.insert(self, point3d_id=pos3d.db_id, point2d_id=pos2d.db_id, part_id=part_id)

        return PJTHousing(self, db_id, self.project_id)


class PJTHousing(PJTEntryBase, Angle3DMixin, Angle2DMixin, Position3DMixin,
                 Position2DMixin, NameMixin, PartMixin, Visible3DMixin, Visible2DMixin):

    _table: PJTHousingsTable = None

    def get_object(self) -> "_housing_obj.Housing":
        return self._obj

    def set_object(self, obj: "_housing_obj.Housing"):
        self._obj = obj

    @property
    def table(self) -> PJTHousingsTable:
        return self._table

    @property
    def cavities(self) -> list["_pjt_cavity.PJTCavity"]:
        cavities = []

        cavity_ids = self._table.db.pjt_cavities_table.select(
            'id', housing_id=self._db_id)

        for cavity_id in cavity_ids:
            cavity = _pjt_cavity.PJTCavity(
                self._table.db.pjt_cavities_table, cavity_id[0], self.project_id)

            cavities.append(cavity)

        return cavities
        
    def __update_cover_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def cover_position3d(self) -> "_point.Point":
        point_id = self.cover_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        point = _point.Point(*rows[0], db_id=str(point_id))
        point.bind(self.__update_cover_position3d)
        return point

    @property
    def cover_position3d_id(self) -> int:
        point_id = self._table.select('cover_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.cover_position3d_id = point_id

        return point_id

    @cover_position3d_id.setter
    def cover_position3d_id(self, value: int):
        self._table.update(self._db_id, cover_point3d_id=value)
    
    def __update_seal_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def seal_position3d(self) -> "_point.Point":
        point_id = self.seal_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self.__update_seal_position3d)
            return point

    @property
    def seal_position3d_id(self) -> int:
        point_id = self._table.select('seal_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.seal_position3d_id = point_id

        return point_id

    @seal_position3d_id.setter
    def seal_position3d_id(self, value: int):
        self._table.update(self._db_id, seal_point3d_id=value)

    def __update_boot_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def boot_position3d(self) -> "_point.Point":
        point_id = self.boot_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self.__update_boot_position3d)
            return point

    @property
    def boot_position3d_id(self) -> int:
        point_id = self._table.select('boot_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.boot_position3d_id = point_id

        return point_id

    @boot_position3d_id.setter
    def boot_position3d_id(self, value: int):
        self._table.update(self._db_id, boot_point3d_id=value)

    def __update_tpa_lock_1_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def tpa_lock_1_position3d(self) -> "_point.Point":
        point_id = self.tpa_lock_1_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self.__update_tpa_lock_1_position3d)
            return point

    @property
    def tpa_lock_1_position3d_id(self) -> int:
        point_id = self._table.select('tpa_lock_1_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.tpa_lock_1_position3d_id = point_id

        return point_id

    @tpa_lock_1_position3d_id.setter
    def tpa_lock_1_position3d_id(self, value: int):
        self._table.update(self._db_id, tpa_lock_1_point3d_id=value)

    def __update_tpa_lock_2_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def tpa_lock_2_position3d(self) -> "_point.Point":
        point_id = self.tpa_lock_2_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self.__update_tpa_lock_2_position3d)
            return point

    @property
    def tpa_lock_2_position3d_id(self) -> int:
        point_id = self._table.select('tpa_lock_2_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.tpa_lock_2_position3d_id = point_id

        return point_id

    @tpa_lock_2_position3d_id.setter
    def tpa_lock_2_position3d_id(self, value: int):
        self._table.update(self._db_id, tpa_lock_2_point3d_id=value)

    def __update_cpa_lock_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def cpa_lock_position3d(self) -> "_point.Point":
        point_id = self.cpa_lock_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self.__update_cpa_lock_position3d)
            return point

    @property
    def cpa_lock_position3d_id(self) -> int:
        point_id = self._table.select('cpa_lock_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id
            self.cpa_lock_position3d_id = point_id

        return point_id

    @cpa_lock_position3d_id.setter
    def cpa_lock_position3d_id(self, value: int):
        self._table.update(self._db_id, cpa_lock_point3d_id=value)

    def add_cavity(self, index, name):
        cavities = self.cavities
        assert cavities[index] is None, 'Sanity Check'

        part = self.part
        cavity_part = part.cavities[index]

        if name is None:
            name = cavity_part.name

        cavity = self._table.db.pjt_cavities_table.insert(cavity_part.db_id, self.db_id)
        cavity.name = name

        self._process_callbacks()
        return cavity

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        db_ids = self._table.db.pjt_seals_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    def cpa_lock(self) -> "_pjt_cpa_lock.PJTCPALock":
        db_ids = self._table.db.pjt_cpa_locks_table.select('id', housing_id=self.db_id)
        for db_id in db_ids:
            try:
                cpa_lock = self._table.db.pjt_cpa_locks_table[db_id[0]]
            except IndexError:
                continue

            return cpa_lock

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
    def part(self) -> "_housing.Housing":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.housings_table[part_id]
