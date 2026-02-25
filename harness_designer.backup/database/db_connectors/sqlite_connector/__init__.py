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

from .. import ConnectorBase

from harness_designer import Config


Config = Config.database.sqlite


_StrOrBytes = _Union[str, bytes]

_ToMysqlInputTypes = _Optional[_Union[int, float, _Decimal, _StrOrBytes, bool,
                                      _datetime, _date, _time, _struct_time, _timedelta]]

_ToPythonOutputTypes = _Optional[_Union[float, int, _Decimal, _StrOrBytes, _date,
                                        _timedelta, _datetime, set[str]]]
_ParamsSequenceType = list[_ToMysqlInputTypes] | tuple[_ToMysqlInputTypes]
_ParamsDictType = dict[str, _ToMysqlInputTypes]
_ParamsSequenceOrDictType = _Union[_ParamsDictType, _ParamsSequenceType]

_RowType = tuple[_ToPythonOutputTypes, ...]


class SQLConnector(ConnectorBase):

    def __init__(self, mainframe):
        super().__init__(mainframe, Config.database_path)

        self._connection: sqlite3.Connection = None
        self._cursor: sqlite3.Cursor = None

    def get_tables(self) -> list[str]:
        self.execute('SELECT name FROM sqlite_master WHERE type="table";')
        res = self.fetchall()

        return [item[0] for item in res]

    def connect(self):
        self._connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self._cursor = self._connection.cursor()

    def execute(self, operation: str,
                params: _Optional[_ParamsSequenceOrDictType] = None,
                _=None) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        try:
            if params is None:
                return self._cursor.execute(operation)
            else:
                return self._cursor.execute(operation, params)
        except:  # NOQA
            print(operation)
            raise

    def executemany(
        self, operation: str, seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]
    ) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        return self._cursor.executemany(operation, seq_params)

    @property
    def lastrowid(self) -> _Optional[int]:
        return self._cursor.lastrowid

    def fetchone(self) -> _Optional[_RowType]:
        return self._cursor.fetchone()

    def fetchmany(self, size: _Optional[int] = None) -> list[_RowType]:
        return self._cursor.fetchmany(size)

    def fetchall(self) -> list[_RowType]:
        return self._cursor.fetchall()

    def commit(self):
        self._connection.commit()

    def close(self):
        self.commit()

        self._cursor.close()
        self._connection.close()

        self._cursor = None
        self._connection = None
