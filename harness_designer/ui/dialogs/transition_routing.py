# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog for re-routing wires between transition output branches via drag-and-drop."""

import math
from typing import TYPE_CHECKING

from PySide6 import QtWidgets, QtCore, QtGui

from . import dialog_base as _dialog_base

if TYPE_CHECKING:
    from ...objects.objects3d import transition as _objects3d_transition


# ---------------------------------------------------------------------------
# Wire label helpers
# ---------------------------------------------------------------------------

def _color_name(color_obj) -> str:
    if color_obj is None:
        return 'None'
    return str(color_obj.name)


def _wire_label(conc_wire) -> str:
    pjt_wire = conc_wire.wire
    part = pjt_wire.part

    circuit = pjt_wire.circuit
    circuit_name = circuit.name if circuit is not None else '?'

    nc = part.num_conductors if part is not None else 1
    size_mm2 = part.size_mm2 if part is not None else 0.0
    size_awg = part.size_awg if part is not None else 0

    primary = _color_name(part.color if part is not None else None)
    stripe = _color_name(part.stripe_color if part is not None else None)

    label = f'{circuit_name}  ·  {nc}C  ·  {size_mm2:.2f}mm²({size_awg}AWG)  ·  {primary}/{stripe}'
    return label


def _effective_diameter(conc_wires, g_branch) -> float:
    total_area = 0.0
    for cw in conc_wires:
        od = cw.wire.part.od_mm if cw.wire.part else 0.0
        total_area += math.pi * (od / 2.0) ** 2
    if not conc_wires:
        return float(g_branch.min_dia)
    return max(2.0 * math.sqrt(total_area * 1.15 / math.pi), float(g_branch.min_dia))


# ---------------------------------------------------------------------------
# Custom QListWidget with drop-target tracking
# ---------------------------------------------------------------------------

_MIME_TYPE = 'application/x-transition-wire'


