from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (Angle3DMixin, Position3DMixin, PartMixin, HousingMixin,
                     Visible3DMixin, NameMixin, NotesMixin)


if TYPE_CHECKING:
    from ..global_db import cpa_lock as _cpa_lock

    from ...objects import cpa_lock as _cpa_lock_obj


class PJTCPALocksTable(PJTTableBase):
    __table_name__ = 'pjt_cpa_locks'

    def _table_needs_update(self) -> bool:
        from ..create_database import cpa_locks

        return cpa_locks.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import cpa_locks

        cpa_locks.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import cpa_locks

        cpa_locks.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCPALock"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCPALock(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCPALock":
        if isinstance(item, int):
            if item in self:
                return PJTCPALock(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d_id: int, housing_id: int | None) -> "PJTCPALock":
        db_id = PJTTableBase.insert(
            self, part_id=part_id, position3d_id=position3d_id, housing_id=housing_id)

        return PJTCPALock(self, db_id, self.project_id)


class PJTCPALock(PJTEntryBase, Angle3DMixin, Position3DMixin, NotesMixin,
                 PartMixin, HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTCPALocksTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_cpa_locks': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_cpa_lock_obj.CPALock":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_cpa_lock_obj.CPALock"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTCPALocksTable:
        return self._table

    _stored_part: "_cpa_lock.CPALock" = None

    @property
    def part(self) -> "_cpa_lock.CPALock":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.cpa_locks_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def propgrid(self) -> tuple[_prop_grid.Category, _prop_grid.Category]:
        group = _prop_grid.Category('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid
        angle_prop = self._angle3d_propgrid
        position_prop = self._position3d_propgrid
        housing_prop = self._housing_propgrid
        visible_prop = self._visible3d_propgrid

        group.Append(name_prop)
        group.Append(notes_prop)
        group.Append(angle_prop)
        group.Append(position_prop)
        group.Append(visible_prop)
        group.Append(housing_prop)

        part_prop = self._part_propgrid

        return group, part_prop
