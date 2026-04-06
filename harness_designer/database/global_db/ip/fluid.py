from typing import Iterable as _Iterable

from ..bases import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)

from .... import image as _image


class IPFluidsTable(TableBase):
    __table_name__ = 'ip_fluids'

    def _table_needs_update(self) -> bool:
        from ...create_database import ip_fluids

        return ip_fluids.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ...create_database import ip_fluids

        ip_fluids.table.add_to_db(self)
        ip_fluids.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ...create_database import ip_fluids

        ip_fluids.table.update_fields(self)

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
    def icon(self) -> _image.Image:
        return getattr(_image.ip, f'IPX{self.name}')
