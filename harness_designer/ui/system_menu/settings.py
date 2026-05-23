# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ..dialogs import debug_settings as _debug_settings


if TYPE_CHECKING:
    from ... import ui as _ui


class SettingsMenu(QMenu):
    """Represent a settings menu in :mod:`harness_designer.ui.system_menu.settings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`SettingsMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        super().__init__('Settings', mainframe)
        self.mainframe = mainframe

        self.addAction('Debug Settings').triggered.connect(self.on_debug_settings)

    def on_debug_settings(self):
        """Handle the debug settings event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        dlg = _debug_settings.DebugSettingsDialog(self.mainframe)
        if dlg.exec() == dlg.Accepted:
            dlg.SetValues()
            self.mainframe.update()   # QWidget.update() ≈ wx.Refresh(False)
