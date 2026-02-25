from typing import Iterable as _Iterable
import wx

from .. import EntryBase, TableBase

from . import solid as _solid
from . import fluid as _fluid
from . import supp as _supp


class IPRatingsTable(TableBase):
    __table_name__ = 'ip_ratings'

    def __iter__(self) -> _Iterable["IPRating"]:
        for db_id in TableBase.__iter__(self):
            yield IPRating(self, db_id)

    def insert(self, name: str, solid_id: int, fluid_id: int, supp_id: int) -> "IPRating":
        db_id = TableBase.insert(self, name=name, solid_id=solid_id, fluid_id=fluid_id, supp_id=supp_id)
        return IPRating(self, db_id)


class IPRating(EntryBase):
    _table: IPRatingsTable = None

    @property
    def name(self):
        return self._table.select('name', id=self._db_id)[0][0]

    @property
    def ip_solid(self) -> _solid.IPSolid:
        ip_solid_id = self._table.select('solid_id', id=self._db_id)
        return _solid.IPSolid(self, ip_solid_id[0][0])

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
        ip_fluid_id = self._table.select('fluid_id', id=self._db_id)
        return _fluid.IPFluid(self, ip_fluid_id[0][0])

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
        ip_supp_id = self._table.select('supp_id', id=self._db_id)

        if ip_supp_id is None:
            return None

        return _supp.IPSupp(self, ip_supp_id[0][0])

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
            return f'{self.ip_solid.description}\n{self.ip_fluid.description}'

        return f'{self.ip_solid.description}\n{self.ip_fluid.description}\n{supp.description}'

    @property
    def icon(self) -> wx.Bitmap:
        bmp = wx.Bitmap(200, 60, depth=32)

        solid_icon_data = self.ip_solid.icon_data
        fluid_icon_data = self.ip_fluid.icon_data

        if (solid_icon_data, fluid_icon_data) != (None, None):
            dc = wx.MemoryDC()
            dc.SelectObject(bmp)

            gcdc = wx.GCDC(dc)

            if solid_icon_data is not None:
                solid_icon = wx.Bitmap.FromPNGData(solid_icon_data)
                gcdc.DrawBitmap(solid_icon, 0, 0)

            if fluid_icon_data is not None:
                fluid_icon = wx.Bitmap.FromPNGData(fluid_icon_data)
                gcdc.DrawBitmap(fluid_icon, 100, 0)

            dc.SelectObject(wx.NullBitmap)
            gcdc.Destroy()
            del gcdc

            dc.Destroy()
            del dc

        return bmp
