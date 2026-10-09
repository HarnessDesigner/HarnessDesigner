# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cached data for one project table: one load per project, reads from memory,
and writes recorded here until the project flushes them in one transaction.

Only project tables (``pjt_*``) use this. Global tables are not cached here.
See WRITE_DESIGN.md sections 4.1-4.8 for the flow this implements.
"""

from typing import Any

from ... import check_types as _check_types


# A cell as the database returns it. None is a NULL column.
_CellValue = int | float | str | bytes | None
_Row = dict[str, _CellValue]


# Guard for when a deleted row leaves the raw data (WRITE_DESIGN.md 4.5a).
#   True  -- removed as soon as delete() is called. Reads raise RowDeletedError.
#   False -- kept until the flush commits. Reads still succeed; changes are ignored.
RAW_DELETE_IMMEDIATE = True


class RowDeletedError(Exception):
    """A row was read or changed after it was deleted."""

    @_check_types.do
    def __init__(self, table_name: str, row_id: bytes) -> None:
        """Build the error.

        :param table_name: The table the row belonged to.
        :type table_name: str
        :param row_id: The id of the deleted row.
        :type row_id: bytes
        """
        super().__init__(f'row {row_id!r} in {table_name} has been deleted')
        self.table_name = table_name
        self.row_id = row_id


def _row_matches(row: _Row, where: dict[str, _CellValue], use_or: bool) -> bool:
    """Whether *row* satisfies *where*, with the same rules as ``PJTTableBase.select``.

    :param row: One cached row.
    :type row: _Row
    :param where: Column names and the values to match. ``None`` matches NULL.
    :type where: dict[str, _CellValue]
    :param use_or: ``True`` to match any condition, ``False`` for all of them.
    :type use_or: bool
    :returns: Whether the row matches.
    :rtype: bool
    """
    if not where:
        return True

    checks = []
    for field, value in where.items():
        if value is None:
            checks.append(row[field] is None)
        else:
            checks.append(row[field] == value)

    if use_or:
        return any(checks)

    return all(checks)


class TableData:
    """Raw row data and pending writes for one project table."""

    @_check_types.do
    def __init__(self, table_name: str, field_names: list[str]) -> None:
        """Create an empty cache. Call :meth:`load` to fill it.

        :param table_name: The SQL table name.
        :type table_name: str
        :param field_names: Every column of the table. ``id`` must be one of them.
        :type field_names: list[str]
        """
        if 'id' not in field_names:
            raise ValueError(f'{table_name} has no id column')

        self.table_name = table_name
        self.field_names = list(field_names)
        self._field_set = frozenset(field_names)

        self._rows: dict[bytes, _Row] = {}
        self._inserts: set[bytes] = set()
        self._updates: dict[bytes, dict[str, _CellValue]] = {}
        self._deletes: set[bytes] = set()

    @_check_types.do
    def load(self, connector: Any, low: bytes, high: bytes) -> None:
        """Fill the cache with this project's rows: one query, every column.

        :param connector: Connector with ``execute`` and ``fetchall``.
        :type connector: Any
        :param low: Lowest row id of the project's id range.
        :type low: bytes
        :param high: Highest row id of the project's id range.
        :type high: bytes
        """
        connector.execute(
            f'SELECT {", ".join(self.field_names)} FROM {self.table_name} '
            'WHERE id >= ? AND id <= ?;',
            (low, high))

        for row in connector.fetchall():
            self._rows[row[0]] = dict(zip(self.field_names, row))

    @_check_types.do
    def select(self, *fields: tuple[str], OR: bool = False,
               **where: dict[str, _CellValue]) -> list[tuple[_CellValue, ...]]:
        """Read *fields* from every cached row that matches *where*.

        Mirrors ``PJTTableBase.select``: the same arguments, the same ``OR``
        switch, and ``None`` in *where* matches a NULL column. The cache holds
        only this project's rows, so the project's id range is implicit.
        Rows pending delete on the deferred path are still returned until the
        flush commits, as WRITE_DESIGN.md 4.5a describes.

        :param fields: Columns to return, in the order given.
        :type fields: str
        :param OR: Match any condition in *where* instead of all of them.
        :type OR: bool
        :param where: Column names and the values to match.
        :type where: dict[str, _CellValue]
        :returns: One tuple of *fields* per matching row.
        :rtype: list[tuple[_CellValue, ...]]
        :raises ValueError: No fields were asked for.
        :raises KeyError: A named column does not exist. Only raised once the
            cache holds at least one row.
        """
        if not fields:
            raise ValueError('select needs at least one field')

        if 'id' in where:
            id = where.pop('id')

            rows = [self._rows[id]]

        else:
            rows = self._rows.values()

        results = []
        for row in rows:
            if _row_matches(row, where, OR):
                results.append(tuple(row[field] for field in fields))

        return results

    @_check_types.do
    def row(self, row_id: bytes) -> tuple[_CellValue, ...] | None:
        """Return one row as a tuple in column order, or ``None`` when not cached.

        :param row_id: The row id.
        :type row_id: bytes
        :returns: The row's values in column order, or ``None``.
        :rtype: tuple[_CellValue, ...] | None
        """
        cached = self._rows.get(row_id)
        if cached is None:
            return None

        return tuple(cached[field] for field in self.field_names)

    @_check_types.do
    def row_ids(self) -> list[bytes]:
        """Return the id of every cached row.

        :returns: The row ids.
        :rtype: list[bytes]
        """
        return list(self._rows)

    @_check_types.do
    def contains(self, row_id: bytes) -> bool:
        """Return whether a row is in the cache.

        :param row_id: The row id.
        :type row_id: bytes
        :returns: ``True`` when the row is cached.
        :rtype: bool
        """
        return row_id in self._rows

    @_check_types.do
    def change(self, row_id: bytes, **values: dict[str, _CellValue]) -> None:
        """Record new values for a row.

        A change to a row that is pending delete is ignored. A change to a row
        that is pending insert only updates the cache, because the insert reads
        the cache when it is written.

        :param row_id: The row id.
        :type row_id: bytes
        :param values: Column names and their new values.
        :type values: dict[str, _CellValue]
        :raises KeyError: A named column is not a column of this table.
        :raises RowDeletedError: The row is not in the cache.
        """
        row = self._rows.get(row_id)
        if row is None:
            raise RowDeletedError(self.table_name, row_id)

        # Keys that are not columns of this table, found by one set difference
        # against the precomputed field names, so a bad column name fails here
        # rather than at flush time.
        unknown = set(values.keys()) - self._field_set
        if unknown:
            raise KeyError(f'{sorted(unknown)} not columns of {self.table_name}')

        if row_id in self._deletes:
            return

        row.update(values)

        if row_id not in self._inserts:
            self._updates.setdefault(row_id, dict()).update(values)

    @_check_types.do
    def insert(self, **values: dict[str, _CellValue]) -> None:
        """Add a new row. Nothing is written until the flush.

        The record is complete: every column, including ``id`` (already
        generated by ``id_generator``) and each column's default value.

        :param values: Every column of the table, ``id`` included.
        :type values: dict[str, _CellValue]
        :raises ValueError: The columns given are not exactly the table's columns.
        :raises KeyError: A row with this id is already in the cache.
        """
        if set(values) != self._field_set:
            raise ValueError(f'{self.table_name} insert needs exactly {sorted(self._field_set)}')

        row_id = values['id']
        if row_id in self._rows:
            raise KeyError(f'{self.table_name} already has row {row_id!r}')

        self._rows[row_id] = dict(values)
        self._inserts.add(row_id)

    @_check_types.do
    def delete(self, row_id: bytes) -> None:
        """Mark a row for deletion.

        A row that was never written is cancelled: it leaves the cache and
        nothing reaches the database. Otherwise its pending changes are dropped
        and its id is queued for a batched ``DELETE``.

        :param row_id: The row id.
        :type row_id: bytes
        :raises RowDeletedError: The row is not in the cache and not already queued.
        """

        if row_id not in self._rows:
            raise RowDeletedError(self.table_name, row_id)

        if row_id in self._deletes:
            return

        if row_id in self._inserts:
            self._inserts.discard(row_id)
            self._rows.pop(row_id, None)
            return

        self._updates.pop(row_id, None)
        self._deletes.add(row_id)

        if RAW_DELETE_IMMEDIATE:
            self._rows.pop(row_id)

    @_check_types.do
    def delete_statement(self) -> tuple[str, list[tuple[_CellValue, ...]]] | None:
        """The pending ``DELETE`` for this table, or ``None`` when nothing is queued.

        :returns: The SQL and its parameter rows.
        :rtype: tuple[str, list[tuple[_CellValue, ...]]] | None
        """
        if not self._deletes:
            return None

        return (f'DELETE FROM {self.table_name} WHERE id = ?;',
                [(row_id,) for row_id in self._deletes])

    @_check_types.do
    def insert_statement(self) -> tuple[str, list[tuple[_CellValue, ...]]] | None:
        """The pending ``INSERT`` for this table, built from the cached rows.

        :returns: The SQL and its parameter rows, or ``None`` when nothing is queued.
        :rtype: tuple[str, list[tuple[_CellValue, ...]]] | None
        """
        if not self._inserts:
            return None

        columns = ', '.join(self.field_names)
        placeholders = ', '.join(['?'] * len(self.field_names))
        rows = [tuple(self._rows[row_id][field] for field in self.field_names)
                for row_id in self._inserts]

        return (f'INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders});', rows)

    @_check_types.do
    def update_statements(self) -> list[tuple[str, list[tuple[_CellValue, ...]]]]:
        """Pending ``UPDATE`` statements, one per distinct set of changed columns.

        :returns: One ``(sql, parameter rows)`` pair per column set.
        :rtype: list[tuple[str, list[tuple[_CellValue, ...]]]]
        """
        groups: dict[tuple[str, ...], list[tuple[_CellValue, ...]]] = {}

        for row_id, changed in self._updates.items():
            columns = tuple(sorted(changed))
            values = tuple(changed[column] for column in columns) + (row_id,)
            groups.setdefault(columns, []).append(values)

        statements = []
        for columns, rows in groups.items():
            assignments = ', '.join(f'{column} = ?' for column in columns)
            statements.append(
                (f'UPDATE {self.table_name} SET {assignments} WHERE id = ?;', rows))

        return statements

    @_check_types.do
    def commit_flushed(self) -> None:
        """Clear the pending state after the flush has committed.

        Call this only after the transaction succeeded. On the deferred delete
        path, the deleted rows leave the cache here.
        """
        if not RAW_DELETE_IMMEDIATE:
            for row_id in self._deletes:
                self._rows.pop(row_id, None)

        self._inserts.clear()
        self._updates.clear()
        self._deletes.clear()

    @_check_types.do
    def mirror_insert(self, **values: dict[str, _CellValue]) -> None:
        """Store a row that was just written to the database. No pending write is recorded.

        :param values: Every column of the table, ``id`` included, as read back
            from the database.
        :type values: dict[str, _CellValue]
        :raises ValueError: The columns given are not exactly the table's columns.
        :raises KeyError: A row with this id is already in the cache.
        """
        if set(values) != self._field_set:
            raise ValueError(f'{self.table_name} insert needs exactly {sorted(self._field_set)}')

        row_id = values['id']
        if row_id in self._rows:
            raise KeyError(f'{self.table_name} already has row {row_id!r}')

        self._rows[row_id] = dict(values)

    @_check_types.do
    def mirror_update(self, row_id: bytes, **values: dict[str, _CellValue]) -> None:
        """Apply a change that was just written to the database. No pending write is recorded.

        :param row_id: The row id.
        :type row_id: bytes
        :param values: Column names and their new values.
        :type values: dict[str, _CellValue]
        :raises KeyError: A named column is not a column of this table.
        :raises RowDeletedError: The row is not in the cache.
        """
        row = self._rows.get(row_id)
        if row is None:
            raise RowDeletedError(self.table_name, row_id)

        unknown = set(values.keys()) - self._field_set
        if unknown:
            raise KeyError(f'{sorted(unknown)} not columns of {self.table_name}')

        row.update(values)

    @_check_types.do
    def mirror_delete(self, row_id: bytes) -> None:
        """Remove a row that was just deleted from the database. No pending write is recorded.

        :param row_id: The row id.
        :type row_id: bytes
        :raises RowDeletedError: The row is not in the cache.
        """
        if row_id not in self._rows:
            raise RowDeletedError(self.table_name, row_id)

        del self._rows[row_id]