class _WireList(QtWidgets.QListWidget):
    """QListWidget that accepts wire drops from other branch lists in the same dialog."""

    wire_moved = QtCore.Signal(object, object, object)  # (conc_wire, src_list, dst_list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return
        mime = QtCore.QMimeData()
        mime.setData(_MIME_TYPE, b'1')
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.source() is not self and event.mimeData().hasFormat(_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.source() is not self and event.mimeData().hasFormat(_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        src = event.source()
        if src is self or not isinstance(src, _WireList):
            event.ignore()
            return
        item = src.currentItem()
        if item is None:
            event.ignore()
            return
        conc_wire = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if conc_wire is None:
            event.ignore()
            return

        event.acceptProposedAction()
        self.wire_moved.emit(conc_wire, src, self)


# ---------------------------------------------------------------------------
# Branch group box: title bar + capacity label + list
# ---------------------------------------------------------------------------

class _BranchGroup(QtWidgets.QGroupBox):

    def __init__(self, branch_idx: int, branch_db, g_branch, parent=None):
        label = f'Branch {branch_idx}'
        super().__init__(label, parent)
        self.branch_db = branch_db
        self.g_branch = g_branch

        inner = QtWidgets.QVBoxLayout(self)
        inner.setContentsMargins(4, 4, 4, 4)
        inner.setSpacing(4)

        self._cap_label = QtWidgets.QLabel(self)
        self._cap_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        inner.addWidget(self._cap_label)

        self.list_widget = _WireList(self)
        inner.addWidget(self.list_widget, 1)

        self._update_capacity_label()

    # ------------------------------------------------------------------

    def _conc_wires(self) -> list:
        try:
            conc = self.branch_db.concentric
        except (IndexError, KeyError):
            return []
        if conc is None:
            return []
        wires = []
        for layer in conc.layers:
            wires.extend(layer.wires)
        return wires

    def _update_capacity_label(self):
        cw = self._conc_wires()
        used = _effective_diameter(cw, self.g_branch)
        max_d = float(self.g_branch.max_dia)
        pct = min(100.0, used / max_d * 100.0) if max_d > 0 else 0.0
        self._cap_label.setText(
            f'{used:.2f} mm / {max_d:.2f} mm  ({pct:.0f}%)')
        if used > max_d:
            self._cap_label.setStyleSheet('color: #e84040;')
        else:
            self._cap_label.setStyleSheet('color: #40c040;')

    def rebuild_list(self):
        self.list_widget.clear()
        for cw in self._conc_wires():
            item = QtWidgets.QListWidgetItem(_wire_label(cw))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, cw)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.list_widget.addItem(item)
        self._update_capacity_label()


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class TransitionRoutingDialog(_dialog_base.BaseDialog):
    """Show one list per output branch; allow drag-and-drop wire reassignment."""

    def __init__(self, parent, transition_3d: "_objects3d_transition.Transition"):
        super().__init__(parent, 'Route Wires', size=(780, 520))
        self._transition_3d = transition_3d
        self._branch_groups: list[_BranchGroup] = []
        self._build_ui(transition_3d)

    def _build_ui(self, transition_3d: "_objects3d_transition.Transition"):
        transition_db = transition_3d.db_obj
        g_transition = transition_db.part
        g_branches = g_transition.branches  # list, index 0 = trunk (branch_id 1)

        branch_count = g_transition.branch_count

        scroll = QtWidgets.QScrollArea(self.panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(container)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(8)

        for branch_id in range(2, branch_count + 1):
            # g_branches is 0-indexed; branch_id 2 → index 1, etc.
            g_branch = g_branches[branch_id - 1]

            branch_db_attr = getattr(transition_db, f'branch{branch_id}', None)
            if branch_db_attr is None:
                continue

            grp = _BranchGroup(branch_id, branch_db_attr, g_branch, container)
            grp.list_widget.wire_moved.connect(self._on_wire_moved)
            grp.rebuild_list()
            row.addWidget(grp)
            self._branch_groups.append(grp)

        scroll.setWidget(container)

        panel_layout = QtWidgets.QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

    # ------------------------------------------------------------------

    def _on_wire_moved(self, conc_wire, src_list: _WireList, dst_list: _WireList):
        # Find destination branch group
        dst_grp = self._group_for_list(dst_list)
        if dst_grp is None:
            return

        # Get the single layer in the destination branch's concentric
        try:
            dst_conc = dst_grp.branch_db.concentric
        except (IndexError, KeyError):
            return
        if dst_conc is None:
            return
        dst_layers = dst_conc.layers
        if not dst_layers:
            return
        dst_layer = dst_layers[0]

        # Update layer counts
        src_layer = conc_wire.layer
        if src_layer is not None:
            new_src_count = max(0, src_layer.num_wires - 1)
            src_layer.num_wires = new_src_count

        conc_wire.layer_id = dst_layer.db_id
        dst_layer.num_wires = dst_layer.num_wires + 1

        # Recalculate branch diameters in DB
        src_grp = self._group_for_list(src_list)
        if src_grp is not None:
            src_wires = src_grp._conc_wires()
            new_src_dia = _effective_diameter(src_wires, src_grp.g_branch)
            src_grp.branch_db.diameter = new_src_dia
            if src_layer is not None:
                src_layer.diameter = new_src_dia

        dst_wires = dst_grp._conc_wires()
        new_dst_dia = _effective_diameter(dst_wires, dst_grp.g_branch)
        dst_grp.branch_db.diameter = new_dst_dia
        dst_layer.diameter = new_dst_dia

        # Update the 3D branch sphere diameters
        if src_grp is not None:
            self._update_branch_3d(src_grp, new_src_dia)
        self._update_branch_3d(dst_grp, new_dst_dia)

        # Refresh list widgets
        if src_grp is not None:
            src_grp.rebuild_list()
        dst_grp.rebuild_list()

    def _group_for_list(self, list_widget: _WireList) -> "_BranchGroup | None":
        for grp in self._branch_groups:
            if grp.list_widget is list_widget:
                return grp
        return None

    def _update_branch_3d(self, grp: _BranchGroup, new_diameter: float):
        branch_id = grp.branch_db.branch_id
        branches = self._transition_3d._branches
        if branch_id - 1 < len(branches):
            branch_3d = branches[branch_id - 1]
            branch_3d.diameter = new_diameter

    def GetValue(self):
        return None
