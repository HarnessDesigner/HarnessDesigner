# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Optional

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import analysis_panel as _analysis_panel
from .... import check_types as _check_types


# Relative tolerance for the "group by size" tree view: two surfaces with
# the same triangle count are bucketed together when their areas are within
# this fraction of the bucket's reference (first/smallest) member.
_SIZE_GROUP_AREA_TOL = 0.05


@_check_types.do
def _compute_size_buckets(
    surf_idxs: list[int], surfaces: list, areas: dict[int, float],
) -> list[list[int]]:
    """
    Group surface indices into size buckets: a surface joins a bucket only
    when its triangle count exactly matches the bucket's reference member
    AND its area is within ``_SIZE_GROUP_AREA_TOL`` of that member's area.

    Sorting by (tri_count, area) first makes every same-tri-count run
    contiguous with non-decreasing area, so a simple forward scan against
    each bucket's first (smallest-area) member is sufficient.
    """

    ordered = sorted(
        surf_idxs, key=lambda si: (len(surfaces[si].tri_indices), areas[si]))

    buckets: list[list[int]] = []

    for si in ordered:
        n_tris = len(surfaces[si].tri_indices)
        area = areas[si]

        if buckets:
            ref_si = buckets[-1][0]
            ref_tris = len(surfaces[ref_si].tri_indices)
            ref_area = areas[ref_si]

            if (n_tris == ref_tris and
                    abs(area - ref_area) <= _SIZE_GROUP_AREA_TOL * max(ref_area, 1e-9)):
                buckets[-1].append(si)
                continue

        buckets.append([si])

    return buckets


@_check_types.do
def _make_caption_label(parent: QtWidgets.QWidget, text: str) -> QtWidgets.QLabel:
    """Sunken, horizontally-gradiented (light blue -> black) caption strip."""

    label = QtWidgets.QLabel(text, parent)
    label.setFrameShape(QtWidgets.QFrame.Shape.Panel)
    label.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    label.setLineWidth(2)
    label.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet(
        'QLabel {'
        '  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,'
        '    stop:0 #6fa8dc, stop:1 #000000);'
        '  color: #10263d;'
        '  font-weight: bold;'
        '  padding: 1px 8px;'
        # A stylesheet targeting this widget's own background/border takes
        # over ALL of its box-model rendering, so the native
        # setFrameShadow(Sunken) bevel above never actually shows through --
        # border-style: inset is what actually produces a sunken look once
        # a stylesheet is in play.
        '  border-style: inset;'
        '  border-width: 2px;'
        '  border-color: #303030;'
        '}')

    return label


