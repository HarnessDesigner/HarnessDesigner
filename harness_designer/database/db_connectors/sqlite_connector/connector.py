# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""SQLite connector implementation and cursor helpers."""
import io
from typing import TYPE_CHECKING

import re
import threading
import traceback
import sqlite3
from typing import (Optional as _Optional,
                    Union as _Union,
                    Generator as _Generator)
from datetime import (date as _date,
                      datetime as _datetime,
                      time as _time,
                      timedelta as _timedelta)

from decimal import Decimal as _Decimal
from time import struct_time as _struct_time
import os
import requests
import zipfile

from .. import base as _base
from .... import config as _config
from .... import logger as _logger
from .... process import manager as _manager


if TYPE_CHECKING:
    from .... import ui as _ui


_NORMALIZE_LITERAL_RE = re.compile(r"'[^']*'|\b\d+\b")


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
    """
    Implement database access through :mod:`sqlite3`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialize the SQLite connector state.

        :param mainframe: Main application frame that owns the connector.
        :type mainframe: :class:`_ui.Mainframe`
        """

        db_path = _config.Config.database.sqlite.database_path

        super().__init__(mainframe, db_path)

        self._connection: sqlite3.Connection = None
        self._cursor: sqlite3.Cursor = None
        self.database_name = 'harness_designer'
        self.cred_manager: _manager.CredManager = None

        # normalized SQL text -> [call_count, total_seconds]
        self._query_profile: dict[str, list] = {}

        # normalized SQL text of statements that have already popped an
        # error dialog this session -- see _report_sql_error. A broken
        # statement hit from a hot loop (mouse-move handlers, etc.) must
        # not queue up one modal dialog per call; every occurrence is
        # still logged, just not re-shown.
        self._shown_sql_errors: set[str] = set()

    def reset_query_profile(self) -> None:
        """Clear accumulated query-profile stats (see ``Config.debug.database.profile_queries``)."""
        self._query_profile = {}

    def dump_query_profile(self, top_n: int = 30, label: str = '') -> None:
        """Log a summary of queries recorded since the last reset.

        Reports the ``top_n`` normalized statements by total time and by
        call count, plus grand totals. No-op if nothing was recorded (e.g.
        profiling was off).
        """
        if not self._query_profile:
            return

        total_calls = sum(v[0] for v in self._query_profile.values())
        total_time = sum(v[1] for v in self._query_profile.values())

        header = f'QUERY PROFILE{f" ({label})" if label else ""}: ' \
                 f'{total_calls} calls, {total_time * 1000:.1f}ms total, ' \
                 f'{len(self._query_profile)} distinct statements'
        _logger.database(header)

        by_time = sorted(self._query_profile.items(), key=lambda kv: kv[1][1], reverse=True)
        _logger.database('-- top statements by total time --')
        for sql, (count, secs) in by_time[:top_n]:
            _logger.database(f'{secs * 1000:8.1f}ms  {count:6d}x  {secs / count * 1000:6.3f}ms/call  {sql}')

        by_count = sorted(self._query_profile.items(), key=lambda kv: kv[1][0], reverse=True)
        _logger.database('-- top statements by call count --')
        for sql, (count, secs) in by_count[:top_n]:
            _logger.database(f'{count:6d}x  {secs * 1000:8.1f}ms  {secs / count * 1000:6.3f}ms/call  {sql}')

    def get_tables(self) -> list[str]:
        """
        Return the table names stored in the SQLite database.

        :returns: A list of table names.
        :rtype: list[str]
        """

        self.execute(f'SELECT name FROM sqlite_master WHERE type="table";')
        rows = self.fetchall()

        return [row[0] for row in rows]

    def get_table_column_names(self, table_name: str) -> list[str]:
        """
        Return the column names defined for a table.

        :param table_name: Name of the database table to inspect or update.
        :type table_name: str

        :returns: The column names defined for the table.
        :rtype: list[str]
        """

        self.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                     f'pragma_table_info("{table_name}");')

        column_names = list(eval(self.fetchall()[0][0]))
        return column_names

    def connect(self, splash) -> bool:
        """
        Open the configured SQLite database and start update monitoring.

        :returns: ``True`` when the connection succeeds; otherwise ``False``.
        :rtype: bool
        """

        def _download_data(url, label, dst):
            response = requests.get(url, stream=True)

            block_size = 1048576
            cur_size = 0

            splash.SetText(f'Downloading {label} {cur_size}')
            splash.flush()

            buf = io.BytesIO()

            for data in response.iter_content(block_size):
                if not data:
                    break

                cur_size += len(data)
                buf.write(data)
                splash.SetText(f'Downloading {label} {cur_size}')

            buf.seek(0)

            splash.SetText(f'Decompressing {label}...')
            splash.flush()

            with zipfile.ZipFile(buf) as zdata:
                zdata.extractall(dst)

            splash.SetText('Finished Decompressing!')
            splash.flush()

            buf.close()

        if not os.path.exists(self.db_name):
            db_path, db_name = os.path.split(self.db_name)

            _download_data(
                'https://github.com/HarnessDesigner/database/raw/refs/heads/main/prebuilt/harness_designer_database.zip',
                'Database', db_path)
            if db_name != 'harness_designer.db':
                src = os.path.join(db_path, 'harness_designer.db')
                os.rename(src, self.db_name)

            model_path = os.path.join(db_path, 'models')
            cad_path = os.path.join(db_path, 'cads')

            items = [
                ('https://github.com/HarnessDesigner/database/raw/refs/heads/main/prebuilt/cads1.zip', 'CAD 1', cad_path),
                ('https://github.com/HarnessDesigner/database/raw/refs/heads/main/prebuilt/cads2.zip', 'CAD 2', cad_path),
                ('https://github.com/HarnessDesigner/database/raw/refs/heads/main/prebuilt/models.zip', 'models', model_path)
            ]

            for item in items:
                _download_data(*item)

            downloaded = True
        else:
            downloaded = False

        self._connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self._cursor = self._connection.cursor()

        if downloaded:
            db_path = os.path.split(self.db_name)[0]

            model_path = os.path.join(db_path, 'models')
            cad_path = os.path.join(db_path, 'cads')
            datasheet_path = os.path.join(db_path, 'datasheets')
            image_path = os.path.join(db_path, 'images')

            self.execute(f'UPDATE settings SET value="{model_path}" WHERE name="model_path";')
            self.execute(f'UPDATE settings SET value="{cad_path}" WHERE name="cad_path";')
            self.execute(f'UPDATE settings SET value="{datasheet_path}" WHERE name="datasheet_path";')
            self.execute(f'UPDATE settings SET value="{image_path}" WHERE name="image_path";')
            self.commit()

            if not os.path.exists(model_path):
                os.makedirs(model_path)

            if not os.path.exists(image_path):
                os.makedirs(image_path)

            if not os.path.exists(cad_path):
                os.makedirs(cad_path)

            if not os.path.exists(datasheet_path):
                os.makedirs(datasheet_path)

            for i in range(0x00, 0x100):
                i = f'{i:02x}'
                for pth in (model_path, image_path, cad_path, datasheet_path):
                    pth = os.path.join(pth, i)
                    if not os.path.exists(pth):
                        os.mkdir(pth)

        # the cred manager needs to be started before the child processes
        # are started. This is because the child processes use the data from
        # the cred manager to collect information  needed to access a database.

        # TODO: Rework the cred manager to secure the data better. I have to
        #  do more research on how to do this.

        from .. import CONNECTOR_SQLITE

        printlock = threading.Lock()
        self.cred_manager = _manager.CredManager(printlock)

        self.cred_manager.store_credentials(printlock, CONNECTOR_SQLITE,
                                            database_path=self.db_name)

        self.mainframe.process_manager.start()

        return True

    def execute(self, operation: str,
                params: _Optional[_ParamsSequenceOrDictType] = None,
                _=None) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        """
        Execute a SQLite operation using the active cursor.

        :param operation: SQL statement to execute.
        :type operation: str
        :param params: Parameters supplied for the SQL operation.
        :type params: _Optional[_ParamsSequenceOrDictType]
        :param _: Unused compatibility argument.
        :type _: None

        :returns: The connector-specific cursor result, if one is returned.
        :rtype: _Generator[sqlite3.Cursor, None, None] | None
        """

        try:
            if params is None:
                return self._cursor.execute(operation)
            else:
                return self._cursor.execute(operation, params)
        except AttributeError:
            pass
        except Exception as err:  # NOQA
            _logger.error('SQLITE execute ERROR:', 'CMD:', operation, '\n', 'PARAMS:', params)
            # err.__traceback__ is exactly one frame deep here (this line) --
            # a traceback only accumulates frames an exception actually
            # unwinds *through*, and this except clause catches it in the
            # very frame it was raised in, so it never had the chance to
            # pick up whichever PJT*/global_db call built this statement.
            # traceback.extract_stack() instead walks the live call stack of
            # this thread right now, which still has that full chain intact.
            call_stack = traceback.extract_stack()[:-1]
            self._report_sql_error(err, operation, params, call_stack)

    def _report_sql_error(self, err: Exception, operation: str, params,
                          call_stack: list = None) -> None:
        """Log a failed SQL statement's traceback and pop an error dialog.

        Never lets the exception itself propagate -- callers must keep
        running so the app can be closed gracefully instead of hanging or
        crashing. Logging always happens; the dialog is shown at most once
        per distinct (normalized) statement per session so a broken
        statement hit repeatedly from a hot loop (mouse-move handlers,
        etc.) can't queue up a stack of modal dialogs -- that would be
        just as effective a lockup as an uncaught exception.

        Marshaled through :func:`harness_designer.app.CallAfter` since
        ``execute``/``executemany`` can be reached from background threads
        (see ``process/manager.py`` for the same dialog-from-worker-thread
        pattern) -- constructing a ``QDialog`` off the main Qt thread is
        not safe.

        *call_stack* is the live call stack captured at the ``execute``/
        ``executemany`` call site (see there) -- ``err`` itself is caught in
        the same frame it's raised in, so ``err.__traceback__`` alone never
        shows which PJT*/global_db call actually built the failing
        statement; *call_stack* is what supplies that.
        """
        stack_text = ''.join(traceback.format_list(call_stack)) if call_stack else None
        _logger.traceback(err, msg=('Called from:\n' + stack_text) if stack_text else None)

        key = _NORMALIZE_LITERAL_RE.sub('?', operation)
        if key in self._shown_sql_errors:
            return

        self._shown_sql_errors.add(key)

        from .... import app as _app

        def _do(e=err, op=operation, p=params, stack=stack_text):
            from .... import critical_error_dialog as _ced

            context = f'SQL: {op}\nPARAMS: {p}'
            if stack:
                context += '\n\nCalled from:\n' + stack

            dlg = _ced.CriticalErrorDialog(
                self.mainframe, e, title='Database Error', context=context)
            dlg.exec()

        _app.CallAfter(_do)

    def executemany(
        self, operation: str, seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]
    ) -> _Optional[_Generator[sqlite3.Cursor, None, None]]:

        """
        Execute a SQLite operation for multiple parameter sets.

        :param operation: SQL statement to execute.
        :type operation: str
        :param seq_params: Sequence of parameter sets to execute.
        :type seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]

        :returns: The connector-specific cursor result, if one is returned.
        :rtype: _Generator[sqlite3.Cursor, None, None] | None
        """

        try:
            return self._cursor.executemany(operation, seq_params)
        except AttributeError:
            return None
        except Exception as err:  # NOQA
            _logger.error('SQLITE executemany ERROR:', 'CMD:', operation, '\n', 'PARAMS:', seq_params)
            call_stack = traceback.extract_stack()[:-1]
            self._report_sql_error(err, operation, seq_params, call_stack)
            return None

    @property
    def lastrowid(self) -> _Optional[int]:
        """
        Return the last inserted SQLite row identifier.

        :returns: The row identifier reported by the active cursor.
        :rtype: int | None
        """

        return self._cursor.lastrowid

    def fetchone(self) -> _Optional[_RowType]:
        """
        Fetch a single row from the SQLite cursor.

        :returns: The next row from the cursor, if available.
        :rtype: _RowType | None
        """

        return self._cursor.fetchone()

    def fetchmany(self, size: _Optional[int] = None) -> list[_RowType]:
        """
        Fetch multiple rows from the SQLite cursor.

        :param size: Maximum number of rows to fetch.
        :type size: int | None

        :returns: A list of fetched rows.
        :rtype: list[_RowType] | None
        """

        return self._cursor.fetchmany(size)

    def fetchall(self) -> list[_RowType]:
        """
        Fetch all remaining rows from the SQLite cursor.

        :returns: All remaining rows from the cursor.
        :rtype: list[_RowType] | None
        """

        return self._cursor.fetchall()

    def commit(self):
        """
        Commit the active SQLite transaction.

        :returns: ``None``.
        :rtype: None
        """

        self._connection.commit()

    def close(self):
        """
        Close the SQLite connector and stop related monitors.

        :returns: ``None``.
        :rtype: None
        """

        self.commit()

        self._cursor.close()
        self._connection.close()

        self._cursor = None
        self._connection = None

        self.cred_manager.cleanup()
