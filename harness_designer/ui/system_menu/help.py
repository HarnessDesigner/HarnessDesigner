# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from ..dialogs import about_dialog as _about_dialog


if TYPE_CHECKING:
    from ... import ui as _ui


class HelpMenu(QtWidgets.QMenu):
    """
    Represent a help menu in :mod:`harness_designer.ui.system_menu.help`.
    """
    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`HelpMenu` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__('Help', mainframe)
        self.mainframe = mainframe

        self.addAction('About Harness Designer').triggered.connect(self.on_about)

    def on_about(self):
        """Open the About dialog."""

        dlg = _about_dialog.AboutDialog(self.mainframe)
        dlg.exec()
