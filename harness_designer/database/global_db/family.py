# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin, ManufacturerMixin


class FamiliesTable(TableBase):
    """Represent a families table in :mod:`harness_designer.database.global_db.family`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'families'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import families

        return families.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import families

        families.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        families.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import families

        families.table.update_fields(self)

    def __iter__(self) -> _Iterable["Family"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Family']
        """
        for db_id in TableBase.__iter__(self):
            yield Family(self, db_id)

    def __getitem__(self, item) -> "Family":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Family`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Family(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Family(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str, mfg_id: int, description: str) -> "Family":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Family`
        """
        db_id = TableBase.insert(self, name=name, mfg_id=mfg_id, description=description)
        return Family(self, db_id)


class Family(EntryBase, NameMixin, DescriptionMixin, ManufacturerMixin):
    """Represent a family in :mod:`harness_designer.database.global_db.family`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: FamiliesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'families': [self.db_id],
        }

        return packet
