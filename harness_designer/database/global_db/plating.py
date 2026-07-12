# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import DescriptionMixin


class PlatingsTable(TableBase):
    """Represent a platings table in :mod:`harness_designer.database.global_db.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'platings'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import platings

        return platings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import platings

        platings.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        platings.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import platings

        platings.table.update_fields(self)

    def __iter__(self) -> _Iterable["Plating"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Plating']
        """

        for db_id in TableBase.__iter__(self):
            yield Plating(self, db_id)

    def __getitem__(self, item) -> "Plating":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Plating`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Plating(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', symbol=item)
        if db_id:
            return Plating(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, symbol: str, description: str) -> "Plating":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param symbol: Value for ``symbol``.
        :type symbol: str
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Plating`
        """
        db_id = TableBase.insert(self, symbol=symbol, description=description)
        return Plating(self, db_id)

    @property
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT symbol FROM {self.__table_name__};')]


class Plating(EntryBase, DescriptionMixin):
    """Represent a plating in :mod:`harness_designer.database.global_db.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PlatingsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'platings': [self.db_id],
        }

        return packet

    _stored_symbol: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def symbol(self) -> str:
        """Return the symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_symbol is DefaultStoredValue:
            self._stored_symbol = self._table.select('symbol', id=self._db_id)[0][0]

        return self._stored_symbol

    @symbol.setter
    def symbol(self, value: str):
        """Set the symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_symbol = value
        self._table.update(self._db_id, symbol=value)
        self._populate('symbol')
