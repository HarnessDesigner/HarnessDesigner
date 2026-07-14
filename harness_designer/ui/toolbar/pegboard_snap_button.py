# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
PegboardSnapButton — QToolButton that toggles Peg Board Editor grid
snapping and edits the manual snap-spacing override through a popup.

Left-clicking the button toggles snap-to-grid on/off; the state is shown
by a checked/unchecked checkbox composited onto the icon's bottom-right
corner -- the exact same convention
:class:`harness_designer.ui.toolbar.snap_angle_button.SnapAngleButton` uses
for rotation-drag snapping. Right-clicking opens a popup with an "Auto"
checkbox and a QDoubleSpinBox: while "Auto" is checked the manual override
is cleared (``None``), so
:meth:`harness_designer.gl.canvas_pegboard.canvas.Canvas.snap_to_grid`
keeps using the live grid LOD spacing (``self._grid.grid_spacing``);
unchecking "Auto" (or editing the spin box, which implicitly unchecks it)
commits a fixed spacing value that overrides the LOD spacing instead.

Unlike :class:`SnapAngleButton`'s angle popup, there is no small enumerable
set of legal manual-spacing values to autocomplete against, so this uses a
plain QDoubleSpinBox + a QCheckBox rather than an
:class:`~harness_designer.ui.widgets.autocomplete_combobox.AutoCompleteComboBox`
-- the interaction *shape* (left = toggle, right = adjust the related
setting) is what's mirrored, not the exact popup widgetry.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class PegboardSnapButton(QtWidgets.QToolButton):
    """
    A QToolButton for use in a QToolBar.

    Renders the grid-snap icon (with a checkbox state overlay). Left click
    toggles grid snapping; right click opens the manual-spacing popup.

    Signals
    -------
    snapEnabledChanged(bool)     emitted when the toggle state changes.
    manualSpacingChanged(object) emitted when the manual spacing override
                                 changes; carries a ``float`` or ``None``
                                 (``None`` means "Auto").

    Parameters
    ----------
    label          : Human-readable name → tooltip.
    checked_icon   : QIcon shown while snapping is enabled.
    unchecked_icon : QIcon shown while snapping is disabled.
    """

    snapEnabledChanged: QtCore.SignalInstance = QtCore.Signal(bool)
    manualSpacingChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent: QtWidgets.QWidget, label: str,
                 checked_icon: QtGui.QIcon, unchecked_icon: QtGui.QIcon):
        super().__init__(parent)

        self._label = label
        self._checked_icon = checked_icon
        self._unchecked_icon = unchecked_icon

        self._enabled_state = False
        self._manual_spacing: float | None = None

        # ── icon on top, spacing text centred below ─────────────────────────
        self.setIconSize(QtCore.QSize(32, 32))
        self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.setFixedHeight(55)
        self.setFixedWidth(72)

        self.setToolTip(f'{label}\nLeft click: enable/disable\n'
                        f'Right click: set manual grid spacing')

        self.clicked.connect(self._on_clicked)

        # ── right-click popup: "Auto" checkbox + manual spacing spin box ───
        self._menu = QtWidgets.QMenu(self)
        widget_action = QtWidgets.QWidgetAction(self._menu)

        self._row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self._row)

        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._auto_check = QtWidgets.QCheckBox('Auto')
        self._auto_check.setChecked(True)
        self._auto_check.toggled.connect(self._on_auto_toggled)
        layout.addWidget(self._auto_check)

        self._spin = QtWidgets.QDoubleSpinBox()
        self._spin.setRange(0.01, 9999.99)
        self._spin.setSingleStep(1.0)
        self._spin.setDecimals(2)
        self._spin.setSuffix(' mm')
        self._spin.setFixedWidth(90)
        self._spin.setKeyboardTracking(True)  # emit while the user types
        self._spin.setValue(10.0)
        self._spin.setEnabled(False)
        self._spin.valueChanged.connect(self._on_spin_changed)
        layout.addWidget(self._spin)

        widget_action.setDefaultWidget(self._row)
        self._menu.addAction(widget_action)

        self._refresh_icon()
        self._refresh_text()

    # ── public API ─────────────────────────────────────────────────────────

    def GetManualSpacing(self) -> float | None:
        """Return the current manual spacing override (``None`` = Auto)."""
        return self._manual_spacing

    def SetManualSpacing(self, value: float | None) -> None:
        """Set the manual spacing override programmatically (no signal
        emitted)."""
        self._manual_spacing = None if value is None else float(value)

        with QtCore.QSignalBlocker(self._auto_check), QtCore.QSignalBlocker(self._spin):
            self._auto_check.setChecked(self._manual_spacing is None)
            self._spin.setEnabled(self._manual_spacing is not None)

            if self._manual_spacing is not None:
                self._spin.setValue(self._manual_spacing)

        self._refresh_text()

    def IsSnapEnabled(self) -> bool:
        """Return whether grid snapping is enabled."""
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

    def _refresh_icon(self) -> None:
        self.setIcon(self._checked_icon if self._enabled_state
                     else self._unchecked_icon)

    def _refresh_text(self) -> None:
        if self._manual_spacing is None:
            self.setText('Auto')
        else:
            self.setText(f'{self._manual_spacing:g}')

    def _on_auto_toggled(self, checked: bool) -> None:
        self._spin.setEnabled(not checked)

        new_value = None if checked else self._spin.value()
        changed = new_value != self._manual_spacing
        self._manual_spacing = new_value

        self._refresh_text()

        if changed:
            self.manualSpacingChanged.emit(new_value)

    def _on_spin_changed(self, value: float) -> None:
        if self._auto_check.isChecked():
            return

        changed = value != self._manual_spacing
        self._manual_spacing = value

        self._refresh_text()

        if changed:
            self.manualSpacingChanged.emit(value)
