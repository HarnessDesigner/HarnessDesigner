from typing import (
    Optional as _Optional,
    Union as _Union,
    Generator as _Generator,
)

import wx

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

from .. import ConnectorBase

from harness_designer import Config

from ....gui_controls import auto_complete


Config = Config.database.mysql

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


class LoginDialog(wx.Dialog):
    def __init__(self, parent):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='LOGIN', style=wx.CAPTION | wx.STAY_ON_TOP, size=(400, 250))
        sizer = wx.BoxSizer(wx.VERTICAL)

        user_label = wx.StaticText(self, wx.ID_ANY, label='Username:')
        username_ctrl = auto_complete.AutoComplete(self, wx.ID_ANY, wx.EmptyString, size=(200, 22),
                                                   autocomplete_choices=Config.recent_users)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(user_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        h_sizer.Add(username_ctrl, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 10)

        sizer.Add(h_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        password_label = wx.StaticText(self, wx.ID_ANY, label='Password:')
        password_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(200, 22), style=wx.TE_PASSWORD)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(password_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        h_sizer.Add(password_ctrl, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 10)

        sizer.Add(h_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        settings_button = wx.Button(self, wx.ID_ANY, label='Settings')

        sizer.AddStretchSpacer(1)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        b_sizer = button_sizer.GetItem(1).GetSizer()

        b_sizer.Insert(0, settings_button, 0, wx.ALL, 5)

        for child in b_sizer.GetChildren():
            child = child.GetWindow()
            if isinstance(child, wx.Button) and child.GetLabel() == 'OK':
                child.SetLabel('Login')
                break

        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)

        def _on_settings_button(evt):
            try:
                from . import settings_dialog
            except ImportError:
                import settings_dialog

            dlg = settings_dialog.SQLOptionsDialog(self)
            if dlg.ShowModal() == wx.ID_OK:
                values = dlg.GetValue()
                for key, value in values.items():
                    setattr(Config, key, value)
            dlg.Destroy()

            evt.Skip()

        settings_button.Bind(wx.EVT_LEFT_UP, _on_settings_button)

        self.username_ctrl = username_ctrl
        self.password_ctrl = password_ctrl

        self.CenterOnParent()

    def GetValue(self):
        return (
            self.username_ctrl.GetValue(),
            self.password_ctrl.GetValue()
        )


class SQLConnector(ConnectorBase):

    def __init__(self, mainframe):
        super().__init__(mainframe, Config.database_name)
        self._connection: mysql.connector.MySQLConnection = None
        self._cursor: _MySQLCursor = None

    def connect(self):
        dlg = LoginDialog(self.mainframe)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                username, password = dlg.GetValue()
            else:
                return False
        except:  # NOQA
            raise RuntimeError('This should not happen')
        finally:
            dlg.Destroy()

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
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
            return False

        if username in Config.recent_users:
            Config.recent_users.remove(username)
        Config.recent_users.insert(0, username)

        while len(Config.recent_users) > 5:
            Config.recent_users = Config.recent_users[:-1]

        self._cursor = self._connection.cursor()
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


if __name__ == '__main__':
    app = wx.App()

    frame = wx.Frame(None, wx.ID_ANY, size=(100, 60))
    btn = wx.Button(frame, wx.ID_ANY, 'click_me', size=(50, 30))

    def _do(evt):
        dlg = LoginDialog(frame)
        if dlg.ShowModal() == wx.ID_OK:
            print(dlg.GetValue())
        dlg.Destroy()

        evt.Skip()


    btn.Bind(wx.EVT_BUTTON, _do)
    frame.Show()
    app.MainLoop()
