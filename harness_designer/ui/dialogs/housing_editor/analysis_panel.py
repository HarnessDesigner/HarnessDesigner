# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import List, Optional

import numpy as np
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
from dataclasses import dataclass


@dataclass
class AnalysisItem:
    name: str
    kind: str        # 'circle' or 'rect'
    params: dict     # center, normal, u, v, plus radius / half_w, half_h
    d_start: float
    d_end: float
    verts: np.ndarray   # (3N, 3) float32 — triangle soup for the 3D overlay
    wire_surf_si: int = -1   # index into picker.surfaces for the matched wire surface
    term_surf_si: int = -1   # index into picker.surfaces for this terminal surface
    is_manual: bool = False  # True if hand-drawn on a single-plane housing
    # Full coplanar surface-index groups wire_surf_si/term_surf_si were
    # picked from (may cover several disconnected mesh islands on the same
    # plane). Persisted to Cavity.wire_surf_indices/terminal_surf_indices so
    # match_cavity_surfaces() can skip its OBB nearest-neighbor heuristic on
    # later loads. Empty for manual (synthetic-marker) cavities.
    wire_surf_indices: list = None
    term_surf_indices: list = None

    def __post_init__(self):
        if self.wire_surf_indices is None:
            self.wire_surf_indices = [self.wire_surf_si] if self.wire_surf_si >= 0 else []
        if self.term_surf_indices is None:
            self.term_surf_indices = [self.term_surf_si] if self.term_surf_si >= 0 else []

    @property
    def radius(self) -> float:
        return float(self.params.get('radius', 0.0))

    @property
    def half_w(self) -> float:
        return float(self.params.get('half_w', 0.0))

    @property
    def half_h(self) -> float:
        return float(self.params.get('half_h', 0.0))

    @property
    def length(self) -> float:
        return abs(float(self.d_end) - float(self.d_start))


_ROLE = QtCore.Qt.ItemDataRole.UserRole


class _ListWidget(QtWidgets.QListWidget):
    itemRemoveRequested: QtCore.SignalInstance = QtCore.Signal(int)   # row

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self._ctx_menu)

    def _ctx_menu(self, pos: QtCore.QPoint):
        item = self.itemAt(pos)
        if item is None:
            return
        row = self.row(item)
        menu = QtWidgets.QMenu(self)
        act = QtGui.QAction('Remove', self)
        act.triggered.connect(lambda: self.itemRemoveRequested.emit(row))
        menu.addAction(act)
        menu.exec(self.mapToGlobal(pos))


class _EditPanel(QtWidgets.QWidget):
    itemChanged: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: Optional[AnalysisItem] = None
        self._guard = False

        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(3)

        self._name = QtWidgets.QLineEdit()
        form.addRow('Name:', self._name)

        self._shape = QtWidgets.QComboBox()
        self._shape.addItems(['circle', 'rect'])
        form.addRow('Shape:', self._shape)

        def _dspin():
            s = QtWidgets.QDoubleSpinBox()
            s.setRange(0.001, 9999.0)
            s.setDecimals(3)
            s.setSingleStep(0.1)
            return s

        self._r_lbl = QtWidgets.QLabel('Radius:')
        self._r = _dspin()
        form.addRow(self._r_lbl, self._r)

        self._w_lbl = QtWidgets.QLabel('Half-Width:')
        self._w = _dspin()
        form.addRow(self._w_lbl, self._w)

        self._h_lbl = QtWidgets.QLabel('Half-Height:')
        self._h = _dspin()
        form.addRow(self._h_lbl, self._h)

        self._l = _dspin()
        form.addRow('Length:', self._l)

        self._name.editingFinished.connect(self._on_name)
        self._shape.currentIndexChanged.connect(self._on_shape)
        self._r.valueChanged.connect(self._on_r)
        self._w.valueChanged.connect(self._on_w)
        self._h.valueChanged.connect(self._on_h)
        self._l.valueChanged.connect(self._on_l)

        self.setEnabled(False)
        self._show_circle(True)

    def _show_circle(self, flag: bool):
        for w in (self._r_lbl, self._r):
            w.setVisible(flag)

        for w in (self._w_lbl, self._w, self._h_lbl, self._h):
            w.setVisible(not flag)

    def load(self, item: Optional[AnalysisItem]):
        self._item = item
        self.setEnabled(item is not None)
        if item is None:
            return

        self._guard = True

        try:
            self._name.setText(item.name)
            idx = self._shape.findText(item.kind)
            self._shape.setCurrentIndex(max(0, idx))
            self._show_circle(item.kind == 'circle')
            self._r.setValue(item.radius)
            self._w.setValue(item.half_w)
            self._h.setValue(item.half_h)
            self._l.setValue(item.length)
        finally:
            self._guard = False

    def _on_name(self):
        if self._guard or self._item is None:
            return

        self._item.name = self._name.text()
        self.itemChanged.emit()

    def _on_shape(self, _):
        if self._guard or self._item is None:
            return

        kind = self._shape.currentText()
        self._item.kind = kind
        self._show_circle(kind == 'circle')
        self.itemChanged.emit()

    def _on_r(self, v):
        if self._guard or self._item is None:
            return

        self._item.params['radius'] = v
        self.itemChanged.emit()

    def _on_w(self, v):
        if self._guard or self._item is None:
            return

        self._item.params['half_w'] = v
        self.itemChanged.emit()

    def _on_h(self, v):
        if self._guard or self._item is None:
            return

        self._item.params['half_h'] = v
        self.itemChanged.emit()

    def _on_l(self, v):
        if self._guard or self._item is None:
            return

        if self._item.d_end >= self._item.d_start:
            sign = 1.0
        else:
            sign = -1.0

        self._item.d_end = self._item.d_start + v * sign
        self.itemChanged.emit()