class _TreeControlBase(QtWidgets.QWidget):
    """
    Shared shell for a bottom-panel tree control: a gradient caption, a
    toolbar row (subclass-populated), a sunken multi-select tree with
    Delete-key removal and arrow-key navigation (native to Qt's
    ``ExtendedSelection`` mode -- no extra code needed), auto-reselect of
    the next item after a removal, and a small info label.

    Subclasses implement:
      - ``_build_toolbar()``: populate/return the toolbar widget, placing
        ``self._btn_remove`` wherever they want it.
      - ``_flatten_item(item)``: tree item -> the domain-specific integer
        indices it represents (a leaf is one index; a group/bucket node is
        every index it contains).
      - ``_perform_removal(units)``: actually remove those units and
        refresh the tree.
    """

    selectionChanged: QtCore.SignalInstance = QtCore.Signal(list)
    removeRequested: QtCore.SignalInstance = QtCore.Signal(list)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, caption: str):
        super().__init__(parent)

        self._pending_reselect_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        layout.addWidget(_make_caption_label(self, caption))

        self._btn_remove = QtWidgets.QPushButton('Remove', self)
        self._btn_remove.setEnabled(False)
        self._btn_remove.clicked.connect(self._on_remove)

        layout.addWidget(self._build_toolbar())

        self._tree = QtWidgets.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setFrameShape(QtWidgets.QFrame.Shape.Panel)
        self._tree.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self._tree.setLineWidth(2)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._tree, 1)

        self._info_label = QtWidgets.QLabel('', self)
        self._info_label.setWordWrap(True)
        self._info_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        # Reserve room for 2 lines up front, rather than sizing to whatever
        # the current text needs -- otherwise a message that happens to
        # wrap to a 2nd line grows this label and, since the tree above it
        # is the only stretchable item in this layout, steals that height
        # back from the tree even though there was already room to spare.
        info_metrics = self._info_label.fontMetrics()
        self._info_label.setMinimumHeight(2 * info_metrics.lineSpacing() + 16)
        layout.addWidget(self._info_label)

        shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Delete), self._tree)
        shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetShortcut)
        shortcut.activated.connect(self._on_remove)

    # ── subclass hooks ───────────────────────────────────────────────────────

    @_check_types.do
    def _build_toolbar(self) -> QtWidgets.QWidget:
        raise NotImplementedError

    @_check_types.do
    def _flatten_item(self, item: QtWidgets.QTreeWidgetItem) -> list:
        raise NotImplementedError

    @_check_types.do
    def _perform_removal(self, units: list) -> None:
        raise NotImplementedError

    # ── shared selection / remove / reselect mechanics ──────────────────────

    @_check_types.do
    def _flattened_items(self) -> list:
        items: list[QtWidgets.QTreeWidgetItem] = []

        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            items.append(top)

            for c in range(top.childCount()):
                items.append(top.child(c))

        return items

    @_check_types.do
    def _selected_units(self) -> list:
        result: list[int] = []
        seen: set[int] = set()

        for item in self._tree.selectedItems():
            for unit in self._flatten_item(item):
                if unit not in seen:
                    seen.add(unit)
                    result.append(unit)

        return result

    @_check_types.do
    def _on_selection_changed(self) -> None:
        units = self._selected_units()
        self._btn_remove.setEnabled(bool(units))
        self.selectionChanged.emit(units)

    @_check_types.do
    def has_selection(self) -> bool:
        return bool(self._tree.selectedItems())

    @_check_types.do
    def clear_tree_selection(self) -> None:
        self._tree.clearSelection()

    @_check_types.do
    def _on_remove(self) -> None:
        units = self._selected_units()
        if not units:
            return

        flat = self._flattened_items()
        selected = set(self._tree.selectedItems())
        positions = [i for i, it in enumerate(flat) if it in selected]
        self._pending_reselect_index = min(positions) if positions else None

        self._perform_removal(units)

    @_check_types.do
    def _restore_selection_after_rebuild(self) -> None:
        if self._pending_reselect_index is None:
            return

        flat = self._flattened_items()
        if flat:
            idx = min(self._pending_reselect_index, len(flat) - 1)
            flat[idx].setSelected(True)
            self._tree.setCurrentItem(flat[idx])

        self._pending_reselect_index = None

    @_check_types.do
    def set_info(self, text: str) -> None:
        self._info_label.setText(text)


