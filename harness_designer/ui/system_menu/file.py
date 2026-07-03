# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets


if TYPE_CHECKING:
    from ... import ui as _ui


class FileMenu(QtWidgets.QMenu):
    """
    Represent a file menu in :mod:`harness_designer.ui.system_menu.file`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`FileMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('File', mainframe)
        self.mainframe = mainframe
