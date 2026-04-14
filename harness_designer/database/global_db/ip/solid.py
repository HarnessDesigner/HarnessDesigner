from typing import Iterable as _Iterable

from ..bases import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)

from .... import image as _image


class IPSolidsTable(TableBase):
    __table_name__ = 'ip_solids'

    def _table_needs_update(self) -> bool:
        from ...create_database import ip_solids

        return ip_solids.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ...create_database import ip_solids

        ip_solids.table.add_to_db(self)
        ip_solids.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ...create_database import ip_solids

        ip_solids.table.update_fields(self)

    def __getitem__(self, item) -> "IPSolid":
        if isinstance(item, int):
            if item in self:
                return IPSolid(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return IPSolid(self, db_id[0][0])

        raise KeyError(item)

    def __iter__(self) -> _Iterable["IPSolid"]:
        for db_id in TableBase.__iter__(self):
            yield IPSolid(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPSolid":
        db_id = TableBase.insert(self, name=name, short_desc=short_desc, description=description, icon_data=icon_data)
        return IPSolid(self, db_id)


class IPSolid(EntryBase, NameMixin, DescriptionMixin):
    _table: IPSolidsTable = None

    @property
    def short_desc(self) -> str:
        return self._table.select('short_desc', id=self._db_id)[0][0]

    @short_desc.setter
    def short_desc(self, value: str):
        self._table.update(self._db_id, short_desc=value)

    @property
    def icon(self) -> _image.Image:
        return getattr(_image.ip, f'IP{self.name}X')
