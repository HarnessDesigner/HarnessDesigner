# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""BOM Builder dialog: parts list, housing tree, wire cut sheet, and
bundle cut sheet, with live wire/bundle fabrication-excess controls."""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets, QtCore, QtGui

from . import dialog_base as _dialog_base
from ..widgets import choice_ctrl as _choice_ctrl
from ..widgets import float_ctrl as _float_ctrl
from ...objects import bom as _bom
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui


_HOUSING_KIND_LABELS = {
    'housing': 'Housing',
    'cpa_lock': 'CPA Lock',
    'cover': 'Cover',
    'boot': 'Boot',
    'seal': 'Seal',
    'tpa_lock_1': 'TPA Lock 1',
    'tpa_lock_2': 'TPA Lock 2',
    'terminal': 'Terminal/Plug',
}

_DEFAULT_EXCESS_PCT = 10.0


# ---------------------------------------------------------------------------
# Toolbar row
# ---------------------------------------------------------------------------

class _BomToolbarRow(QtWidgets.QWidget):
    """View switcher + wire/bundle excess-percentage controls, laid out in
    a single row -- a plain widget row rather than a real ``QToolBar``,
    since the movable/floatable chrome a real toolbar carries has no place
    inside a modal dialog."""

    viewChanged: QtCore.SignalInstance = QtCore.Signal(int)
    wireExcessChanged: QtCore.SignalInstance = QtCore.Signal(float)
    bundleExcessChanged: QtCore.SignalInstance = QtCore.Signal(float)

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)

        self.view_ctrl = _choice_ctrl.ChoiceCtrl(
            self, 'View:',
            ['Parts List', 'Housings', 'Wire Cut Sheet', 'Bundle Cut Sheet'])

        self.wire_excess_ctrl = _float_ctrl.FloatCtrl(
            self, 'Wire Excess %:', 0.0, 100.0, 0.5, slider=False)
        self.wire_excess_ctrl.SetValue(_DEFAULT_EXCESS_PCT)

        self.bundle_excess_ctrl = _float_ctrl.FloatCtrl(
            self, 'Bundle Excess %:', 0.0, 100.0, 0.5, slider=False)
        self.bundle_excess_ctrl.SetValue(_DEFAULT_EXCESS_PCT)

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.view_ctrl)
        row.addStretch(1)
        row.addWidget(self.wire_excess_ctrl)
        row.addWidget(self.bundle_excess_ctrl)

        self.view_ctrl.valueChanged.connect(self._on_view_changed)
        self.wire_excess_ctrl.value_changed.connect(self.wireExcessChanged.emit)
        self.bundle_excess_ctrl.value_changed.connect(self.bundleExcessChanged.emit)

    @_check_types.do
    def _on_view_changed(self, _text: str):
        self.viewChanged.emit(self.view_ctrl.GetSelection())


# ---------------------------------------------------------------------------
# View widgets
# ---------------------------------------------------------------------------

class _FlatListTree(QtWidgets.QTreeWidget):
    """View 1: flat parts list, one row per distinct part number."""

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setColumnCount(4)
        self.setHeaderLabels(['Manufacturer', 'Part Number', 'Description', 'Total Quantity'])
        self.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    @_check_types.do
    def load(self, rows: list["_bom.BomLineItem"]):
        self.clear()
        for row in rows:
            qty_text = f'{row.quantity:.1f} mm' if row.is_length else str(int(row.quantity))
            QtWidgets.QTreeWidgetItem(
                self, [row.manufacturer, row.part_number, row.description, qty_text])


class _HousingTree(QtWidgets.QTreeWidget):
    """View 2: one expandable tree per housing."""

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHeaderLabels(
            ['Type', 'Manufacturer', 'Part Number', 'Description', 'AWG Min', 'AWG Max'])
        self.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    @_check_types.do
    def _add_node(self, parent, node: "_bom.HousingTreeNode", bold: bool):
        awg_min = '' if node.awg_min is None else str(node.awg_min)
        awg_max = '' if node.awg_max is None else str(node.awg_max)
        label = _HOUSING_KIND_LABELS.get(node.kind, node.kind)

        item = QtWidgets.QTreeWidgetItem(
            parent, [label, node.manufacturer, node.part_number,
                     node.description, awg_min, awg_max])

        if bold:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)

        for child in node.children:
            self._add_node(item, child, bold=False)

        return item

    @_check_types.do
    def load(self, nodes: list["_bom.HousingTreeNode"]):
        self.clear()
        for node in nodes:
            item = self._add_node(self, node, bold=True)
            item.setExpanded(True)


class _WireCutSheetTree(QtWidgets.QTreeWidget):
    """View 3: one row per physical wire instance."""

    _COLOR_COLUMN = 7

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setColumnCount(10)
        self.setHeaderLabels([
            'Manufacturer', 'Part Number', 'Description', 'AWG', 'mm²',
            'Conductors', 'Shielded', 'Color', 'Exact Length (mm)',
            'Length w/ Excess (mm)'])
        self.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    @_check_types.do
    def load(self, rows: list["_bom.WireCutRow"]):
        self.clear()
        for row in rows:
            item = QtWidgets.QTreeWidgetItem(self, [
                row.manufacturer, row.part_number, row.description,
                str(row.awg), f'{row.mm2:.4f}', str(row.num_conductors),
                'Yes' if row.shielded else 'No', '',
                f'{row.exact_length_mm:.1f}', f'{row.length_with_excess_mm:.1f}'])

            item.setIcon(self._COLOR_COLUMN, QtGui.QIcon(row.icon.pixmap))


class _BundleCutSheetTree(QtWidgets.QTreeWidget):
    """View 4: one row per bundle-covering instance."""

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setColumnCount(7)
        self.setHeaderLabels([
            'Manufacturer', 'Part Number', 'Description', 'Diameter Min (mm)',
            'Diameter Max (mm)', 'Exact Length (mm)', 'Length w/ Excess (mm)'])
        self.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    @_check_types.do
    def load(self, rows: list["_bom.BundleCutRow"]):
        self.clear()
        for row in rows:
            QtWidgets.QTreeWidgetItem(self, [
                row.manufacturer, row.part_number, row.description,
                f'{row.dia_min_mm:.2f}', f'{row.dia_max_mm:.2f}',
                f'{row.exact_length_mm:.1f}', f'{row.length_with_excess_mm:.1f}'])


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class BomDialog(_dialog_base.BaseDialog):
    """Read-only BOM Builder: parts list, housing tree, wire cut sheet, and
    bundle cut sheet views, with live Wire Excess % / Bundle Excess %
    controls. Print is a no-op stub; OK just closes the dialog -- nothing
    here is persisted."""

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame"):
        super().__init__(
            parent, 'Bill of Materials', size=(960, 640),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        self._wire_excess_pct = _DEFAULT_EXCESS_PCT
        self._bundle_excess_pct = _DEFAULT_EXCESS_PCT

        self._toolbar_row = _BomToolbarRow(self.panel)

        self._stack = QtWidgets.QStackedWidget(self.panel)
        self._flat_view = _FlatListTree(self._stack)
        self._housing_view = _HousingTree(self._stack)
        self._wire_view = _WireCutSheetTree(self._stack)
        self._bundle_view = _BundleCutSheetTree(self._stack)

        for view in (self._flat_view, self._housing_view,
                     self._wire_view, self._bundle_view):
            self._stack.addWidget(view)

        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.addWidget(self._toolbar_row)
        layout.addWidget(self._stack, 1)

        self._toolbar_row.viewChanged.connect(self._stack.setCurrentIndex)
        self._toolbar_row.wireExcessChanged.connect(self._on_wire_excess_changed)
        self._toolbar_row.bundleExcessChanged.connect(self._on_bundle_excess_changed)

        self._print_btn = self.button_box.addButton(
            'Print', QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        self._print_btn.clicked.connect(self._on_print)

        self._reload_all()

    @_check_types.do
    def _project(self):
        return self.mainframe.project

    @_check_types.do
    def _reload_all(self):
        project = self._project()
        if project is None:
            for view in (self._flat_view, self._housing_view,
                         self._wire_view, self._bundle_view):
                view.clear()
            return

        self._flat_view.load(_bom.build_flat_list(
            project, self._wire_excess_pct, self._bundle_excess_pct))
        self._housing_view.load(_bom.build_housing_tree(project))
        self._wire_view.load(_bom.build_wire_cut_sheet(project, self._wire_excess_pct))
        self._bundle_view.load(_bom.build_bundle_cut_sheet(project, self._bundle_excess_pct))

    @_check_types.do
    def _on_wire_excess_changed(self, pct: float):
        self._wire_excess_pct = pct
        project = self._project()
        if project is None:
            return

        self._flat_view.load(_bom.build_flat_list(
            project, self._wire_excess_pct, self._bundle_excess_pct))
        self._wire_view.load(_bom.build_wire_cut_sheet(project, pct))

    @_check_types.do
    def _on_bundle_excess_changed(self, pct: float):
        self._bundle_excess_pct = pct
        project = self._project()
        if project is None:
            return

        self._flat_view.load(_bom.build_flat_list(
            project, self._wire_excess_pct, self._bundle_excess_pct))
        self._bundle_view.load(_bom.build_bundle_cut_sheet(project, pct))

    @_check_types.do
    def _on_print(self, checked: bool = False):
        pass

    @_check_types.do
    def GetValue(self):
        return None
