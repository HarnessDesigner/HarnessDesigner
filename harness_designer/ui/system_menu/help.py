# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu


if TYPE_CHECKING:
    from ... import ui as _ui


class HelpMenu(QMenu):
    def __init__(self, mainframe: "_ui.MainFrame"):
        super().__init__('Help', mainframe)
        self.mainframe = mainframe
