# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets


if TYPE_CHECKING:
    from ... import ui as _ui


class EditMenu(QtWidgets.QMenu):
    """
    Represent an edit menu in :mod:`harness_designer.ui.system_menu.edit`.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`EditMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('Edit', mainframe)
        self.mainframe = mainframe
