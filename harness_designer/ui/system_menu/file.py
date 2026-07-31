# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


class FileMenu(QtWidgets.QMenu):
    """
    Represent a file menu in :mod:`harness_designer.ui.system_menu.file`.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`FileMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('File', mainframe)
        self.mainframe = mainframe

        self.addAction('Load Project...').triggered.connect(self.on_load_project)

    @_check_types.do
    def on_load_project(self):
        """
        Handle the load project action.
        """

        self.mainframe.load_project()
