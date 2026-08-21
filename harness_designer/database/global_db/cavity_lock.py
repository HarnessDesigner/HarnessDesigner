# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin
from ... import check_types as _check_types


class CavityLocksTable(TableBase):
    """Represent a cavity locks table in :mod:`harness_designer.database.global_db.cavity_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'cavity_locks'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import cavity_locks

        return cavity_locks.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import cavity_locks

        cavity_locks.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        cavity_locks.add_records(self._con, splash, data_path)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import cavity_locks

        cavity_locks.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["CavityLock"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['CavityLock']
        """
        for db_id in TableBase.__iter__(self):
            yield CavityLock(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "CavityLock":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CavityLock`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in CavityLock or item in self:
                return CavityLock(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return CavityLock(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, name: str, description: str) -> "CavityLock":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CavityLock`
        """
        db_id = TableBase.insert(self, name=name, description=description)
        return CavityLock(self, db_id)

    @property
    @_check_types.do
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class CavityLock(EntryBase, NameMixin, DescriptionMixin):
    """Represent a cavity lock in :mod:`harness_designer.database.global_db.cavity_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: CavityLocksTable = None

