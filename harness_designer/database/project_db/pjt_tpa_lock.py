from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from wx import propgrid as wxpg

from .pjt_bases import PJTEntryBase, PJTTableBase

from .mixins import (Angle3DMixin, Position3DMixin, PartMixin,
                     HousingMixin, Visible3DMixin, NameMixin)


if TYPE_CHECKING:
    from ..global_db import tpa_lock as _tpa_lock

    from ...objects import tpa_lock as _tpa_lock_obj


class PJTTPALocksTable(PJTTableBase):
    __table_name__ = 'pjt_tpa_locks'

    def _table_needs_update(self) -> bool:
        from ..create_database import tpa_locks

        return tpa_locks.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import tpa_locks

        tpa_locks.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import tpa_locks

        tpa_locks.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTTPALock"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTPALock(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTPALock":
        if isinstance(item, int):
            if item in self:
                return PJTTPALock(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d_id: int, housing_id: int | None) -> "PJTTPALock":
        db_id = PJTTableBase.insert(
            self, part_id=part_id, position3d_id=position3d_id, housing_id=housing_id)

        return PJTTPALock(self, db_id, self.project_id)


class PJTTPALock(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
                 HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTTPALocksTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_tpa_locks': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_tpa_lock_obj.TPALock":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_tpa_lock_obj.TPALock"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def idx(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        self._table.update(self._db_id, idx=value)

    @property
    def table(self) -> PJTTPALocksTable:
        return self._table

    _stored_part: "_tpa_lock.TPALock" = None

    @property
    def part(self) -> "_tpa_lock.TPALock":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.cpa_locks_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def propgrid(self) -> wxpg.PGProperty:
        group = wxpg.PropertyCategory('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid
        angle_prop = self._angle3d_propgrid
        position_prop = self._position3d_propgrid
        housing_prop = self._housing_propgrid
        visible_prop = self._visible3d_propgrid

        group.AppendChild(name_prop)
        group.AppendChild(notes_prop)
        group.AppendChild(angle_prop)
        group.AppendChild(position_prop)
        group.AppendChild(visible_prop)
        group.AppendChild(housing_prop)

        part_prop = self._part_propgrid

        return group, part_prop
