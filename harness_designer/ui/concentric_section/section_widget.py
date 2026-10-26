# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The concentric twisting widget: the cross-section on the left, an
information pane on the right, side by side with a draggable sash between
them -- the same splitter the circuit editor uses. Drag the sash all the way
right to close the information pane and back to open it.

It is built to be drawn into a buffer and shown as a GL texture in the peg
board view, the way the floating wire tables are (``ui.pegboard_table.
mdi_host`` -> ``objects.objects_pegboard.table``): ``host_offscreen()`` keeps
it off the real screen and ``grab_rgba()`` returns the same ``(bytes, width,
height)`` RGBA8888 buffer ``PegboardTableHost.grab_rgba`` does.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import info_panel as _info_panel
from . import section_model as _section_model
from . import section_view as _section_view
from ... import check_types as _check_types


# Logical pixels per world mm for the hidden widget (the same fixed scale
# ui.pegboard_table.mdi_host.PIXELS_PER_MM uses), so a widget sized in mm on
# the peg board is this many times as many pixels when it is drawn.
PIXELS_PER_MM = 6.0

# A splitter like the circuit editor's panel (its 3 : 1), but the information
# pane here has more to say in less room, so it opens at 3 : 2.
_VIEW_STRETCH = 3
_INFO_STRETCH = 2
_HANDLE_WIDTH = 6
_HANDLE_STYLE = 'QSplitter::handle { background:#3a3a3a; }'


class ConcentricSectionWidget(QtWidgets.QWidget):
    """The cross-section pane and the wire information pane, in a splitter."""

    # re-emitted from the cross-section so the owner needs only this widget
    cable_selected: QtCore.SignalInstance = QtCore.Signal(object)
    cable_moved: QtCore.SignalInstance = QtCore.Signal(object, float, float)
    cable_move_finished: QtCore.SignalInstance = QtCore.Signal(object)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self._details: dict[str | bytes, _section_model.WireDetail] = {}
        self._open_sizes: list[int] = []

        self._view = _section_view.CrossSectionView(self)
        self._panel = _info_panel.WireInfoPanel(self)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self._view)
        self._splitter.addWidget(self._panel)
        self._splitter.setStretchFactor(0, _VIEW_STRETCH)
        self._splitter.setStretchFactor(1, _INFO_STRETCH)
        self._splitter.setSizes([_VIEW_STRETCH * 200, _INFO_STRETCH * 200])
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, True)
        self._splitter.setHandleWidth(_HANDLE_WIDTH)
        self._splitter.setStyleSheet(_HANDLE_STYLE)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        self._view.cable_selected.connect(self._on_cable_selected)
        self._view.cable_moved.connect(self._on_cable_moved)
        self._view.cable_move_finished.connect(self.cable_move_finished.emit)

        self._panel.clear()

    # ── data ──────────────────────────────────────────────────────────────
    @_check_types.do
    def set_section(self, spec: _section_model.SectionSpec) -> None:
        """Show a cross-section (clears the selection's information)."""
        self._view.set_section(spec)
        self._refresh_panel()

    @_check_types.do
    def set_wire_details(self, details: dict[str | bytes, _section_model.WireDetail]) -> None:
        """The information to show for each wire, by cable key."""
        self._details = details
        self._refresh_panel()

    @_check_types.do
    def view(self) -> _section_view.CrossSectionView:
        return self._view

    @_check_types.do
    def panel(self) -> _info_panel.WireInfoPanel:
        return self._panel

    @_check_types.do
    def select(self, key: str | bytes | None) -> None:
        """Select a cable (or nothing)."""
        self._view.set_selected_key(key)

    # ── the sash ──────────────────────────────────────────────────────────
    @_check_types.do
    def is_info_open(self) -> bool:
        """Whether the information pane is showing (the sash is not all the way right)."""
        return self._splitter.sizes()[1] > 0

    @_check_types.do
    def set_info_open(self, is_open: bool) -> None:
        """Open or close the information pane, as dragging the sash would."""
        sizes = self._splitter.sizes()

        if is_open == (sizes[1] > 0):
            return

        if is_open:
            if self._open_sizes:
                self._splitter.setSizes(self._open_sizes)
            else:
                total = sum(sizes)
                info = total * _INFO_STRETCH // (_VIEW_STRETCH + _INFO_STRETCH)
                self._splitter.setSizes([total - info, info])
        else:
            self._open_sizes = sizes
            self._splitter.setSizes([sum(sizes), 0])

    # ── the information pane follows the selection ────────────────────────
    @_check_types.do
    def _on_cable_selected(self, key: object) -> None:
        self._refresh_panel()
        self.cable_selected.emit(key)

    @_check_types.do
    def _on_cable_moved(self, key: object, x_mm: float, y_mm: float) -> None:
        # the wire's distance from the axis changed, so its helix length did
        self._refresh_panel()
        self.cable_moved.emit(key, x_mm, y_mm)

    @_check_types.do
    def _refresh_panel(self) -> None:
        key = self._view.selected_key()
        if key is None:
            self._panel.clear()
            return

        spec = self._view.section()
        placed = spec.find(key)

        detail = self._details.get(key)
        if detail is None:
            detail = _section_model.WireDetail(name=str(key))

        helix = _section_model.helix_length_mm(
            spec.run_length_mm, placed.axis_distance_mm, placed.lay_length_mm)
        self._panel.show_wire(detail, placed.cable, spec.run_length_mm, helix)

    # ── the buffer, for the GL texture ────────────────────────────────────
    @_check_types.do
    def host_offscreen(self) -> None:
        """Keep the widget off the real screen but fully laid out and
        paintable, with a real alpha channel, for :meth:`grab_rgba`.

        ``show()`` is still called: ``WA_DontShowOnScreen`` only stops it
        reaching the screen, and a widget that was never shown is never laid
        out, which makes a forced grab unstable (see MEMORY.md, Peg Board
        Editor).
        """
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.show()

    @_check_types.do
    def resize_mm(self, width_mm: float, height_mm: float) -> None:
        """Size the widget from a peg-board size in world mm
        (``pjt_pegboard_sections.size``)."""
        self.resize(int(width_mm * PIXELS_PER_MM), int(height_mm * PIXELS_PER_MM))

    @_check_types.do
    def grab_rgba(self) -> tuple[bytes, int, int]:
        """Capture the widget's current appearance.

        :returns: Raw RGBA8888 bytes, width, height -- ready for
            ``glTexImage2D``.
        :rtype: tuple[bytes, int, int]
        """
        QtWidgets.QApplication.processEvents()

        pixmap = self.grab()
        image = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        return bytes(image.constBits()), image.width(), image.height()