class PlaneTreePanel(_TreeControlBase):
    """Wire-side or terminal-side surface tree (one fixed side per instance).

    "Group by Plane" -- top-level (bold) nodes are one plane group per
    coplanar click, labelled "Plane N - X surfaces", each expanding to its
    individual surfaces ("Surface M - Y tris").

    "Group by Size" -- ignores plane grouping entirely: top-level (bold)
    nodes are buckets of surfaces sharing the same triangle count and a
    close (within tolerance) area, labelled "Size N - X surfaces (...)",
    each expanding to its individual member surfaces.

    Selection follows standard Qt extended-selection rules: click selects
    only that item, ctrl+click toggles one item in/out of the selection,
    shift+click range-selects. Remove removes every surface covered by the
    current selection (a selected group/bucket node covers every surface it
    contains), regardless of which node(s) it came from.
    """

    addManualRequested: QtCore.SignalInstance = QtCore.Signal(int, str)
    # Plane-group indices whose "select holes instead of the surface" state
    # should be toggled (terminal side only).
    invertHolesRequested: QtCore.SignalInstance = QtCore.Signal(list)
    removeAllRequested: QtCore.SignalInstance = QtCore.Signal()
    clearTerminalsRequested: QtCore.SignalInstance = QtCore.Signal()
    addTerminalToggled: QtCore.SignalInstance = QtCore.Signal(bool)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, is_terminal: bool, caption: str):
        self._is_terminal = is_terminal
        self._view_mode: str = 'plane'  # 'plane' | 'size'

        # Cached from the last load() call, so switching view modes can
        # rebuild the tree locally without asking the dialog again.
        self._groups: list[list[int]] = []
        self._surfaces: list = []
        self._areas: dict[int, float] = {}
        # group index -> number of holes selected in place of that plane's
        # surface(s); a group appears here only while it is inverted.
        self._group_holes: dict[int, int] = {}

        # Populated by _build_toolbar(); terminal-only widgets stay None on
        # the wire instance.
        self._btn_by_plane: Optional[QtWidgets.QPushButton] = None
        self._btn_by_size: Optional[QtWidgets.QPushButton] = None
        self._btn_remove_all: Optional[QtWidgets.QPushButton] = None
        self._btn_add_circle: Optional[QtWidgets.QPushButton] = None
        self._btn_add_rect: Optional[QtWidgets.QPushButton] = None
        self._btn_terminal: Optional[QtWidgets.QPushButton] = None
        self._btn_clear_terminals: Optional[QtWidgets.QPushButton] = None

        super().__init__(parent, caption)

        self._tree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_ctx_menu)

    # ── toolbar ───────────────────────────────────────────────────────────────

    @_check_types.do
    def _build_toolbar(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        outer = QtWidgets.QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        row1 = QtWidgets.QHBoxLayout()
        self._btn_by_plane = QtWidgets.QPushButton('By Plane', container)
        self._btn_by_size = QtWidgets.QPushButton('By Size', container)

        for btn in (self._btn_by_plane, self._btn_by_size):
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

        self._btn_by_plane.setChecked(True)
        self._btn_by_plane.toggled.connect(self._on_view_mode_toggled)
        self._btn_by_size.toggled.connect(self._on_view_mode_toggled)

        row1.addWidget(self._btn_by_plane)
        row1.addWidget(self._btn_by_size)
        row1.addStretch(1)
        row1.addWidget(self._btn_remove)

        if self._is_terminal:
            # "Remove All" here clears every terminal plane, individual
            # terminal, and manual cavity draw -- kept under the same
            # attribute/signal name (clearTerminalsRequested) as before,
            # just relabeled and moved up next to Remove for parity with
            # the wire panel's own Remove All.
            self._btn_clear_terminals = QtWidgets.QPushButton('Remove All', container)
            self._btn_clear_terminals.clicked.connect(self.clearTerminalsRequested)
            row1.addWidget(self._btn_clear_terminals)
        else:
            self._btn_remove_all = QtWidgets.QPushButton('Remove All', container)
            self._btn_remove_all.clicked.connect(self.removeAllRequested)
            row1.addWidget(self._btn_remove_all)

        outer.addLayout(row1)

        if self._is_terminal:
            row2 = QtWidgets.QHBoxLayout()

            self._btn_add_circle = QtWidgets.QPushButton('Add Circle', container)
            self._btn_add_rect = QtWidgets.QPushButton('Add Rectangle', container)
            self._btn_terminal = QtWidgets.QPushButton('Add Terminal', container)

            self._btn_add_circle.setEnabled(False)
            self._btn_add_rect.setEnabled(False)
            self._btn_terminal.setCheckable(True)

            self._btn_add_circle.clicked.connect(
                lambda: self._emit_add_manual('circle'))
            self._btn_add_rect.clicked.connect(
                lambda: self._emit_add_manual('rect'))
            self._btn_terminal.toggled.connect(self.addTerminalToggled)

            row2.addWidget(self._btn_add_circle)
            row2.addWidget(self._btn_add_rect)
            row2.addWidget(self._btn_terminal)
            row2.addStretch(1)
            outer.addLayout(row2)

        return container

    @_check_types.do
    def set_add_terminal_checked(self, flag: bool) -> None:
        """Programmatic uncheck from the dialog's mode-button coordination --
        blocked so it doesn't re-emit addTerminalToggled."""

        if self._btn_terminal is None:
            return

        self._btn_terminal.blockSignals(True)
        self._btn_terminal.setChecked(flag)
        self._btn_terminal.blockSignals(False)

    @_check_types.do
    def _emit_add_manual(self, kind: str) -> None:
        g = self._single_selected_plane_group()
        if g is not None:
            self.addManualRequested.emit(g, kind)

    @_check_types.do
    def _single_selected_plane_group(self) -> Optional[int]:
        """The lone selected top-level plane_group node's index, in Plane
        view, or None -- used both for the Add Circle/Rectangle toolbar
        buttons' enabled state and their click handlers."""

        if self._view_mode != 'plane':
            return None

        items = self._tree.selectedItems()
        if len(items) != 1:
            return None

        kind, payload = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
        if kind != 'plane_group':
            return None

        return payload

    # ── load / rebuild ───────────────────────────────────────────────────────

    @_check_types.do
    def load(
        self,
        groups: list[list[int]],
        surfaces: list,
        areas: dict[int, float],
        group_holes: dict[int, int] | None = None,
    ) -> None:
        """
        Rebuild the tree from plane groups.

        groups[g] is the list of surface indices for plane group g.
        surfaces is the full picker surface list (for triangle-count labels).
        areas maps every surface index appearing in groups to its computed
        world-space area (used by the "Group by Size" view).
        group_holes maps the index of each inverted plane group to the
        number of holes selected in place of its surface(s).
        """

        self._groups = groups
        self._surfaces = surfaces
        self._areas = areas

        if group_holes is None:
            self._group_holes = {}
        else:
            self._group_holes = dict(group_holes)

        self._rebuild_tree()
        self._restore_selection_after_rebuild()
        self._on_selection_changed()

    @_check_types.do
    def _rebuild_tree(self) -> None:
        self._tree.clear()

        if not self._groups:
            self._add_placeholder()
            return

        if self._view_mode == 'size':
            self._build_size_tree()
        else:
            self._build_plane_tree()

    @_check_types.do
    def _add_placeholder(self) -> None:
        item = QtWidgets.QTreeWidgetItem(self._tree, ['Click me to add surfaces.'])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, ('placeholder', None))

        font = item.font(0)
        font.setItalic(True)
        item.setFont(0, font)

    @_check_types.do
    def select_last_top_level(self) -> None:
        """Keep this tree "active" (something selected) right after a 3D-
        canvas pick adds/removes a plane, since select_mode is derived from
        tree selection now -- without this, the reload's fresh (unselected)
        tree would immediately drop back out of pick mode after one click."""

        n = self._tree.topLevelItemCount()
        if n:
            item = self._tree.topLevelItem(n - 1)
            item.setSelected(True)
            self._tree.setCurrentItem(item)

    @_check_types.do
    def select_groups(self, group_idxs: list[int]) -> None:
        """Re-select the given plane groups' top-level nodes (Plane view) --
        used after a rebuild that would otherwise drop the selection."""

        if self._view_mode != 'plane':
            return

        for g in group_idxs:
            if 0 <= g < self._tree.topLevelItemCount():
                item = self._tree.topLevelItem(g)
                item.setSelected(True)
                self._tree.setCurrentItem(item)

    @_check_types.do
    def _build_plane_tree(self) -> None:
        for g, group in enumerate(self._groups):
            n = len(group)

            label = f'Plane {g + 1}  —  {n} surface{"s" if n != 1 else ""}'

            if g in self._group_holes:
                n_holes = self._group_holes[g]
                label += f'  —  {n_holes} hole{"s" if n_holes != 1 else ""} selected'

            parent_item = QtWidgets.QTreeWidgetItem(self._tree, [label])

            parent_item.setData(
                0, QtCore.Qt.ItemDataRole.UserRole, ('plane_group', g))

            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)

            for s, si in enumerate(group):
                n_tris = len(self._surfaces[si].tri_indices)

                if self._is_terminal:
                    area = self._areas.get(si, 0.0)
                    label = (f'  Surface {s + 1}  —  {n_tris}'
                             f' tri{"s" if n_tris != 1 else ""}, area ≈ {area:.3g}')
                else:
                    label = (f'  Surface {s + 1}  —  {n_tris}'
                             f' tri{"s" if n_tris != 1 else ""}')

                child = QtWidgets.QTreeWidgetItem(parent_item, [label])

                child.setData(
                    0, QtCore.Qt.ItemDataRole.UserRole, ('surface', si))

            parent_item.setExpanded(True)

    @_check_types.do
    def _build_size_tree(self) -> None:
        all_idxs = [si for group in self._groups for si in group]
        buckets = _compute_size_buckets(all_idxs, self._surfaces, self._areas)

        for b, bucket in enumerate(buckets):
            n = len(bucket)
            n_tris = len(self._surfaces[bucket[0]].tri_indices)
            area = self._areas[bucket[0]]

            parent_item = QtWidgets.QTreeWidgetItem(
                self._tree,
                [f'Size {b + 1}  —  {n} surface{"s" if n != 1 else ""}'
                 f'  ({n_tris} tri{"s" if n_tris != 1 else ""}, area ≈ {area:.3g})'])

            parent_item.setData(
                0, QtCore.Qt.ItemDataRole.UserRole, ('size_bucket', list(bucket)))

            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)

            for s, si in enumerate(bucket):
                child = QtWidgets.QTreeWidgetItem(
                    parent_item, [f'  Surface {s + 1}'])

                child.setData(
                    0, QtCore.Qt.ItemDataRole.UserRole, ('surface', si))

            parent_item.setExpanded(True)

    # ── base-class hooks ─────────────────────────────────────────────────────

    @_check_types.do
    def _flatten_item(self, item: QtWidgets.QTreeWidgetItem) -> list:
        kind, payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if kind == 'surface':
            return [payload]
        if kind == 'plane_group':
            return list(self._groups[payload])
        if kind == 'size_bucket':
            return list(payload)

        return []

    @_check_types.do
    def _perform_removal(self, units: list) -> None:
        self.removeRequested.emit(units)

    # ── misc handlers ────────────────────────────────────────────────────────

    @_check_types.do
    def _on_view_mode_toggled(self, _checked: bool) -> None:
        if self._btn_by_size is not None and self._btn_by_size.isChecked():
            self._view_mode = 'size'
        else:
            self._view_mode = 'plane'

        self._rebuild_tree()
        self._on_selection_changed()

    @_check_types.do
    def _on_selection_changed(self) -> None:
        super()._on_selection_changed()
        self._update_add_shape_enabled()

    @_check_types.do
    def _update_add_shape_enabled(self) -> None:
        if self._btn_add_circle is None:
            return

        enabled = self._single_selected_plane_group() is not None
        self._btn_add_circle.setEnabled(enabled)
        self._btn_add_rect.setEnabled(enabled)

    @_check_types.do
    def _selected_plane_groups(self) -> list[int]:
        """Indices of every selected top-level plane_group node."""

        result: list[int] = []

        for item in self._tree.selectedItems():
            kind, payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if kind == 'plane_group':
                result.append(payload)

        return sorted(result)

    @_check_types.do
    def _on_ctx_menu(self, pos: QtCore.QPoint) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return

        # Right-clicking an item outside the current selection replaces the
        # selection with just that item; right-clicking within an existing
        # multi-selection leaves it intact so "Remove" acts on all of it.
        if item not in self._tree.selectedItems():
            self._tree.clearSelection()
            item.setSelected(True)
            self._tree.setCurrentItem(item)

        kind, payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        menu = QtWidgets.QMenu(self._tree)
        act = menu.addAction('Remove')
        act.triggered.connect(self._on_remove)

        if (self._is_terminal and self._view_mode == 'plane' and
                kind == 'plane_group'):
            menu.addSeparator()
            act = menu.addAction('Add Circle Cavity')
            act.triggered.connect(
                lambda: self.addManualRequested.emit(payload, 'circle'))

            act = menu.addAction('Add Rectangle Cavity')
            act.triggered.connect(
                lambda: self.addManualRequested.emit(payload, 'rect'))

        if self._is_terminal and self._view_mode == 'plane':
            group_idxs = self._selected_plane_groups()

            if group_idxs:
                menu.addSeparator()

                if all(g in self._group_holes for g in group_idxs):
                    act = menu.addAction('Select Surface (Undo Hole Selection)')
                else:
                    act = menu.addAction('Select Holes Instead of Surface')

                act.triggered.connect(
                    lambda: self.invertHolesRequested.emit(group_idxs))

        menu.exec(self._tree.mapToGlobal(pos))


