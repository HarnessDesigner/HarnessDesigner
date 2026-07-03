
from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import file as _file
from . import edit as _edit
from . import database as _database
from . import settings as _settings
from . import view as _view
from . import window as _window
from . import help as _help


if TYPE_CHECKING:
    from ... import ui as _ui


class SystemMenu(QtWidgets.QMenuBar):
    """
    Represent a system menu in :mod:`harness_designer.ui.system_menu.__init__`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`SystemMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__(mainframe)
        self.mainframe = mainframe

        self.file = _file.FileMenu(mainframe)
        self.addMenu(self.file)

        self.edit = _edit.EditMenu(mainframe)
        self.addMenu(self.edit)

        self.view = _view.ViewMenu(mainframe)
        self.addMenu(self.view)

        self.database = _database.DatabaseMenu(mainframe)
        self.addMenu(self.database)

        self.settings = _settings.SettingsMenu(mainframe)
        self.addMenu(self.settings)

        self.window = _window.WindowMenu(mainframe)
        self.addMenu(self.window)

        self.help = _help.HelpMenu(mainframe)
        self.addMenu(self.help)
