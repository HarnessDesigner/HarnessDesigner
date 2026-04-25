from typing import TYPE_CHECKING

import wx

from ...database.db_connectors.mysql_connector import settings_dialog as _mysql_settings
from ...database.db_connectors.sqlite_connector import settings_dialog as _sqlite_settings

from ... import config as _config

DBConfig = _config.Config.database
MySQLConfig = _config.Config.database.mysql
SQLiteConfig = _config.Config.database.sqlite


if TYPE_CHECKING:
    from ... import ui as _ui


class DatabaseMenu(wx.Menu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        wx.Menu.__init__(self)

        menu_item = self.Append(wx.ID_ANY, 'SQLite Settings')
        mainframe.Bind(wx.EVT_MENU, self.on_sqlite_settings, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'MySQL Settings')
        mainframe.Bind(wx.EVT_MENU, self.on_mysql_settings, id=menu_item.GetId())

        self.AppendSeparator()

        menu_item = self.Append(wx.ID_ANY, 'Import Data')
        mainframe.Bind(wx.EVT_MENU, self.on_import_data, id=menu_item.GetId())

    def on_sqlite_settings(self, _):
        pass

    def on_mysql_settings(self, _):
        dlg = _mysql_settings.SQLOptionsDialog(self.mainframe)

        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.GetValue()

            for key, value in settings.items():
                setattr(MySQLConfig, key, value)

        dlg.Destroy()

    def on_import_data(self, _):
        dlg = _sqlite_settings.SQLOptionsDialog(self.mainframe)

        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.GetValue()

            for key, value in settings.items():
                setattr(SQLiteConfig, key, value)

        dlg.Destroy()
