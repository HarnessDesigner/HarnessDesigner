# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""SQLite connector implementation and cursor helpers."""

from typing import (
    Optional as _Optional,
    Union as _Union,
    Generator as _Generator,
)

from datetime import (
    date as _date,
    datetime as _datetime,
    time as _time,
    timedelta as _timedelta
)

from decimal import Decimal as _Decimal
from time import struct_time as _struct_time

import sqlite3

from .. import base as _base
from ... import update_monitor as _update_monitor

from .... import config as _config
from .... import logger as _logger


Config = _config.Config.database.sqlite


_StrOrBytes = _Union[str, bytes]

_ToMysqlInputTypes = _Optional[_Union[int, float, _Decimal, _StrOrBytes, bool,
                                      _datetime, _date, _time, _struct_time, _timedelta]]

_ToPythonOutputTypes = _Optional[_Union[float, int, _Decimal, _StrOrBytes, _date,
                                        _timedelta, _datetime, set[str]]]
_ParamsSequenceType = list[_ToMysqlInputTypes] | tuple[_ToMysqlInputTypes]
_ParamsDictType = dict[str, _ToMysqlInputTypes]
_ParamsSequenceOrDictType = _Union[_ParamsDictType, _ParamsSequenceType]

_RowType = tuple[_ToPythonOutputTypes, ...]

class SQLConnector(_base.ConnectorBase):

    """Implement database access through :mod:`sqlite3`.
    """
    def __init__(self, mainframe):
        """Initialize the SQLite connector state.

        :param mainframe: Main application frame that owns the connector.
        :type mainframe: UNKNOWN
        """
        db_path = Config.database_path

        super().__init__(mainframe, db_path)

        self._connection: sqlite3.Connection = None
        self._cursor: sqlite3.Cursor = None
        self.database_name = 'harness_designer'
        self.cred_manager: _update_monitor.Manager = None
        self.update_monitor: _update_monitor.Monitor = None

    def get_tables(self) -> list[str]:
        """Return the table names stored in the SQLite database.

        :returns: A list of table names.
        :rtype: list[str]
        """
        self.execute(f'SELECT name FROM sqlite_master WHERE type="table";')
        rows = self.fetchall()

        return [row[0] for row in rows]

    def get_table_column_names(self, table_name: str) -> list[str]:
        """Return the column names defined for a table.

        :param table_name: Name of the database table to inspect or update.
        :type table_name: str

        :returns: The column names defined for the table.
        :rtype: list[str]
        """
        self.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                     f'pragma_table_info("{table_name}");')

        column_names = eval(self.fetchall()[0][0])
        return column_names

    def connect(self):
        """Open the configured SQLite database and start update monitoring.

        :returns: ``True`` when the connection succeeds; otherwise ``False``.
        :rtype: bool
        """
        self._connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self._cursor = self._connection.cursor()

        import threading

        printlock = threading.Lock()
        self.cred_manager = _update_monitor.Manager(printlock)

        from .. import CONNECTOR_SQLITE

        self.cred_manager.store_credentials(printlock, CONNECTOR_SQLITE, database_path=self.db_name)
        self.update_monitor = _update_monitor.Monitor(self.mainframe)

        self.update_monitor.start()
        return True

    def execute(self, operation: str,
                params: _Optional[_ParamsSequenceOrDictType] = None,
                _=None) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        """Execute a SQLite operation using the active cursor.

        :param operation: SQL statement to execute.
        :type operation: str
        :param params: Parameters supplied for the SQL operation.
        :type params: _Optional[_ParamsSequenceOrDictType]
        :param _: Unused compatibility argument.
        :type _: None

        :returns: The connector-specific cursor result, if one is returned.
        :rtype: UNKNOWN
        """
        try:
            if params is None:
                return self._cursor.execute(operation)
            else:
                return self._cursor.execute(operation, params)
        except:  # NOQA
            _logger.logger.error('SQLITE ERROR:', 'CMD:', operation, '\n', 'PARAMS:', params)
            raise

    def executemany(
        self, operation: str, seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]
    ) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        """Execute a SQLite operation for multiple parameter sets.

        :param operation: SQL statement to execute.
        :type operation: str
        :param seq_params: Sequence of parameter sets to execute.
        :type seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]

        :returns: The connector-specific cursor result, if one is returned.
        :rtype: UNKNOWN
        """
        return self._cursor.executemany(operation, seq_params)

    @property
    def lastrowid(self) -> _Optional[int]:
        """Return the last inserted SQLite row identifier.

        :returns: The row identifier reported by the active cursor.
        :rtype: int | None
        """
        return self._cursor.lastrowid

    def fetchone(self) -> _Optional[_RowType]:
        """Fetch a single row from the SQLite cursor.

        :returns: The next row from the cursor, if available.
        :rtype: UNKNOWN
        """
        return self._cursor.fetchone()

    def fetchmany(self, size: _Optional[int] = None) -> list[_RowType]:
        """Fetch multiple rows from the SQLite cursor.

        :param size: Maximum number of rows to fetch.
        :type size: _Optional[int]

        :returns: A list of fetched rows.
        :rtype: list[tuple]
        """
        return self._cursor.fetchmany(size)

    def fetchall(self) -> list[_RowType]:
        """Fetch all remaining rows from the SQLite cursor.

        :returns: All remaining rows from the cursor.
        :rtype: list[tuple]
        """
        return self._cursor.fetchall()

    def commit(self):
        """Commit the active SQLite transaction.

        :returns: ``None``.
        :rtype: None
        """
        self._connection.commit()

    def close(self):
        """Close the SQLite connector and stop related monitors.

        :returns: ``None``.
        :rtype: None
        """
        self.commit()

        self._cursor.close()
        self._connection.close()

        self._cursor = None
        self._connection = None

        self.update_monitor.stop()
        self.cred_manager.cleanup()