class CavityTreePanel(_TreeControlBase):
    """Flat tree of pending (not-yet-committed) detected cavities, one leaf
    row per :class:`~.analysis_panel.AnalysisItem`. No Plane/Size grouping
    -- there's nothing to group a handful of finished cavities by."""

    removeAllRequested: QtCore.SignalInstance = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, caption: str):
        self._items: list[_analysis_panel.AnalysisItem] = []

        super().__init__(parent, caption)

    # ── toolbar ───────────────────────────────────────────────────────────────

    @_check_types.do
    def _build_toolbar(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        btn_remove_all = QtWidgets.QPushButton('Remove All', container)
        btn_remove_all.clicked.connect(self.removeAllRequested)

        row.addStretch(1)
        row.addWidget(self._btn_remove)
        row.addWidget(btn_remove_all)

        return container

    # ── public ────────────────────────────────────────────────────────────────

    @_check_types.do
    def load(self, items: list[_analysis_panel.AnalysisItem]) -> None:
        self._items = list(items)
        self._pending_reselect_index = None
        self._rebuild_tree()

        if self._items:
            first = self._tree.topLevelItem(0)
            first.setSelected(True)
            self._tree.setCurrentItem(first)

        self._on_selection_changed()

    @_check_types.do
    def items(self) -> list[_analysis_panel.AnalysisItem]:
        return list(self._items)

    # ── rebuild ───────────────────────────────────────────────────────────────

    @staticmethod
    @_check_types.do
    def _label(i: int, item: _analysis_panel.AnalysisItem) -> str:
        if item.kind == 'circle':
            dims = f'r={item.radius:.3f}'
        else:
            dims = f'{item.half_w * 2:.3f} × {item.half_h * 2:.3f}'

        return f'[{i + 1}]  {item.name} — {item.kind}  ({dims})'

    @_check_types.do
    def _rebuild_tree(self) -> None:
        self._tree.clear()

        for i, item in enumerate(self._items):
            row = QtWidgets.QTreeWidgetItem(self._tree, [self._label(i, item)])
            row.setData(0, QtCore.Qt.ItemDataRole.UserRole, ('item', i))

    @_check_types.do
    def refresh_labels(self) -> None:
        """Call after in-place edits to an item (e.g. from the edit form)."""

        for i in range(self._tree.topLevelItemCount()):
            row = self._tree.topLevelItem(i)
            row.setText(0, self._label(i, self._items[i]))

    # ── base-class hooks ─────────────────────────────────────────────────────

    @_check_types.do
    def _flatten_item(self, item: QtWidgets.QTreeWidgetItem) -> list:
        _kind, payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return [payload]

    @_check_types.do
    def _perform_removal(self, units: list) -> None:
        for i in sorted(set(units), reverse=True):
            if 0 <= i < len(self._items):
                self._items.pop(i)

        self._rebuild_tree()
        self._restore_selection_after_rebuild()
        self._on_selection_changed()
