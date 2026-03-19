from typing import Optional as _Optional, Generator as _Generator
from . import db_data as _db_data


class ConnectorBase:

    def __init__(self, mainframe, db_name):
        self.mainframe = mainframe
        self.db_name = db_name
        self._db_data = None

    @property
    def db_data(self):
        if self._db_data is None:
            self._db_data = _db_data.DBData()

        return self._db_data

    @db_data.setter
    def db_data(self, value):
        if value is None:
            if self._db_data is not None:
                self._db_data.close()
                self._db_data = None

    def get_tables(self) -> list[str]:
        raise NotImplementedError

    def connect(self) -> bool:
        raise NotImplementedError

    def execute(self, operation: str,
                params: _Optional[tuple] = None,
                multi: bool = False) -> _Optional[_Generator]:
        raise NotImplementedError

    def executemany(self, operation: str,
                    seq_params: list | tuple) -> _Optional[_Generator]:
        raise NotImplementedError

    @property
    def lastrowid(self) -> _Optional[int]:
        raise NotImplementedError

    def fetchone(self) -> _Optional[list[tuple]]:
        raise NotImplementedError

    def fetchmany(self, size: _Optional[int] = None) -> list[tuple]:
        raise NotImplementedError

    def fetchall(self) -> list[tuple]:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
