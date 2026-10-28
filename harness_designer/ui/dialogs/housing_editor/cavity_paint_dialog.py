# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
cavity_paint_dialog.py

A standalone 2-D "paint program" style dialog for manually laying out
cavity shapes (circles/rectangles) on a flattened projection of a housing
surface. Pure Qt widget-space math -- no 3-D/mesh dependencies at all; the
caller (housing_editor.py) is responsible for projecting the surface's
outline into local (x, y) millimetre coordinates before opening this
dialog, and for converting the accepted shapes back into world space
afterward.

Coordinate convention: (0, 0) is wherever the caller's projection puts it
(housing_editor.py anchors it at the surface's own plane, projected from
the world origin) -- this dialog only ever works in that local 2-D space.
"""

import math
from dataclasses import dataclass

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from .... import check_types as _check_types


# Shapes smaller than this (radius, or half_w/half_h) are discarded as an
# accidental click rather than a real draw.
_MIN_SIZE_MM = 0.5

_RULER_SIZE = 26
_TICK_CANDIDATES = (0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0,
                    25.0, 50.0, 100.0, 200.0, 250.0, 500.0, 1000.0)


@dataclass
class _PaintShape:
    kind: str   # 'circle' | 'rect'
    x: float = 0.0
    y: float = 0.0
    radius: float = 0.0
    half_w: float = 0.0
    half_h: float = 0.0

    @_check_types.do
    def bbox(self) -> tuple[float, float, float, float]:
        """(xmin, xmax, ymin, ymax)."""

        if self.kind == 'circle':
            r = self.radius
            return self.x - r, self.x + r, self.y - r, self.y + r

        return (self.x - self.half_w, self.x + self.half_w,
                self.y - self.half_h, self.y + self.half_h)

    @_check_types.do
    def extent(self) -> float:
        """The single value a drag-to-draw gesture is sizing."""

        if self.kind == 'circle':
            return self.radius

        return max(self.half_w, self.half_h)

    @_check_types.do
    def contains(self, x: float, y: float) -> bool:
        if self.kind == 'circle':
            return math.hypot(x - self.x, y - self.y) <= self.radius

        return abs(x - self.x) <= self.half_w and abs(y - self.y) <= self.half_h


@_check_types.do
def _bbox_overlap(a: tuple, b: tuple) -> bool:
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b

    return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)


@_check_types.do
def _merge_clusters(shapes: list[_PaintShape]) -> list[list[int]]:
    """Union-find over bounding-box overlap -- a cluster of 2+ overlapping
    shapes becomes one bounding-box cavity in :func:`result_shapes`; a
    cluster of 1 stays exactly the shape the user drew."""

    n = len(shapes)
    parent = list(range(n))

    @_check_types.do
    def find(i: int) -> int:
        while parent[i] != i:
            i = parent[i]
        return i

    @_check_types.do
    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    boxes = [s.bbox() for s in shapes]
    for i in range(n):
        for j in range(i + 1, n):
            if _bbox_overlap(boxes[i], boxes[j]):
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    return list(clusters.values())


@_check_types.do
def _nice_tick_interval(scale: float, min_px: float = 40.0) -> float:
    for c in _TICK_CANDIDATES:
        if c * scale >= min_px:
            return c

    return _TICK_CANDIDATES[-1]


class _PaintCanvas(QtWidgets.QWidget):
    """The paint surface itself: background outline, grid, rulers, shapes."""

    selectionChanged: QtCore.SignalInstance = QtCore.Signal(int)   # -1 = none
    shapesChanged: QtCore.SignalInstance = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, outline_loops: list, shapes: list[_PaintShape]):
        super().__init__(parent)
        self.setMinimumSize(420, 320)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # list[(N, 2) sequences of (x_mm, y_mm)] -- static for this dialog's
        # lifetime, the view's fit-to-outline framing is computed once from
        # these and never rescaled while drawing (rescaling under an active
        # drag would make dragging unusable).
        self._outline_loops = outline_loops

        # Shared with the owning dialog -- the dialog reads this same list
        # back out when the user accepts.
        self.shapes = shapes

        self.draw_kind: str | None = None   # 'circle' | 'rect' | None
        self.selected: int = -1

        self._drag_mode: str | None = None   # 'new' | 'move' | None
        self._drag_new: _PaintShape | None = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_orig: tuple[float, float] | None = None

        self._scale = 1.0
        self._view_xmin = -40.0
        self._view_ymax = 40.0
        self._off_x = float(_RULER_SIZE)
        self._off_y = float(_RULER_SIZE)

        self._rebuild_transform()

    # ── coordinate transform ─────────────────────────────────────────────────

    @_check_types.do
    def _rebuild_transform(self) -> None:
        avail_w = max(1, self.width() - _RULER_SIZE)
        avail_h = max(1, self.height() - _RULER_SIZE)

        xs: list[float] = []
        ys: list[float] = []
        for loop in self._outline_loops:
            for px, py in loop:
                xs.append(float(px))
                ys.append(float(py))

        if not xs:
            xmin, xmax, ymin, ymax = -40.0, 40.0, -40.0, 40.0
        else:
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)

            if xmax - xmin < 1e-6:
                xmin -= 10.0
                xmax += 10.0
            if ymax - ymin < 1e-6:
                ymin -= 10.0
                ymax += 10.0

            pad_x = (xmax - xmin) * 0.15 + 1.0
            pad_y = (ymax - ymin) * 0.15 + 1.0
            xmin -= pad_x
            xmax += pad_x
            ymin -= pad_y
            ymax += pad_y

        scale = min(avail_w / (xmax - xmin), avail_h / (ymax - ymin))
        used_w = (xmax - xmin) * scale
        used_h = (ymax - ymin) * scale

        self._scale = scale
        self._view_xmin = xmin
        self._view_ymax = ymax
        self._off_x = _RULER_SIZE + (avail_w - used_w) / 2.0
        self._off_y = _RULER_SIZE + (avail_h - used_h) / 2.0

    @_check_types.do
    def _mm_to_px(self, x: float, y: float) -> QtCore.QPointF:
        px = self._off_x + (x - self._view_xmin) * self._scale
        py = self._off_y + (self._view_ymax - y) * self._scale

        return QtCore.QPointF(px, py)

    @_check_types.do
    def _px_to_mm(self, px: float, py: float) -> tuple[float, float]:
        x = self._view_xmin + (px - self._off_x) / self._scale
        y = self._view_ymax - (py - self._off_y) / self._scale

        return x, y

    # ── hit testing ───────────────────────────────────────────────────────────

    @_check_types.do
    def _hit_test(self, x: float, y: float) -> int:
        for i in reversed(range(len(self.shapes))):
            if self.shapes[i].contains(x, y):
                return i

        return -1

    # ── public ────────────────────────────────────────────────────────────────

    @_check_types.do
    def set_draw_kind(self, kind: str | None) -> None:
        self.draw_kind = kind

    @_check_types.do
    def select(self, idx: int) -> None:
        self.selected = idx
        self.update()

    @_check_types.do
    def remove_selected(self) -> None:
        if not (0 <= self.selected < len(self.shapes)):
            return

        self.shapes.pop(self.selected)
        self.selected = -1
        self.selectionChanged.emit(-1)
        self.shapesChanged.emit()
        self.update()

    @_check_types.do
    def clear_all(self) -> None:
        self.shapes.clear()
        self.selected = -1
        self.selectionChanged.emit(-1)
        self.shapesChanged.emit()
        self.update()

    @_check_types.do
    def notify_shape_edited(self) -> None:
        self.shapesChanged.emit()
        self.update()

    # ── Qt events ─────────────────────────────────────────────────────────────

    @_check_types.do
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._rebuild_transform()
        super().resizeEvent(event)

    @_check_types.do
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        x, y = self._px_to_mm(pos.x(), pos.y())

        if self.draw_kind is not None:
            self._drag_new = _PaintShape(kind=self.draw_kind, x=x, y=y)
            self._drag_start = (x, y)
            self._drag_mode = 'new'
        else:
            idx = self._hit_test(x, y)
            if idx >= 0:
                self.selected = idx
                self._drag_start = (x, y)
                shape = self.shapes[idx]
                self._drag_orig = (shape.x, shape.y)
                self._drag_mode = 'move'
            else:
                self.selected = -1
                self._drag_mode = None

            self.selectionChanged.emit(self.selected)

        self.update()

    @_check_types.do
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_mode is None:
            return

        pos = event.position()
        x, y = self._px_to_mm(pos.x(), pos.y())

        if self._drag_mode == 'new':
            dx = x - self._drag_start[0]
            dy = y - self._drag_start[1]
            shape = self._drag_new

            if shape.kind == 'circle':
                shape.radius = math.hypot(dx, dy)
            else:
                shape.half_w = abs(dx)
                shape.half_h = abs(dy)

        elif self._drag_mode == 'move':
            dx = x - self._drag_start[0]
            dy = y - self._drag_start[1]
            shape = self.shapes[self.selected]
            shape.x = self._drag_orig[0] + dx
            shape.y = self._drag_orig[1] + dy

        self.update()

    @_check_types.do
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        changed = False

        if self._drag_mode == 'new':
            shape = self._drag_new
            if shape.extent() >= _MIN_SIZE_MM:
                self.shapes.append(shape)
                self.selected = len(self.shapes) - 1
                self.selectionChanged.emit(self.selected)
                changed = True

            self._drag_new = None

        elif self._drag_mode == 'move':
            changed = True

        self._drag_mode = None
        self._drag_start = None
        self._drag_orig = None

        if changed:
            self.shapesChanged.emit()

        self.update()

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.remove_selected()
        else:
            super().keyPressEvent(event)

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QtGui.QColor(235, 235, 235))

        tick = _nice_tick_interval(self._scale)
        self._draw_grid(painter, tick)
        self._draw_outline(painter)

        clusters = _merge_clusters(self.shapes)
        cluster_of: dict[int, list[int]] = {}
        for cluster in clusters:
            for i in cluster:
                cluster_of[i] = cluster

        for cluster in clusters:
            if len(cluster) > 1:
                self._draw_merge_box(painter, cluster)

        for i, shape in enumerate(self.shapes):
            self._draw_shape(painter, shape, selected=(i == self.selected))

        if self._drag_new is not None:
            self._draw_shape(painter, self._drag_new, selected=True, preview=True)

        self._draw_rulers(painter, tick)

        painter.end()

    # ── drawing helpers ───────────────────────────────────────────────────────

    @_check_types.do
    def _draw_grid(self, painter: QtGui.QPainter, tick: float) -> None:
        pen = QtGui.QPen(QtGui.QColor(210, 210, 210))
        pen.setWidth(1)
        painter.setPen(pen)

        x0, _ = self._px_to_mm(_RULER_SIZE, 0)
        x1, _ = self._px_to_mm(self.width(), 0)
        _, y1 = self._px_to_mm(0, _RULER_SIZE)
        _, y0 = self._px_to_mm(0, self.height())

        n0 = math.floor(x0 / tick)
        n1 = math.ceil(x1 / tick)
        for n in range(n0, n1 + 1):
            x = n * tick
            p = self._mm_to_px(x, 0)
            painter.drawLine(QtCore.QPointF(p.x(), _RULER_SIZE),
                              QtCore.QPointF(p.x(), self.height()))

        n0 = math.floor(y0 / tick)
        n1 = math.ceil(y1 / tick)
        for n in range(n0, n1 + 1):
            y = n * tick
            p = self._mm_to_px(0, y)
            painter.drawLine(QtCore.QPointF(_RULER_SIZE, p.y()),
                              QtCore.QPointF(self.width(), p.y()))

    @_check_types.do
    def _draw_outline(self, painter: QtGui.QPainter) -> None:
        if not self._outline_loops:
            return

        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.FillRule.OddEvenFill)

        for loop in self._outline_loops:
            if len(loop) < 3:
                continue

            poly = QtGui.QPolygonF(
                [self._mm_to_px(float(px), float(py)) for px, py in loop])
            path.addPolygon(poly)
            path.closeSubpath()

        painter.fillPath(path, QtGui.QBrush(QtGui.QColor(180, 210, 235)))
        painter.setPen(QtGui.QPen(QtGui.QColor(90, 130, 160), 2))
        painter.drawPath(path)

    @_check_types.do
    def _draw_shape(self, painter: QtGui.QPainter, shape: _PaintShape,
                    selected: bool, preview: bool = False) -> None:
        if preview:
            brush = QtGui.QColor(255, 80, 80, 140)
            pen = QtGui.QPen(QtGui.QColor(200, 30, 30), 2)
        elif selected:
            brush = QtGui.QColor(80, 220, 120, 170)
            pen = QtGui.QPen(QtGui.QColor(20, 140, 50), 2)
        else:
            brush = QtGui.QColor(60, 140, 220, 130)
            pen = QtGui.QPen(QtGui.QColor(30, 90, 160), 2)

        painter.setBrush(QtGui.QBrush(brush))
        painter.setPen(pen)

        if shape.kind == 'circle':
            c = self._mm_to_px(shape.x, shape.y)
            r = shape.radius * self._scale
            painter.drawEllipse(c, r, r)
        else:
            tl = self._mm_to_px(shape.x - shape.half_w, shape.y + shape.half_h)
            br = self._mm_to_px(shape.x + shape.half_w, shape.y - shape.half_h)
            painter.drawRect(QtCore.QRectF(tl, br))

    @_check_types.do
    def _draw_merge_box(self, painter: QtGui.QPainter, cluster: list) -> None:
        xmin = min(self.shapes[i].bbox()[0] for i in cluster)
        xmax = max(self.shapes[i].bbox()[1] for i in cluster)
        ymin = min(self.shapes[i].bbox()[2] for i in cluster)
        ymax = max(self.shapes[i].bbox()[3] for i in cluster)

        tl = self._mm_to_px(xmin, ymax)
        br = self._mm_to_px(xmax, ymin)

        pen = QtGui.QPen(QtGui.QColor(230, 140, 0))
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRect(QtCore.QRectF(tl, br))

    @_check_types.do
    def _draw_rulers(self, painter: QtGui.QPainter, tick: float) -> None:
        painter.fillRect(QtCore.QRectF(0, 0, self.width(), _RULER_SIZE),
                          QtGui.QColor(250, 250, 250))
        painter.fillRect(QtCore.QRectF(0, 0, _RULER_SIZE, self.height()),
                          QtGui.QColor(250, 250, 250))

        painter.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60)))

        x0, _ = self._px_to_mm(_RULER_SIZE, 0)
        x1, _ = self._px_to_mm(self.width(), 0)

        n0 = math.floor(x0 / tick)
        n1 = math.ceil(x1 / tick)
        for n in range(n0, n1 + 1):
            x = n * tick
            p = self._mm_to_px(x, 0)
            painter.drawLine(QtCore.QPointF(p.x(), _RULER_SIZE - 6),
                              QtCore.QPointF(p.x(), _RULER_SIZE))
            painter.drawText(QtCore.QRectF(p.x() - 20, 2, 40, _RULER_SIZE - 8),
                              QtCore.Qt.AlignmentFlag.AlignCenter, f'{x:g}')

        _, y1 = self._px_to_mm(0, _RULER_SIZE)
        _, y0 = self._px_to_mm(0, self.height())

        n0 = math.floor(y0 / tick)
        n1 = math.ceil(y1 / tick)
        for n in range(n0, n1 + 1):
            y = n * tick
            p = self._mm_to_px(0, y)
            painter.drawLine(QtCore.QPointF(_RULER_SIZE - 6, p.y()),
                              QtCore.QPointF(_RULER_SIZE, p.y()))

            painter.save()
            painter.translate(10, p.y())
            painter.rotate(-90)
            painter.drawText(QtCore.QRectF(-20, -10, 40, 20),
                              QtCore.Qt.AlignmentFlag.AlignCenter, f'{y:g}')
            painter.restore()

        painter.fillRect(QtCore.QRectF(0, 0, _RULER_SIZE, _RULER_SIZE),
                          QtGui.QColor(240, 240, 240))


class CavityPaintDialog(QtWidgets.QDialog):
    """2-D paint-style editor for manually laying out circle/rectangle
    cavities on a flattened surface outline.

    Overlapping shapes are automatically grouped and committed as a single
    bounding-box cavity (see :func:`_merge_clusters`) -- the side list and
    canvas still show/edit each drawn shape individually, the merge only
    happens when :meth:`result_shapes` is read.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, outline_loops: list,
                existing_shapes: list[dict]):
        super().__init__(parent)
        self.setWindowTitle('Draw Cavities on Surface')
        self.resize(760, 560)

        shapes = [
            _PaintShape(kind=s['kind'], x=s['x'], y=s['y'],
                        radius=s.get('radius', 0.0),
                        half_w=s.get('half_w', 0.0),
                        half_h=s.get('half_h', 0.0))
            for s in existing_shapes
        ]

        self._canvas = _PaintCanvas(self, outline_loops, shapes)
        self._canvas.selectionChanged.connect(self._on_selection_changed)
        self._canvas.shapesChanged.connect(self._on_shapes_changed)

        root = QtWidgets.QVBoxLayout(self)

        toolbar = QtWidgets.QHBoxLayout()
        self._btn_circle = QtWidgets.QPushButton('Circle', self)
        self._btn_rect = QtWidgets.QPushButton('Rectangle', self)
        for btn in (self._btn_circle, self._btn_rect):
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

        self._btn_circle.toggled.connect(self._on_tool_toggled)
        self._btn_rect.toggled.connect(self._on_tool_toggled)

        toolbar.addWidget(QtWidgets.QLabel('Draw:', self))
        toolbar.addWidget(self._btn_circle)
        toolbar.addWidget(self._btn_rect)
        toolbar.addStretch(1)

        self._info_label = QtWidgets.QLabel(
            'Pick a shape above, then click and drag on the surface to draw it.', self)
        root.addLayout(toolbar)
        root.addWidget(self._info_label)

        body = QtWidgets.QHBoxLayout()
        body.addWidget(self._canvas, 1)

        side = QtWidgets.QVBoxLayout()

        self._list = QtWidgets.QListWidget(self)
        self._list.currentRowChanged.connect(self._on_list_row_changed)
        side.addWidget(QtWidgets.QLabel('Drawn Shapes', self))
        side.addWidget(self._list, 1)

        list_btn_row = QtWidgets.QHBoxLayout()
        self._btn_remove = QtWidgets.QPushButton('Remove', self)
        self._btn_remove.setEnabled(False)
        self._btn_remove.clicked.connect(self._canvas.remove_selected)
        self._btn_remove_all = QtWidgets.QPushButton('Remove All', self)
        self._btn_remove_all.clicked.connect(self._canvas.clear_all)
        list_btn_row.addWidget(self._btn_remove)
        list_btn_row.addWidget(self._btn_remove_all)
        side.addLayout(list_btn_row)

        edit_group = QtWidgets.QGroupBox('Selected Shape', self)
        form = QtWidgets.QFormLayout(edit_group)

        self._x_spin = self._make_spin()
        self._y_spin = self._make_spin()
        self._radius_spin = self._make_spin(minimum=0.01)
        self._w_spin = self._make_spin(minimum=0.01)
        self._h_spin = self._make_spin(minimum=0.01)

        self._x_spin.valueChanged.connect(self._on_x_changed)
        self._y_spin.valueChanged.connect(self._on_y_changed)
        self._radius_spin.valueChanged.connect(self._on_radius_changed)
        self._w_spin.valueChanged.connect(self._on_w_changed)
        self._h_spin.valueChanged.connect(self._on_h_changed)

        form.addRow('X (mm):', self._x_spin)
        form.addRow('Y (mm):', self._y_spin)

        self._radius_label = QtWidgets.QLabel('Radius (mm):', edit_group)
        self._w_label = QtWidgets.QLabel('Width (mm):', edit_group)
        self._h_label = QtWidgets.QLabel('Height (mm):', edit_group)

        form.addRow(self._radius_label, self._radius_spin)
        form.addRow(self._w_label, self._w_spin)
        form.addRow(self._h_label, self._h_spin)

        edit_group.setEnabled(False)
        self._edit_group = edit_group
        side.addWidget(edit_group)
        side.addStretch(1)

        body.addLayout(side)
        root.addLayout(body, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._loading = False
        self._reload_list()

    @_check_types.do
    def _make_spin(self, minimum: float = -1000000.0) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox(self)
        spin.setRange(minimum, 1000000.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.1)

        return spin

    # ── toolbar ───────────────────────────────────────────────────────────────

    @_check_types.do
    def _on_tool_toggled(self, _checked: bool) -> None:
        if self._btn_circle.isChecked():
            self._canvas.set_draw_kind('circle')
            self._info_label.setText('Click and drag on the surface to draw a circle.')
        elif self._btn_rect.isChecked():
            self._canvas.set_draw_kind('rect')
            self._info_label.setText('Click and drag on the surface to draw a rectangle.')
        else:
            self._canvas.set_draw_kind(None)
            self._info_label.setText('Click a shape to select it, or pick a tool above to draw.')

    # ── shape list <-> canvas sync ───────────────────────────────────────────

    @_check_types.do
    def _reload_list(self) -> None:
        clusters = _merge_clusters(self._canvas.shapes)
        cluster_sizes = [1] * len(self._canvas.shapes)
        for cluster in clusters:
            for i in cluster:
                cluster_sizes[i] = len(cluster)

        self._list.blockSignals(True)
        self._list.clear()

        for i, shape in enumerate(self._canvas.shapes):
            label = self._shape_label(i, shape, cluster_sizes[i])
            self._list.addItem(label)

        if 0 <= self._canvas.selected < self._list.count():
            self._list.setCurrentRow(self._canvas.selected)
        else:
            self._list.setCurrentRow(-1)

        self._list.blockSignals(False)

    @staticmethod
    @_check_types.do
    def _shape_label(i: int, shape: _PaintShape, cluster_size: int) -> str:
        if shape.kind == 'circle':
            dims = f'r={shape.radius:.3f}'
            name = 'Circle'
        else:
            dims = f'{shape.half_w * 2:.3f} x {shape.half_h * 2:.3f}'
            name = 'Rectangle'

        label = f'{i + 1}: {name} — {dims}'
        if cluster_size > 1:
            label += '  (merged)'

        return label

    @_check_types.do
    def _on_shapes_changed(self) -> None:
        self._reload_list()
        self._load_selected_into_fields()

    @_check_types.do
    def _on_selection_changed(self, idx: int) -> None:
        if 0 <= idx < self._list.count():
            self._list.blockSignals(True)
            self._list.setCurrentRow(idx)
            self._list.blockSignals(False)
        else:
            self._list.blockSignals(True)
            self._list.setCurrentRow(-1)
            self._list.blockSignals(False)

        self._btn_remove.setEnabled(idx >= 0)
        self._load_selected_into_fields()

    @_check_types.do
    def _on_list_row_changed(self, row: int) -> None:
        self._canvas.select(row)
        self._btn_remove.setEnabled(row >= 0)
        self._load_selected_into_fields()

    # ── edit fields ───────────────────────────────────────────────────────────

    @_check_types.do
    def _load_selected_into_fields(self) -> None:
        idx = self._canvas.selected
        if not (0 <= idx < len(self._canvas.shapes)):
            self._edit_group.setEnabled(False)
            return

        shape = self._canvas.shapes[idx]
        self._edit_group.setEnabled(True)

        is_circle = shape.kind == 'circle'
        for w in (self._radius_label, self._radius_spin):
            w.setVisible(is_circle)
        for w in (self._w_label, self._w_spin, self._h_label, self._h_spin):
            w.setVisible(not is_circle)

        self._loading = True
        self._x_spin.setValue(shape.x)
        self._y_spin.setValue(shape.y)
        self._radius_spin.setValue(shape.radius)
        self._w_spin.setValue(shape.half_w * 2.0)
        self._h_spin.setValue(shape.half_h * 2.0)
        self._loading = False

    @_check_types.do
    def _selected_shape(self) -> _PaintShape | None:
        idx = self._canvas.selected
        if 0 <= idx < len(self._canvas.shapes):
            return self._canvas.shapes[idx]

        return None

    @_check_types.do
    def _on_x_changed(self, value: float) -> None:
        if self._loading:
            return

        shape = self._selected_shape()
        if shape is not None:
            shape.x = value
            self._canvas.notify_shape_edited()

    @_check_types.do
    def _on_y_changed(self, value: float) -> None:
        if self._loading:
            return

        shape = self._selected_shape()
        if shape is not None:
            shape.y = value
            self._canvas.notify_shape_edited()

    @_check_types.do
    def _on_radius_changed(self, value: float) -> None:
        if self._loading:
            return

        shape = self._selected_shape()
        if shape is not None and shape.kind == 'circle':
            shape.radius = value
            self._canvas.notify_shape_edited()

    @_check_types.do
    def _on_w_changed(self, value: float) -> None:
        if self._loading:
            return

        shape = self._selected_shape()
        if shape is not None and shape.kind == 'rect':
            shape.half_w = value / 2.0
            self._canvas.notify_shape_edited()

    @_check_types.do
    def _on_h_changed(self, value: float) -> None:
        if self._loading:
            return

        shape = self._selected_shape()
        if shape is not None and shape.kind == 'rect':
            shape.half_h = value / 2.0
            self._canvas.notify_shape_edited()

    # ── result ────────────────────────────────────────────────────────────────

    @_check_types.do
    def result_shapes(self) -> list[dict]:
        """Final, post-merge shapes: each a
        ``{'kind', 'x', 'y', 'radius', 'half_w', 'half_h'}`` dict in the same
        local 2-D millimetre space the dialog was opened with."""

        shapes = self._canvas.shapes
        results: list[dict] = []

        for cluster in _merge_clusters(shapes):
            if len(cluster) == 1:
                s = shapes[cluster[0]]
                results.append(dict(
                    kind=s.kind, x=s.x, y=s.y,
                    radius=s.radius, half_w=s.half_w, half_h=s.half_h))
                continue

            xmin = min(shapes[i].bbox()[0] for i in cluster)
            xmax = max(shapes[i].bbox()[1] for i in cluster)
            ymin = min(shapes[i].bbox()[2] for i in cluster)
            ymax = max(shapes[i].bbox()[3] for i in cluster)

            results.append(dict(
                kind='rect', x=(xmin + xmax) / 2.0, y=(ymin + ymax) / 2.0,
                radius=0.0, half_w=(xmax - xmin) / 2.0, half_h=(ymax - ymin) / 2.0))

        return results
