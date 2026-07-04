# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets


try:
    import mysql
except ImportError:
    mysql = None


from ... import config as _config


if TYPE_CHECKING:
    from ... import ui as _ui


DBConfig = _config.Config.database
MySQLConfig = _config.Config.database.mysql
SQLiteConfig = _config.Config.database.sqlite


class DatabaseMenu(QtWidgets.QMenu):
    """
    Represent a database menu in :mod:`harness_designer.ui.system_menu.database`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`DatabaseMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('Database', mainframe)
        self.mainframe = mainframe

        self.addAction('SQLite Settings').triggered.connect(self.on_sqlite_settings)

        if mysql is not None:
            self.addAction('MySQL Settings').triggered.connect(self.on_mysql_settings)

        self.addSeparator()

    def on_sqlite_settings(self):
        """
        Handle the sqlite settings event.
        """

        from ...database.db_connectors.sqlite_connector import settings_dialog as _sqlite_settings

        pass

    if mysql is None:
        def on_mysql_settings(self):
            pass

    else:
        def on_mysql_settings(self):
            """
            Handle the mysql settings event.
            """

            from ...database.db_connectors.mysql_connector import settings_dialog as _mysql_settings

            dlg = _mysql_settings.SQLOptionsDialog(self.mainframe)
            if dlg.exec() == dlg.Accepted:
                settings = dlg.GetValue()
                for key, value in settings.items():
                    setattr(MySQLConfig, key, value)
