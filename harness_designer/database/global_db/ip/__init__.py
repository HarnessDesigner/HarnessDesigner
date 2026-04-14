from typing import Iterable as _Iterable
import wx

from ....ui.editor_obj import prop_grid as _prop_grid

from ..bases import EntryBase, TableBase

from . import solid as _solid
from . import fluid as _fluid
from . import supp as _supp


class IPRatingsTable(TableBase):
    __table_name__ = 'ip_ratings'

    def _table_needs_update(self) -> bool:
        from ...create_database import ip_ratings

        return ip_ratings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ...create_database import ip_ratings

        ip_ratings.table.add_to_db(self)
        ip_ratings.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ...create_database import ip_ratings

        ip_ratings.table.update_fields(self)

    def __iter__(self) -> _Iterable["IPRating"]:
        for db_id in TableBase.__iter__(self):
            yield IPRating(self, db_id)

    def __getitem__(self, item) -> "IPRating":
        if isinstance(item, int):
            if item in self:
                return IPRating(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return IPRating(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, solid_id: int, fluid_id: int, supp_id: int) -> "IPRating":
        db_id = TableBase.insert(self, name=name, solid_id=solid_id, fluid_id=fluid_id, supp_id=supp_id)
        return IPRating(self, db_id)


class IPRating(EntryBase):
    _table: IPRatingsTable = None

    def build_monitor_packet(self):
        packet = {
            'ip_ratings': [self.db_id],
            'ip_solids': [self.ip_solid_id],
            'ip_fluids': [self.ip_fluid_id],
            'ip_supps': [self.ip_supp_id]
        }

        return packet

    @property
    def name(self):
        return self._table.select('name', id=self._db_id)[0][0]

    @property
    def ip_solid(self) -> _solid.IPSolid:
        ip_solid_id = self.ip_solid_id
        return self._table.db.ip_solids_table[ip_solid_id]

    @ip_solid.setter
    def ip_solid(self, value: _solid.IPSolid):
        self._table.update(self._db_id, solid_id=value.db_id)

    @property
    def ip_solid_id(self) -> int:
        return self._table.select('solid_id', id=self._db_id)[0][0]

    @ip_solid_id.setter
    def ip_solid_id(self, value: int):
        self._table.update(self._db_id, solid_id=value)

    @property
    def ip_fluid(self) -> _fluid.IPFluid:
        ip_fluid_id = self.ip_fluid_id
        return self._table.db.ip_fluids_table[ip_fluid_id]

    @ip_fluid.setter
    def ip_fluid(self, value: _fluid.IPFluid):
        self._table.update(self._db_id, fluid_id=value.db_id)

    @property
    def ip_fluid_id(self) -> int:
        return self._table.select('fluid_id', id=self._db_id)[0][0]

    @ip_fluid_id.setter
    def ip_fluid_id(self, value: int):
        self._table.update(self._db_id, fluid_id=value)

    @property
    def ip_supp(self) -> _supp.IPSupp | None:
        ip_supp_id = self.ip_supp_id
        if ip_supp_id is None:
            return None

        return self._table.db.ip_supps_table[ip_supp_id]

    @ip_supp.setter
    def ip_supp(self, value: _supp.IPSupp | None):
        if value is None:
            self._table.update(self._db_id, supp_id=None)
        else:
            self._table.update(self._db_id, supp_id=value.db_id)

    @property
    def ip_supp_id(self) -> int | None:
        return self._table.select('supp_id', id=self._db_id)[0][0]

    @ip_supp_id.setter
    def ip_supp_id(self, value: int | None):
        self._table.update(self._db_id, supp_id=value)

    @property
    def short_desc(self) -> str:
        supp = self.ip_supp
        if supp is None:
            return f'{self.ip_solid.short_desc}\n{self.ip_fluid.short_desc}'

        return f'{self.ip_solid.short_desc}\n{self.ip_fluid.short_desc}\n{supp.description}'

    @property
    def description(self) -> str:
        supp = self.ip_supp
        if supp is None:
            return f'{self.ip_solid.description}\n\n{self.ip_fluid.description}'

        return f'{self.ip_solid.description}\n\n{self.ip_fluid.description}\n\n{supp.description}'

    @property
    def bitmap(self) -> wx.Bitmap:
        simg = self.ip_solid.icon
        fimg = self.ip_fluid.icon

        img = simg | fimg

        return img.bitmap

    @property
    def propgrid(self) -> _prop_grid.Property:
        choices = []

        for ip_rating in self._table:
            choices.append([ip_rating.name, ip_rating.bitmap, ip_rating.description])

        prop = _prop_grid.BitmapComboBoxProperty('IP Rating', 'ip_rating', self.name, choices)
        return prop
