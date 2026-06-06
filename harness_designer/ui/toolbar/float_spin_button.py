# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
FloatSpinToolButton — QToolButton with icon on top, current value
centred below, and a dropdown QDoubleSpinBox for editing.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class FloatSpinButton(QtWidgets.QToolButton):
    """
    A QToolButton for use in a QToolBar.

    Renders an icon with the current float value centred below it.
    Clicking anywhere on the button opens a dropdown QDoubleSpinBox.

    Signals
    -------
    valueChanged(float)  emitted on every spin-box change.

    Parameters
    ----------
    label     : Human-readable name → tooltip + dropdown label.
    icon      : QIcon displayed above the value text.
                If None the style falls back to text-only.
    min_val   : Spin-box minimum.
    max_val   : Spin-box maximum.
    step      : Single-step increment.
    decimals  : Decimal places shown on the button and in the spin box.
    suffix    : Optional unit string, e.g. " m/s" or "%".
    """

    valueChanged: QtCore.SignalInstance = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget, label: str, icon: QtGui.QIcon,
                 min_val: float, max_val: float, step: float = 0.1, decimals: int = 2,
                 suffix: str = ""):

        super().__init__(parent)

        self._label = label
        self._decimals = decimals
        self._suffix = suffix

        # ── icon on top, value text centred below ─────────────────────────
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.setFixedHeight(55)
        self.setFixedWidth(72)

        self.setToolTip(label)
        self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self._refresh_text(0.0)

        # ── dropdown menu with spin box ────────────────────────
        menu = QtWidgets.QMenu(self)
        widget_action = QtWidgets.QWidgetAction(menu)

        self._row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self._row)

        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._spin = QtWidgets.QDoubleSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setSingleStep(step)
        self._spin.setDecimals(decimals)
        self._spin.setValue(0.0)
        self._spin.setSuffix(suffix)
        self._spin.setFixedWidth(85)
        self._spin.setKeyboardTracking(True)   # emit while the user types
        self._spin.valueChanged.connect(self._on_spin_changed)
        layout.addWidget(self._spin)
        # row.setLayout(layout)

        widget_action.setDefaultWidget(self._row)
        menu.addAction(widget_action)

        self.setMenu(menu)

    def GetValue(self) -> float:
        """Return the current float value."""
        return self._spin.value()

    def SetValue(self, v: float) -> None:
        """Set the value programmatically (also updates button text)."""
        with QtCore.QSignalBlocker(self._spin):
            self._spin.setValue(v)  # valueChanged is suppressed
        self._refresh_text(v)  # still update the button label

    # ── internals ─────────────────────────────────────────────────────────

    def _refresh_text(self, value: float) -> None:
        # Only the formatted number goes under the icon; the icon/tooltip
        # conveys the label so the button stays compact.
        self.setText(f"{value:.{self._decimals}f}{self._suffix}")

    def _on_spin_changed(self, value: float) -> None:
        self._refresh_text(value)
        self.valueChanged.emit(value)
        # QtWidgets.QApplication.processEvents(
        #     QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        # )
