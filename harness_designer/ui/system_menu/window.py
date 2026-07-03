# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets


if TYPE_CHECKING:
    from ... import ui as _ui


class WindowMenu(QtWidgets.QMenu):
    """Represent a window menu in :mod:`harness_designer.ui.system_menu.window`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`WindowMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        super().__init__('Window', mainframe)
        self.mainframe = mainframe
