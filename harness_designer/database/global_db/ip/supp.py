# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from ..bases import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)


class IPSuppsTable(TableBase):
    """Represent an ip supps table in :mod:`harness_designer.database.global_db.ip.supp`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'ip_supps'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ...create_database import ip_supps

        return ip_supps.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ...create_database import ip_supps

        ip_supps.table.add_to_db(self)
        ip_supps.add_records(self._con, splash)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ...create_database import ip_supps

        ip_supps.table.update_fields(self)

    def __getitem__(self, item) -> "IPSupp":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPSupp`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return IPSupp(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return IPSupp(self, db_id[0][0])

        raise KeyError(item)

    def __iter__(self) -> _Iterable["IPSupp"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['IPSupp']
        """
        for db_id in TableBase.__iter__(self):
            yield IPSupp(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPSupp":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param short_desc: Value for ``short_desc``.
        :type short_desc: str
        :param description: Value for ``description``.
        :type description: str
        :param icon_data: Value for ``icon_data``.
        :type icon_data: bytes | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPSupp`
        """
        db_id = TableBase.insert(self, name=name, description=description)
        return IPSupp(self, db_id)


class IPSupp(EntryBase, NameMixin, DescriptionMixin):
    """Represent an ip supp in :mod:`harness_designer.database.global_db.ip.supp`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: IPSuppsTable = None
