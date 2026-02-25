from typing import Iterable as _Iterable

from .. import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)


class IPFluidsTable(TableBase):
    __table_name__ = 'ip_fluids'

    def __iter__(self) -> _Iterable["IPFluid"]:
        for db_id in TableBase.__iter__(self):
            yield IPFluid(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPFluid":
        db_id = TableBase.insert(self, name=name, short_desc=short_desc, description=description, icon_data=icon_data)
        return IPFluid(self, db_id)


class IPFluid(EntryBase, NameMixin, DescriptionMixin):
    _table: IPFluidsTable = None

    @property
    def short_desc(self) -> str:
        return self._table.select('short_desc', id=self._db_id)[0][0]

    @short_desc.setter
    def short_desc(self, value: str):
        self._table.update(self._db_id, short_desc=value)

    @property
    def icon_data(self) -> bytes | None:
        return self._table.select('icon_data', id=self._db_id)[0][0]

    @icon_data.setter
    def icon_data(self, value: bytes | None):
        self._table.update(self._db_id, icon_data=value)
