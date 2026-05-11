# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...database.db_connectors.mysql_connector import settings_dialog as _mysql_settings
from ...database.db_connectors.sqlite_connector import settings_dialog as _sqlite_settings
from ... import config as _config


if TYPE_CHECKING:
    from ... import ui as _ui


DBConfig    = _config.Config.database
MySQLConfig = _config.Config.database.mysql
SQLiteConfig = _config.Config.database.sqlite


class DatabaseMenu(QMenu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        super().__init__('Database', mainframe)
        self.mainframe = mainframe

        self.addAction('SQLite Settings').triggered.connect(self.on_sqlite_settings)
        self.addAction('MySQL Settings').triggered.connect(self.on_mysql_settings)
        self.addSeparator()
        self.addAction('Import Data').triggered.connect(self.on_import_data)

    def on_sqlite_settings(self):
        pass

    def on_mysql_settings(self):
        dlg = _mysql_settings.SQLOptionsDialog(self.mainframe)
        if dlg.exec() == dlg.Accepted:
            settings = dlg.GetValue()
            for key, value in settings.items():
                setattr(MySQLConfig, key, value)

    def on_import_data(self):
        dlg = _sqlite_settings.SQLOptionsDialog(self.mainframe)
        if dlg.exec() == dlg.Accepted:
            settings = dlg.GetValue()
            for key, value in settings.items():
                setattr(SQLiteConfig, key, value)
