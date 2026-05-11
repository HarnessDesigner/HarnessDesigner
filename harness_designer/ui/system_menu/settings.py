# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ..dialogs import debug_settings as _debug_settings


if TYPE_CHECKING:
    from ... import ui as _ui


class SettingsMenu(QMenu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        super().__init__('Settings', mainframe)
        self.mainframe = mainframe

        self.addAction('Debug Settings').triggered.connect(self.on_debug_settings)

    def on_debug_settings(self):
        dlg = _debug_settings.DebugSettingsDialog(self.mainframe)
        if dlg.exec() == dlg.Accepted:
            dlg.SetValues()
            self.mainframe.update()   # QWidget.update() ≈ wx.Refresh(False)
