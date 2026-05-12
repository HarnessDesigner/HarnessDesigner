# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import (
    Optional as _Optional,
    Union as _Union,
    Generator as _Generator,
)

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt

from datetime import (
    date as _date,
    datetime as _datetime,
    time as _time,
    timedelta as _timedelta
)

from decimal import Decimal as _Decimal
from time import struct_time as _struct_time
from mysql.connector.cursor import MySQLCursor as _MySQLCursor

import mysql.connector
from mysql.connector import errorcode
import mysql.connector.constants

from .. import base as _base
from ... import update_monitor as _update_monitor

from .... import config as _config

from ....ui.widgets import auto_complete
from .... import logger as _logger

Config = _config.Config.database.mysql

if Config.client_flags is None:
    Config.client_flags = mysql.connector.constants.ClientFlag.get_default()


_StrOrBytes = _Union[str, bytes]

_ToMysqlInputTypes = _Optional[_Union[int, float, _Decimal, _StrOrBytes, bool,
                                      _datetime, _date, _time, _struct_time, _timedelta]]

_ToPythonOutputTypes = _Optional[_Union[float, int, _Decimal, _StrOrBytes, _date,
                                        _timedelta, _datetime, set[str]]]
_ParamsSequenceType = list[_ToMysqlInputTypes] | tuple[_ToMysqlInputTypes]
_ParamsDictType = dict[str, _ToMysqlInputTypes]
_ParamsSequenceOrDictType = _Union[_ParamsDictType, _ParamsSequenceType]

_RowType = tuple[_ToPythonOutputTypes, ...]


class LoginDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('LOGIN')
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        user_row = QHBoxLayout()
        user_label = QLabel('Username:')
        self.username_ctrl = auto_complete.AutoComplete(
            self, autocomplete_choices=Config.recent_users)
        user_row.addWidget(user_label)
        user_row.addWidget(self.username_ctrl)
        layout.addLayout(user_row)

        pass_row = QHBoxLayout()
        pass_label = QLabel('Password:')
        self.password_ctrl = QLineEdit()
        self.password_ctrl.setEchoMode(QLineEdit.EchoMode.Password)
        pass_row.addWidget(pass_label)
        pass_row.addWidget(self.password_ctrl)
        layout.addLayout(pass_row)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        self._settings_button = QPushButton('Settings')
        btn_row.addWidget(self._settings_button)
        btn_row.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        # Rename OK to Login
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText('Login')
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        btn_row.addWidget(button_box)
        layout.addLayout(btn_row)

        self._settings_button.clicked.connect(self._on_settings_button)

    def _on_settings_button(self):
        try:
            from . import settings_dialog
        except ImportError:
            import settings_dialog

        dlg = settings_dialog.SQLOptionsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            values = dlg.GetValue()
            for key, value in values.items():
                setattr(Config, key, value)

    def GetValue(self):
        return (
            self.username_ctrl.GetValue(),
            self.password_ctrl.text()
        )


class SQLConnector(_base.ConnectorBase):

    def __init__(self, mainframe, splash, args):
        super().__init__(mainframe, Config.database_name)
        self._connection: mysql.connector.MySQLConnection = None
        self._cursor: _MySQLCursor = None
        self.cred_manager: _update_monitor.Manager = None
        self.update_monitor: _update_monitor.Monitor = None

    def connect(self):
        dlg = LoginDialog(self.mainframe)
        try:
            if dlg.exec() == QDialog.DialogCode.Accepted:
                username, password = dlg.GetValue()
            else:
                return False
        except:  # NOQA
            raise RuntimeError('This should not happen')

        try:
            self._connection = mysql.connector.connect(
                user=username,
                password=password,
                host=Config.host,
                port=Config.port,
                compress=Config.compress,
                oci_config_file=Config.oci_config_file,
                oci_config_profile=Config.oci_config_profile,
                kerberos_auth_mode=Config.kerberos_auth_mode,
                force_ipv6=Config.force_ipv6,
                ssl_verify_identity=Config.ssl_verify_identity,
                ssl_verify_cert=Config.ssl_verify_cert,
                ssl_key=Config.ssl_key,
                ssl_disabled=Config.ssl_disabled,
                ssl_cert=Config.ssl_cert,
                ssl_ca=Config.ssl_ca,
                tls_versions=Config.tls_versions,
                buffered=Config.buffered,
                write_timeout=Config.write_timeout,
                read_timeout=Config.read_timeout,
                connection_timeout=Config.connection_timeout,
                client_flags=Config.client_flags,
                sql_mode=Config.sql_mode,
                auth_plugin=Config.auth_plugin,
                openid_token_file=Config.openid_token_file,
                database=self.db_name,
            )
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                _logger.logger.database("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                _logger.logger.database("Database does not exist")
            else:
                _logger.logger.traceback(err, 'MYSQL DATABASE')
            return False

        if username in Config.recent_users:
            Config.recent_users.remove(username)
        Config.recent_users.insert(0, username)

        while len(Config.recent_users) > 5:
            Config.recent_users = Config.recent_users[:-1]

        self._cursor = self._connection.cursor()

        self.cred_manager = _update_monitor.Manager()

        from .. import CONNECTOR_MYSQL

        self.cred_manager.store_credentials(
            CONNECTOR_MYSQL, host=Config.host, port=Config.port, user=username,
            password=password, database=self.db_name)

        self.update_monitor = _update_monitor.Monitor(self.mainframe)

        self.update_monitor.start()
        return True

    def get_tables(self) -> list[str]:
        self.execute(f'SELECT table_name FROM information_schema.tables WHERE table_schema = "{self.db_name}";')
        res = self.fetchall()

        return [item[0] for item in res]

    def execute(self, operation: _StrOrBytes,
                params: _Optional[_ParamsSequenceOrDictType] = None,
                multi: bool = False) -> _Optional[_Generator[_MySQLCursor, None, None]]:
        self._cursor.execute(operation, params, multi)

    def executemany(
        self, operation: str, seq_params: list[_ParamsSequenceOrDictType] | tuple[_ParamsSequenceOrDictType]
    ) -> _Optional[_Generator[_MySQLCursor, None, None]]:

        self._cursor.executemany(operation, seq_params)

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

        self.update_monitor.stop()
        self.cred_manager.cleanup()
