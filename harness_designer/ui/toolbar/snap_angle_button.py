# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
SnapAngleButton — QToolButton that toggles rotation-drag snapping and edits
the snap angle through a popup AutoCompleteComboBox.

Left-clicking the button toggles snapping on/off; the state is shown by a
checked/unchecked checkbox composited onto the icon's bottom-right corner
(the same convention the view toolbar uses). Right-clicking opens a popup
with the autocomplete combo listing every valid snap angle — a valid angle
has at most 2 decimal places and divides the 360 degree range evenly, which
makes the set fully enumerable (the divisors of 36000 in hundredths). Typed
entries autocomplete inline and are coerced to the nearest valid value on
commit, so an illegal angle can never be selected.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ..widgets import autocomplete_combobox as _acb


def valid_snap_angles(max_angle: float = 180.0) -> list[float]:
    """Return every legal snap angle up to ``max_angle``, ascending.

    Legal: at most 2 decimal places AND divides 360 evenly — i.e. the value
    in hundredths is a divisor of 36000.
    """
    limit = int(round(max_angle * 100.0))

    return [d / 100.0 for d in range(1, limit + 1) if 36000 % d == 0]


def _format_angle(value: float) -> str:
    """Format a snap angle without trailing zeros (15, 22.5, 0.05)."""
    return f'{value:g}'


class SnapAngleButton(QtWidgets.QToolButton):
    """
    A QToolButton for use in a QToolBar.

    Renders the snap icon (with a checkbox state overlay) and the current
    snap angle centred below it. Left click toggles snapping; right click
    opens the angle popup.

    Signals
    -------
    snapEnabledChanged(bool)  emitted when the toggle state changes.
    snapAngleChanged(float)   emitted when a new valid angle is committed.

    Parameters
    ----------
    label          : Human-readable name → tooltip.
    checked_icon   : QIcon shown while snapping is enabled.
    unchecked_icon : QIcon shown while snapping is disabled.
    """

    snapEnabledChanged: QtCore.SignalInstance = QtCore.Signal(bool)
    snapAngleChanged: QtCore.SignalInstance = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget, label: str,
                 checked_icon: QtGui.QIcon, unchecked_icon: QtGui.QIcon):
        super().__init__(parent)

        self._label = label
        self._checked_icon = checked_icon
        self._unchecked_icon = unchecked_icon

        self._angles = valid_snap_angles()
        self._value = self._angles[0]
        self._enabled_state = False

        # ── icon on top, angle text centred below ──────────────────────────
        self.setIconSize(QtCore.QSize(32, 32))
        self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.setFixedHeight(55)
        self.setFixedWidth(72)

        self.setToolTip(f'{label}\nLeft click: enable/disable\n'
                        f'Right click: set snap angle')

        self.clicked.connect(self._on_clicked)

        # ── right-click popup with the autocomplete combo ──────────────────
        self._menu = QtWidgets.QMenu(self)
        widget_action = QtWidgets.QWidgetAction(self._menu)

        self._row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self._row)

        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._combo = _acb.AutoCompleteComboBox(
            choices=[_format_angle(v) for v in self._angles])
        self._combo.setFixedWidth(95)
        self._combo.activated.connect(self._on_combo_committed)
        self._combo.lineEdit().editingFinished.connect(self._on_combo_committed)
        layout.addWidget(self._combo)

        widget_action.setDefaultWidget(self._row)
        self._menu.addAction(widget_action)

        self._refresh_icon()
        self._refresh_text()

    # ── public API ─────────────────────────────────────────────────────────

    def GetValue(self) -> float:
        """Return the current snap angle."""
        return self._value

    def SetValue(self, value: float) -> None:
        """Set the snap angle programmatically (coerced to the nearest
        valid value, no signal emitted)."""
        self._value = self._nearest_valid(value)

        with QtCore.QSignalBlocker(self._combo):
            self._combo.SetValue(_format_angle(self._value))

        self._refresh_text()

    def IsSnapEnabled(self) -> bool:
        """Return whether snapping is enabled."""
        return self._enabled_state

    def SetSnapEnabled(self, enabled: bool) -> None:
        """Set the toggle state programmatically (no signal emitted)."""
        self._enabled_state = bool(enabled)
        self._refresh_icon()

    # ── internals ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self._menu.exec(self.mapToGlobal(self.rect().bottomLeft()))
            event.accept()
            return

        super().mousePressEvent(event)

    def _on_clicked(self, _: bool = False) -> None:
        self._enabled_state = not self._enabled_state
        self._refresh_icon()
        self.snapEnabledChanged.emit(self._enabled_state)

    def _nearest_valid(self, value) -> float:
        """Coerce any input to the closest legal snap angle."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return self._value

        return min(self._angles, key=lambda a: abs(a - v))

    def _refresh_icon(self) -> None:
        self.setIcon(self._checked_icon if self._enabled_state
                     else self._unchecked_icon)

    def _refresh_text(self) -> None:
        self.setText(f'{_format_angle(self._value)}°')

    def _on_combo_committed(self, *_) -> None:
        new_value = self._nearest_valid(self._combo.GetValue())

        changed = new_value != self._value
        self._value = new_value

        # reflect the (possibly coerced) value back into the combo
        with QtCore.QSignalBlocker(self._combo):
            self._combo.SetValue(_format_angle(self._value))

        self._refresh_text()

        if changed:
            self.snapAngleChanged.emit(self._value)
