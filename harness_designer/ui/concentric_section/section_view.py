# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The custom-drawn cross-section of the harness.

Draws the bundle outline, the layer guide rings and every placed cable
(:mod:`.wire_painter`). Click selects a cable; dragging it moves the WHOLE
cable -- every conductor with it -- and reports the new place. The view scales
to fit the content as it was when :meth:`CrossSectionView.set_section` (or
:meth:`~CrossSectionView.refit`) last ran, and does NOT rescale while a cable
is dragged, so dragging never makes the picture jump.
"""

import math

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import section_model as _section_model
from . import wire_painter as _wire_painter
from ... import check_types as _check_types


# Space kept round the content, in mm.
MARGIN_MM = 0.6

# Guide rings and the selection ring.
_GUIDE_ALPHA = 120


class CrossSectionView(QtWidgets.QWidget):
    """The left pane: the cross-section itself."""

    # the selected cable's key, or None when nothing is selected
    cable_selected: QtCore.SignalInstance = QtCore.Signal(object)
    # key, new x_mm, new y_mm -- while a cable is being dragged
    cable_moved: QtCore.SignalInstance = QtCore.Signal(object, float, float)
    # key -- when the drag ends (the place to save)
    cable_move_finished: QtCore.SignalInstance = QtCore.Signal(object)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self._spec = _section_model.SectionSpec()
        self._fit_radius_mm = MARGIN_MM
        self._selected_key: str | bytes | None = None
        self._dragging: _section_model.PlacedCable | None = None
        self._last_x_mm = 0.0
        self._last_y_mm = 0.0

        self.setMinimumSize(80, 80)

    # ── data ──────────────────────────────────────────────────────────────
    @_check_types.do
    def set_section(self, spec: _section_model.SectionSpec) -> None:
        """Show *spec* and fit the view to it."""
        self._spec = spec
        self.refit()

    @_check_types.do
    def section(self) -> _section_model.SectionSpec:
        return self._spec

    @_check_types.do
    def refit(self) -> None:
        """Rescale so everything now in the section fits."""
        self._fit_radius_mm = self._spec.content_radius_mm() + MARGIN_MM
        self.update()

    @_check_types.do
    def selected_key(self) -> str | bytes | None:
        return self._selected_key

    @_check_types.do
    def set_selected_key(self, key: str | bytes | None) -> None:
        if key == self._selected_key:
            return

        self._selected_key = key
        self.update()
        self.cable_selected.emit(key)

    # ── geometry ──────────────────────────────────────────────────────────
    @_check_types.do
    def _scale(self, width: int, height: int) -> float:
        """Pixels per mm for a view of this size."""
        return min(width, height) / (2.0 * self._fit_radius_mm)

    @_check_types.do
    def _to_mm(self, pos: QtCore.QPointF) -> tuple[float, float]:
        scale = self._scale(self.width(), self.height())
        return ((pos.x() - self.width() / 2.0) / scale, (pos.y() - self.height() / 2.0) / scale)

    # ── drawing ───────────────────────────────────────────────────────────
    @_check_types.do
    def _paint_section(self, painter: QtGui.QPainter, width: int, height: int, scale: float) -> None:
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.save()
        painter.translate(width / 2.0, height / 2.0)
        painter.scale(scale, scale)

        palette = self.palette()
        spec = self._spec

        if spec.envelope_dia_mm > 0.0:
            radius = spec.envelope_dia_mm / 2.0
            fill = QtGui.QColor(palette.color(QtGui.QPalette.ColorRole.Window))
            fill.setAlpha(190)
            outline = QtGui.QPen(palette.color(QtGui.QPalette.ColorRole.Mid))
            outline.setCosmetic(True)
            outline.setWidthF(1.5)
            painter.setPen(outline)
            painter.setBrush(fill)
            painter.drawEllipse(QtCore.QPointF(0.0, 0.0), radius, radius)

        guide_color = QtGui.QColor(palette.color(QtGui.QPalette.ColorRole.Mid))
        guide_color.setAlpha(_GUIDE_ALPHA)
        guide = QtGui.QPen(guide_color)
        guide.setCosmetic(True)
        guide.setWidthF(1.0)
        guide.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(guide)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        for diameter in spec.layer_dia_mm:
            painter.drawEllipse(QtCore.QPointF(0.0, 0.0), diameter / 2.0, diameter / 2.0)

        for placed in spec.cables:
            painter.save()
            painter.translate(placed.x_mm, placed.y_mm)
            _wire_painter.paint_cable(painter, placed.cable, placed.angle_deg)
            painter.restore()

        if self._selected_key is not None:
            placed = spec.find(self._selected_key)
            ring = QtGui.QPen(palette.color(QtGui.QPalette.ColorRole.Highlight))
            ring.setCosmetic(True)
            ring.setWidthF(2.0)
            painter.setPen(ring)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            radius = placed.cable.radius_mm + 0.08
            painter.drawEllipse(QtCore.QPointF(placed.x_mm, placed.y_mm), radius, radius)

        painter.restore()

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        self._paint_section(painter, self.width(), self.height(), self._scale(self.width(), self.height()))
        painter.end()

    @_check_types.do
    def render_image(self, px_per_mm: float) -> QtGui.QImage:
        """Draw the section at a FIXED scale into a transparent image sized to
        hold the content (independent of this widget's own size).

        :param px_per_mm: Pixels per millimetre.
        :type px_per_mm: float
        :returns: A premultiplied ARGB32 image.
        :rtype: :class:`QtGui.QImage`
        """
        side = max(32, int(math.ceil(2.0 * self._fit_radius_mm * px_per_mm)))
        image = QtGui.QImage(side, side, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(image)
        self._paint_section(painter, side, side, px_per_mm)
        painter.end()
        return image

    # ── mouse: select, and drag a cable as ONE unit ───────────────────────
    @_check_types.do
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        x_mm, y_mm = self._to_mm(event.position())
        placed = self._spec.hit_test(x_mm, y_mm)

        if placed is None:
            self._dragging = None
            self.set_selected_key(None)
            return

        self.set_selected_key(placed.cable.key)
        self._dragging = placed
        self._last_x_mm = x_mm
        self._last_y_mm = y_mm

    @_check_types.do
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._dragging is None:
            return

        x_mm, y_mm = self._to_mm(event.position())

        # the cable's own x/y move; its conductors are drawn relative to it, so they all go together
        self._dragging.x_mm += x_mm - self._last_x_mm
        self._dragging.y_mm += y_mm - self._last_y_mm
        self._last_x_mm = x_mm
        self._last_y_mm = y_mm

        self.update()
        self.cable_moved.emit(self._dragging.cable.key, self._dragging.x_mm, self._dragging.y_mm)

    @_check_types.do
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        dragged = self._dragging
        self._dragging = None

        if dragged is not None:
            self.cable_move_finished.emit(dragged.cable.key)
