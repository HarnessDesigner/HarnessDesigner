# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu


if TYPE_CHECKING:
    from ... import ui as _ui


class FileMenu(QMenu):
    """Represent a file menu in :mod:`harness_designer.ui.system_menu.file`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`FileMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        super().__init__('File', mainframe)
        self.mainframe = mainframe
