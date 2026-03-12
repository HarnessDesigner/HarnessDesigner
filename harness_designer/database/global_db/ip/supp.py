from typing import Iterable as _Iterable

from ..bases import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)


class IPSuppsTable(TableBase):
    __table_name__ = 'ip_supps'

    def _table_needs_update(self) -> bool:
        from ...create_database import ip_supps

        return ip_supps.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ...create_database import ip_supps

        ip_supps.table.add_to_db(self)
        ip_supps.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ...create_database import ip_supps

        ip_supps.table.update_fields(self)

    def __iter__(self) -> _Iterable["IPSupp"]:
        for db_id in TableBase.__iter__(self):
            yield IPSupp(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPSupp":
        db_id = TableBase.insert(self, name=name, description=description)
        return IPSupp(self, db_id)


class IPSupp(EntryBase, NameMixin, DescriptionMixin):
    _table: IPSuppsTable = None
