# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Borderless progress dialog shown while the application shuts down."""

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtWidgets


if TYPE_CHECKING:
    from ... import ui as _ui


class ClosingDialog(QtWidgets.QDialog):
    """Borderless, button-less progress dialog shown during shutdown.

    The dialog is always shown with :meth:`show`, never :meth:`exec`, so it
    never runs a nested event loop — the caller's shutdown sequence keeps
    driving the main thread's event loop while this is visible. Application
    modality is enough to block user input to the rest of the UI without
    that nested loop.
    """

    def __init__(self, parent: "_ui.MainFrame", total_steps: int = 1):
        """Build and center the shutdown progress dialog.

        :param parent: Main window the dialog is centered on and blocks
            input to.
        :type parent: :class:`_ui.MainFrame`
        :param total_steps: Number of steps :meth:`set_step` will be driven
            through; sets the progress bar's maximum.
        :type total_steps: int
        """

        super().__init__(
            parent,
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        title_label = QtWidgets.QLabel('Closing Harness Designer', self)
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)

        self._bar = QtWidgets.QProgressBar(self)
        self._bar.setRange(0, total_steps)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)

        self._message_label = QtWidgets.QLabel('', self)
        self._message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        layout.addWidget(title_label)
        layout.addWidget(self._bar)
        layout.addWidget(self._message_label)

        self.setFixedWidth(320)
        self.adjustSize()
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Center this dialog over its parent window.

        """
        parent = self.parent()

        if parent is None:
            return

        parent_geo = parent.frameGeometry()
        geo = self.frameGeometry()
        geo.moveCenter(parent_geo.center())
        self.move(geo.topLeft())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_step(self, step: int) -> None:
        """Advance the progress bar to ``step``.

        :param step: Step index, where ``0`` is the bar's starting position
            and ``total_steps`` (from the constructor) is fully complete.
        :type step: int
        """
        self._bar.setValue(step)

    def set_message(self, text: str) -> None:
        """Update the status label shown below the progress bar.

        :param text: Status text describing the current shutdown step.
        :type text: str
        """
        self._message_label.setText(text)
