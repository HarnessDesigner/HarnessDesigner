# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import uuid

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin
from ... import check_types as _check_types


class CPALockTypesTable(TableBase):
    """Represent a CPA lock types table in :mod:`harness_designer.database.global_db.cpa_lock_type`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'cpa_lock_types'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import cpa_lock_types

        return cpa_lock_types.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import cpa_lock_types

        cpa_lock_types.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        cpa_lock_types.add_records(self._con, splash, data_path)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import cpa_lock_types

        cpa_lock_types.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["CPALockType"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['CPALockType']
        """
        for db_id in TableBase.__iter__(self):
            yield CPALockType(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "CPALockType":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CPALockType`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes, uuid.UUID)):
            if item in self:
                return CPALockType(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return CPALockType(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, name: str) -> "CPALockType":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CPALockType`
        """
        db_id = TableBase.insert(self, name=name)
        return CPALockType(self, db_id)

    @property
    @_check_types.do
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class CPALockType(EntryBase, NameMixin):
    """Represent a CPA lock type in :mod:`harness_designer.database.global_db.cpa_lock_type`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: CPALockTypesTable = None

