# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import time
import uuid

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .. import id_generator as _id_generator
from ... import check_types as _check_types


class AppUsersTable(TableBase):

    """Lookup table mapping a MySQL login account to a compact app-level user id.

    Used by the row-id generation mechanism to resolve CURRENT_USER() to the
    16-bit author value embedded in every migrated row's id (the trailing
    2 bytes -- see database/id_generator.py) -- kept separate from MySQL's
    own account system since the two serve different purposes (authorization
    vs. a compact, display-friendly identity).

    This table's own row ids follow the exact same 128-bit layout as every
    other migrated table, with project_id fixed at 0 (an app user doesn't
    belong to a project) -- so the row is, in effect, mostly zero bytes with
    a real timestamp in the middle and the row's own trailing 2-byte user_id
    being the actual user identity being defined. See insert() below for how
    that user_id is chosen. User id 0 is reserved for rows inserted before
    any real user identity exists (single-seat / initial setup) -- see
    id_generator._LOCAL_USER_ID.
    """
    __table_name__ = 'app_users'

    # False because this table's id generation is bespoke (see insert()
    # below), not because the id itself is still a plain AUTO_INCREMENT
    # int -- TableBase.insert()'s generic __uses_uuid_id__ path would embed
    # id_generator._LOCAL_USER_ID (0) as this row's own trailing user_id,
    # which is wrong here: this row's whole purpose is to define a *new*,
    # never-before-used user_id, not record who authored the row.
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
        if isinstance(item, (int, bytes)):
            if item in AppUser or item in self:
                return AppUser(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', mysql_account=item)
        if db_id:
            return AppUser(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, mysql_account: str, display_name: str = '') -> "AppUser":
        """Add a new app-level user identity.

        Deliberately does not go through TableBase.insert()'s generic
        __uses_uuid_id__ path -- that path embeds
        id_generator._LOCAL_USER_ID (0) as the row's own trailing
        user_id, meaning "authored by the local/no-identity user". This
        row's whole point is the opposite: to mint a *new* user_id that
        has never been used before, so it picks the next one itself by
        scanning every existing row's trailing user_id and taking the
        highest + 1 (starting from 0, so the first real user becomes 1
        -- 0 stays reserved, see the class docstring). New users are only
        ever added in multi-seat setups and very rarely, so scanning the
        whole (small) table client-side instead of a server-side locked
        counter is an acceptable trade for not needing MySQL-specific
        coordination here.

        :param mysql_account: The MySQL login account this identity maps to.
        :type mysql_account: str
        :param display_name: Friendly name shown in the UI.
        :type display_name: str
        :returns: The newly created user entry.
        :rtype: :class:`AppUser`
        """
        max_user_id = 0
        for row_id in TableBase.__iter__(self):
            max_user_id = max(max_user_id, _id_generator.unpack_user_id(row_id))

        new_id = _id_generator.pack_global_row_id(time.time_ns(), max_user_id + 1)

        self._con.execute(
            f'INSERT INTO {self.__table_name__} (id, mysql_account, display_name) VALUES (?, ?, ?);',
            (new_id, mysql_account, display_name))
        self._con.commit()

        return AppUser(self, new_id)


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
