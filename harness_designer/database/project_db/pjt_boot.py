from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (Angle3DMixin, Position3DMixin, PartMixin, HousingMixin,
                     Visible3DMixin, NameMixin, NotesMixin)


if TYPE_CHECKING:
    from ..global_db import boot as _boot
    from ...objects import boot as _boot_obj


class PJTBootsTable(PJTTableBase):
    __table_name__ = 'pjt_boots'

    def get_from_position3d_id(self, position3d_id) -> "PJTBoot":
        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

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

    def insert(self, part_id: int, position3d_id: int, housing_id: int | None) -> "PJTBoot":
        db_id = PJTTableBase.insert(
            self, part_id=part_id, position3d_id=position3d_id, housing_id=housing_id)

        return PJTBoot(self, db_id, self.project_id)


class PJTBoot(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
              HousingMixin, Visible3DMixin, NameMixin, NotesMixin):

    _table: PJTBootsTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_boots': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_boot_obj.Boot":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_boot_obj.Boot"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTBootsTable:
        return self._table

    _stored_part: "_boot.Boot" = None

    @property
    def part(self) -> "_boot.Boot":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.boots_table[part_id]
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
