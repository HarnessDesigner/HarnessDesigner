from typing import TYPE_CHECKING

import wx
from . import file as _file
from . import edit as _edit
from . import database as _database
from . import settings as _settings
from . import view as _view
from . import window as _window
from . import help as _help


if TYPE_CHECKING:
    from ... import ui as _ui


class SystemMenu(wx.MenuBar):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        wx.MenuBar.__init__(self)

        self.file = _file.FileMenu(self.mainframe)
        self.file_menu = self.Append(self.file, "File")

        self.edit = _edit.EditMenu(self.mainframe)
        self.edit_menu = self.Append(self.edit, "Edit")

        self.view = _view.ViewMenu(self.mainframe)
        self.view_menu = self.Append(self.view, "View")

        self.database = _database.DatabaseMenu(self.mainframe)
        self.database_menu = self.Append(self.database, "Database")

        self.settings = _settings.SettingsMenu(self.mainframe)
        self.settings_menu = self.Append(self.settings, "Settings")

        self.window = _window.WindowMenu(self.mainframe)
        self.window_menu = self.Append(self.window, "Window")

        self.help = _help.HelpMenu(self.mainframe)
        self.help_menu = self.Append(self.help, "Help")