class AnalysisResultPanel(QtWidgets.QWidget):
    """Side panel for reviewing/editing detected cavities before committing."""

    accepted: QtCore.SignalInstance = QtCore.Signal()
    rejected: QtCore.SignalInstance = QtCore.Signal()
    # Emits row index of selected item, or -1 when nothing is selected
    selectionChanged: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)

        vl = QtWidgets.QVBoxLayout(self)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(4)

        hdr = QtWidgets.QLabel('Detected Cavities')
        font = hdr.font()
        font.setBold(True)
        hdr.setFont(font)
        vl.addWidget(hdr)

        self._list = _ListWidget(self)
        vl.addWidget(self._list, 2)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        vl.addWidget(sep)

        self._edit = _EditPanel(self)
        vl.addWidget(self._edit, 1)

        hl = QtWidgets.QHBoxLayout()
        self._ok_btn = QtWidgets.QPushButton('OK')
        self._cancel_btn = QtWidgets.QPushButton('Cancel')
        hl.addWidget(self._ok_btn)
        hl.addWidget(self._cancel_btn)
        vl.addLayout(hl)

        self._list.currentRowChanged.connect(self._on_row)
        self._list.itemRemoveRequested.connect(self._remove)
        self._list.model().rowsMoved.connect(self._on_reorder)  # NOQA
        self._edit.itemChanged.connect(self._refresh_current_label)
        self._ok_btn.clicked.connect(self.accepted)
        self._cancel_btn.clicked.connect(self.rejected)

        self.hide()

    # ── public ────────────────────────────────────────────────────────────────

    def load(self, items: List[AnalysisItem]):
        self._list.clear()
        self._edit.load(None)

        for i, item in enumerate(items):
            lw = QtWidgets.QListWidgetItem(self._label(i, item))
            lw.setData(_ROLE, item)
            self._list.addItem(lw)

        if self._list.count():
            self._list.setCurrentRow(0)
            self.show()
        else:
            self.hide()

    def items(self) -> List[AnalysisItem]:
        return [
            self._list.item(i).data(_ROLE)
            for i in range(self._list.count())]

    # ── internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _label(i: int, item: AnalysisItem) -> str:
        if item.kind == 'circle':
            dims = f'r={item.radius:.3f}'
        else:
            dims = f'{item.half_w * 2:.3f} × {item.half_h * 2:.3f}'
        return f'[{i + 1}]  {item.name} — {item.kind}  ({dims})'

    def _on_row(self, row: int):
        if 0 <= row < self._list.count():
            self._edit.load(self._list.item(row).data(_ROLE))
            self.selectionChanged.emit(row)
        else:
            self._edit.load(None)
            self.selectionChanged.emit(-1)

    def _remove(self, row: int):
        self._list.takeItem(row)
        self._refresh_all_labels()
        n = self._list.count()
        if n:
            self._list.setCurrentRow(min(row, n - 1))
        else:
            self._edit.load(None)
            self.selectionChanged.emit(-1)

    def _on_reorder(self, *_):
        self._refresh_all_labels()
        # selection_changed fires via currentRowChanged which Qt emits after move
        self.selectionChanged.emit(self._list.currentRow())

    def _refresh_current_label(self):
        row = self._list.currentRow()
        if 0 <= row < self._list.count():
            lw = self._list.item(row)
            lw.setText(self._label(row, lw.data(_ROLE)))

    def _refresh_all_labels(self):
        for i in range(self._list.count()):
            lw = self._list.item(i)
            lw.setText(self._label(i, lw.data(_ROLE)))
