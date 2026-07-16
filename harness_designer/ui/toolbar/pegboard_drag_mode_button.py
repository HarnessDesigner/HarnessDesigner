# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
PegboardDragModeButton — QToolButton that switches the Peg Board Editor's
drag-repositioning behavior between "clamp" and "pull"
(see ``Config.editor_pegboard.drag.mode`` /
``gl.canvas_pegboard.canvas.Canvas._propagate_pull``).

Unlike :class:`~harness_designer.ui.toolbar.pegboard_snap_button.PegboardSnapButton`,
there is no secondary setting to adjust with a right-click popup -- this is
a plain binary switch, so only the left-click-toggles half of that
button's interaction shape is mirrored here. Left-clicking flips between
the two modes; the button's own text shows which one is currently active
("Clamp"/"Pull") rather than a checkbox-overlay icon, since there is no
existing icon asset for either concept.
"""

from PySide6 import QtCore
from PySide6 import QtWidgets


class PegboardDragModeButton(QtWidgets.QToolButton):
    """
    A QToolButton for use in a QToolBar.

    Left click toggles the peg board's drag mode between "clamp" (dragging
    stops at each segment's length limit) and "pull" (dragging past a
    taut segment pulls the neighboring point along instead of stopping).

    Signals
    -------
    dragModeChanged(str)  emitted when the mode changes; carries "clamp" or
                          "pull".
    """

    dragModeChanged: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

        self._mode = 'clamp'

        self.setCheckable(False)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setFixedHeight(55)
        self.setFixedWidth(72)

        self.clicked.connect(self._on_clicked)

        self._refresh()

    # ── public API ─────────────────────────────────────────────────────────

    def GetDragMode(self) -> str:
        """Return the current drag mode ("clamp" or "pull")."""
        return self._mode

    def SetDragMode(self, mode: str) -> None:
        """Set the drag mode programmatically (no signal emitted)."""
        self._mode = 'pull' if mode == 'pull' else 'clamp'
        self._refresh()

    # ── internals ──────────────────────────────────────────────────────────

    def _on_clicked(self, _: bool = False) -> None:
        self._mode = 'pull' if self._mode == 'clamp' else 'clamp'
        self._refresh()
        self.dragModeChanged.emit(self._mode)

    def _refresh(self) -> None:
        label = 'Pull' if self._mode == 'pull' else 'Clamp'
        self.setText(label)
        self.setToolTip(
            f'Drag mode: {label}\n'
            'Click to switch between "Clamp" (dragging stops at each '
            'segment\'s length limit) and "Pull" (dragging past a taut '
            'segment pulls the neighboring point along).')
