# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import NameMixin
from ... import check_types as _check_types


class SealTypesTable(TableBase):
    """Represent a seal types table in :mod:`harness_designer.database.global_db.seal_type`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__: str = 'seal_types'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import seal_types

        return seal_types.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import seal_types

        seal_types.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        seal_types.add_records(self._con, splash, data_path)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seal_types

        seal_types.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["SealType"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['SealType']
        """
        for db_id in TableBase.__iter__(self):
            yield SealType(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "SealType":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`SealType`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in SealType or item in self:
                return SealType(self, item)

            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return SealType(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, name: str, category: str) -> "SealType":
        """Insert a new seal type row.

        :param name: Manufacturer-facing type name (unique).
        :param category: One of ``create_database.seal_types.CATEGORIES``
            -- required, since this is what a placement session actually
            branches on (see ``add_handlers.editor_3d.seal``), independent
            of whatever free-text *name* a manufacturer happens to use.
        :returns: The newly-inserted row.
        :rtype: :class:`SealType`
        """

        db_id = TableBase.insert(self, name=name, category=category)
        return SealType(self, db_id)

    @property
    @_check_types.do
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class SealType(EntryBase, NameMixin):
    """Represent a seal type in :mod:`harness_designer.database.global_db.seal_type`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: SealTypesTable = None

    _stored_category: DefaultStoredValueType | str = DefaultStoredValue

    @property
    @_check_types.do
    def category(self) -> str:
        """Return this type's category (one of
        ``create_database.seal_types.CATEGORIES``) -- what placement
        logic (see ``add_handlers.editor_3d.seal``) actually branches
        on, independent of this type's own manufacturer-facing
        :attr:`name`.

        :rtype: str
        """
        if self._stored_category is DefaultStoredValue:
            self._stored_category = self._table.select('category', id=self._db_id)[0][0]

        return self._stored_category

    @category.setter
    @_check_types.do
    def category(self, value: str):
        """Set this type's category.

        :param value: One of ``create_database.seal_types.CATEGORIES``.
        :type value: str
        """
        self._stored_category = value
        self._table.update(self._db_id, category=value)
        self._populate('category')
