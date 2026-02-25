from typing import Iterable as _Iterable

from .. import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)


class IPSuppsTable(TableBase):
    __table_name__ = 'ip_supps'

    def __iter__(self) -> _Iterable["IPSupp"]:
        for db_id in TableBase.__iter__(self):
            yield IPSupp(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPSupp":
        db_id = TableBase.insert(self, name=name, description=description)
        return IPSupp(self, db_id)


class IPSupp(EntryBase, NameMixin, DescriptionMixin):
    _table: IPSuppsTable = None
