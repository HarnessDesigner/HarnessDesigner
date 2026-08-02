# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from ... import check_types as _check_types


class AppUsersTable(TableBase):

    """Lookup table mapping a MySQL login account to a compact app-level user id.

    Used by the row-id generation mechanism to resolve CURRENT_USER() to the
    32-bit author value embedded in every migrated row's id -- kept separate
    from MySQL's own account system since the two serve different purposes
    (authorization vs. a compact, display-friendly identity).
    """
    __table_name__ = 'app_users'

    # Plain AUTO_INCREMENT id, not part of the UUID migration -- author
    # values embedded in every migrated row need to stay a compact 32-bit
    # int, not a full UUID.
    __uses_uuid_id__ = False

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the ``app_users`` table needs new fields added.

        :returns: ``True`` when the table requires updates; otherwise ``False``.
        :rtype: bool
        """
        from ..create_database import app_users

        return app_users.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Create the ``app_users`` table.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import app_users

        app_users.table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Add any missing fields to the existing ``app_users`` table.
        """
        from ..create_database import app_users

        app_users.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["AppUser"]:
        """Iterate over the available items.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['AppUser']
        """
        for db_id in TableBase.__iter__(self):
            yield AppUser(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "AppUser":
        """Return the requested item.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`AppUser`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return AppUser(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', mysql_account=item)
        if db_id:
            return AppUser(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, mysql_account: str, display_name: str = '') -> "AppUser":
        """Add a new app-level user identity.

        :param mysql_account: The MySQL login account this identity maps to.
        :type mysql_account: str
        :param display_name: Friendly name shown in the UI.
        :type display_name: str
        :returns: The newly created user entry.
        :rtype: :class:`AppUser`
        """
        db_id = TableBase.insert(self, mysql_account=mysql_account, display_name=display_name)

        return AppUser(self, db_id)


class AppUser(EntryBase):

    """Represent a single app-level user identity.
    """
    _table: AppUsersTable = None

    _stored_mysql_account: DefaultStoredValueType | str = DefaultStoredValue

    @property
    @_check_types.do
    def mysql_account(self) -> str:
        """Return the MySQL login account this identity maps to.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_mysql_account is DefaultStoredValue:
            self._stored_mysql_account = self._table.select('mysql_account', id=self._db_id)[0][0]

        return self._stored_mysql_account

    _stored_display_name: DefaultStoredValueType | str = DefaultStoredValue

    @property
    @_check_types.do
    def display_name(self) -> str:
        """Return the display name.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_display_name is DefaultStoredValue:
            self._stored_display_name = self._table.select('display_name', id=self._db_id)[0][0]

        return self._stored_display_name

    @display_name.setter
    @_check_types.do
    def display_name(self, value: str):
        """Set the display name.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_display_name = value
        self._table.update(self._db_id, display_name=value)
        self._populate('display_name')
