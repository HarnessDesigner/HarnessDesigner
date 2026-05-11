# © 2025-2026 Kevin G. Schksloser <kevin.g.schlosser@gmail.com>

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from collections import OrderedDict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QScrollArea, QSizePolicy,
    QListWidget, QListWidgetItem, QFrame, QSpinBox, QDoubleSpinBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from . import dialog_base as _dialog_base


if TYPE_CHECKING:
    from ... import ui as _ui

RESOLUTION_SUFFIXES: Tuple[str, ...] = ("name", "symbol", "description")

FK_FILTER = "fk"
ENUM_FILTER = "enum"
RANGE_FILTER = "range"


class _MainTableInfo:

    def __init__(self, conn, table_name: str):
        self.table_name = table_name
        self.columns: "OrderedDict[str, str]" = OrderedDict()
        self.fk_target: Dict[str, str] = {}

        conn.execute(f'PRAGMA table_info("{table_name}")')
        rows = conn.fetchall()

        for row in rows:
            self.columns[row[1]] = (row[2] or "").upper()

        conn.execute(f'PRAGMA foreign_key_list("{table_name}")')
        rows = conn.fetchall()

        for row in rows:
            self.fk_target[row[3]] = row[2]

    @property
    def exists(self) -> bool:
        return bool(self.columns)

    def resolve_alias(self, alias: str) -> Optional[Tuple[str, Optional[str]]]:
        if alias == "id":
            return None

        if alias in self.columns:
            if alias in self.fk_target:
                return None
            return alias, None

        for suffix in RESOLUTION_SUFFIXES:
            if alias.endswith("_" + suffix):
                fk_col = alias[: -(len(suffix) + 1)] + "_id"
                if fk_col in self.columns:
                    return fk_col, suffix

        return None


PANEL_W = 200
PANEL_H = 260
DISABLED_COLOUR = QColor(160, 160, 160)


class _FilterPanelBase(QWidget):
    kind: str = ""

    def __init__(self, parent: QWidget, label: str, on_change):
        super().__init__(parent)
        self.label = label
        self.on_change = on_change
        self.setMinimumSize(PANEL_W, PANEL_H)
        self.setMaximumWidth(PANEL_W)
        self.setFrameShape = lambda *a: None  # compat stub

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def add_reset_button(self, layout):
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        button = QPushButton('Reset', self)
        button.clicked.connect(self._on_reset_button)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button)

        layout.addWidget(line)
        layout.addLayout(row)

    def _on_reset_button(self):
        self.clear()


class FKFilterPanel(_FilterPanelBase):
    kind = FK_FILTER

    def __init__(self, parent, column, ref_table, display_col, label, on_change):
        super().__init__(parent, label, on_change)
        self.column = column
        self.ref_table = ref_table
        self.display_col = display_col
        self._available: Optional[set] = None
        self._syncing = False

        lay = QVBoxLayout(self)
        title = QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        self.list = QListWidget(self)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        lay.addWidget(self.list, 1)

        self.add_reset_button(lay)

        self.list.itemChanged.connect(self._on_check)

    def populate(self, displays: List[str]) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for d in displays:
            item = QListWidgetItem(str(d))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def update_availability(self, available) -> None:
        if isinstance(available, list):
            available = set(available)
        self._available = available
        normal = self.palette().color(self.foregroundRole())

        for i in range(self.list.count()):
            item = self.list.item(i)
            ok = available is None or item.text() in available
            item.setForeground(normal if ok else DISABLED_COLOUR)

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        displays = [
            self.list.item(i).text()
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.Checked
        ]

        if not displays:
            return None

        placeholders = ",".join(["?"] * len(displays))
        sql = (f't.{self.column} IN ('
               f'SELECT id FROM {self.ref_table} '
               f'WHERE {self.display_col} IN ({placeholders}));')

        return sql, displays

    def clear(self) -> None:
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Unchecked)
        self.list.blockSignals(False)

    def _on_check(self, item):
        if self._syncing:
            return
        QTimer.singleShot(0, self._sync_and_notify)

    def _sync_and_notify(self):
        self._syncing = True
        try:
            if self._available is not None:
                for i in range(self.list.count()):
                    item = self.list.item(i)
                    if (item.checkState() == Qt.Checked and
                            item.text() not in self._available):
                        item.setCheckState(Qt.Unchecked)
        finally:
            self._syncing = False

        self.on_change(self)


class EnumFilterPanel(_FilterPanelBase):
    kind = ENUM_FILTER

    def __init__(self, parent, column, label, on_change):
        super().__init__(parent, label, on_change)
        self.column = column
        self._available: Optional[set] = None
        self._syncing = False

        lay = QVBoxLayout(self)
        title = QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        self.list = QListWidget(self)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        lay.addWidget(self.list, 1)

        self.add_reset_button(lay)

        self.list.itemChanged.connect(self._on_check)

    def populate(self, values: List[int]) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for v in values:
            item = QListWidgetItem(str(v))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def update_availability(self, available) -> None:
        if isinstance(available, list):
            available = set(available)
        self._available = available
        normal = self.palette().color(self.foregroundRole())

        for i in range(self.list.count()):
            item = self.list.item(i)
            try:
                v = int(item.text())
            except ValueError:
                continue
            ok = available is None or v in available
            item.setForeground(normal if ok else DISABLED_COLOUR)

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        vals: List[int] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                try:
                    vals.append(int(item.text()))
                except ValueError:
                    pass

        if not vals:
            return None

        placeholders = ",".join(["?"] * len(vals))
        return f't.{self.column} IN ({placeholders})', vals

    def clear(self) -> None:
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Unchecked)
        self.list.blockSignals(False)

    def _on_check(self, item):
        if self._syncing:
            return
        QTimer.singleShot(0, self._sync_and_notify)

    def _sync_and_notify(self):
        self._syncing = True
        try:
            if self._available is not None:
                for i in range(self.list.count()):
                    item = self.list.item(i)
                    if item.checkState() != Qt.Checked:
                        continue
                    try:
                        v = int(item.text())
                    except ValueError:
                        continue
                    if v not in self._available:
                        item.setCheckState(Qt.Unchecked)
        finally:
            self._syncing = False

        self.on_change(self)


class RangeFilterPanel(_FilterPanelBase):
    kind = RANGE_FILTER

    _INT_LIMIT = 2 ** 31 - 1
    _FLOAT_LIMIT = 1.0e15

    def __init__(self, parent, column, is_int, label, on_change):
        super().__init__(parent, label, on_change)
        self.column = column
        self.is_int = is_int
        self._lo_default: Optional[float] = None
        self._hi_default: Optional[float] = None
        self._initialised = False

        lay = QVBoxLayout(self)
        title = QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        from PySide6.QtWidgets import QFormLayout
        form = QFormLayout()

        if is_int:
            self.min_ctrl = QSpinBox(self)
            self.min_ctrl.setRange(-self._INT_LIMIT, self._INT_LIMIT)
            self.max_ctrl = QSpinBox(self)
            self.max_ctrl.setRange(-self._INT_LIMIT, self._INT_LIMIT)
        else:
            self.min_ctrl = QDoubleSpinBox(self)
            self.min_ctrl.setRange(-self._FLOAT_LIMIT, self._FLOAT_LIMIT)
            self.min_ctrl.setDecimals(4)
            self.max_ctrl = QDoubleSpinBox(self)
            self.max_ctrl.setRange(-self._FLOAT_LIMIT, self._FLOAT_LIMIT)
            self.max_ctrl.setDecimals(4)

        form.addRow('Min:', self.min_ctrl)
        form.addRow('Max:', self.max_ctrl)
        lay.addLayout(form)

        self.range_label = QLabel('(no data)', self)
        self.range_label.setStyleSheet('color: gray;')
        lay.addWidget(self.range_label)
        lay.addStretch()

        self.min_ctrl.valueChanged.connect(self._fire)
        self.max_ctrl.valueChanged.connect(self._fire)

    def _fire(self):
        QTimer.singleShot(0, lambda: self.on_change(self))

    @staticmethod
    def _good_increment(span: float) -> float:
        if span >= 1000:
            return 1.0
        if span >= 100:
            return 0.5
        if span >= 10:
            return 0.1
        if span >= 1:
            return 0.01
        return 0.001

    def update_bounds(self, lo, hi) -> None:
        if lo is None or hi is None:
            self.range_label.setText("(no data)")
            return

        if not self._initialised:
            self._initialised = True

            if self.is_int:
                lo_i, hi_i = int(lo), int(hi)
                self._lo_default, self._hi_default = lo_i, hi_i
                self.min_ctrl.setRange(lo_i, hi_i)
                self.max_ctrl.setRange(lo_i, hi_i)
                self.min_ctrl.setValue(lo_i)
                self.max_ctrl.setValue(hi_i)
            else:
                lo_f, hi_f = float(lo), float(hi)
                self._lo_default, self._hi_default = lo_f, hi_f
                inc = self._good_increment(hi_f - lo_f)
                self.min_ctrl.setSingleStep(inc)
                self.max_ctrl.setSingleStep(inc)
                self.min_ctrl.setRange(lo_f, hi_f)
                self.max_ctrl.setRange(lo_f, hi_f)
                self.min_ctrl.setValue(lo_f)
                self.max_ctrl.setValue(hi_f)

        self.range_label.setText(f"In data: {lo:g} - {hi:g}")

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        if not self._initialised:
            return None

        lo = self.min_ctrl.value()
        hi = self.max_ctrl.value()
        clauses, params = [], []

        if lo > self._lo_default:
            clauses.append(f't.{self.column} >= ?')
            params.append(lo)

        if hi < self._hi_default:
            clauses.append(f't.{self.column} <= ?')
            params.append(hi)

        if not clauses:
            return None

        return " AND ".join(clauses), params

    def clear(self) -> None:
        if self._initialised:
            self.min_ctrl.setValue(self._lo_default)
            self.max_ctrl.setValue(self._hi_default)


MAX_DISTINCT_FOR_ENUM = 200
MIN_DISTINCT_FOR_FILTER = 2


class SearchDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame", page_class, table, title: str):
        super().__init__(parent, title=title)

        self.table = table
        self.conn = parent.db_connector
        self.page_class = page_class
        self.mainframe = parent
        self.current_table: str = page_class.__table_name__
        self.filters: "OrderedDict[str, _FilterPanelBase]" = OrderedDict()

        self.info = _MainTableInfo(self.conn, self.current_table)

        if not self.info.exists:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Search error",
                f"Table {self.current_table!r} is not in the database."
            )
            return

        self._build_ui()
        self._build_filters_for(self.current_table)
        self._refresh_all()

        QTimer.singleShot(0, lambda: self.resize(1180, 780))

    def GetValue(self) -> Optional[int]:
        sel = getattr(self.results, "selected", None)

        if sel is None:
            return None

        try:
            return self.results.get_obj_id(sel)
        except Exception:
            return None

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        top = QHBoxLayout()
        st = QLabel("Keyword:", self)
        top.addWidget(st)

        self.kw_ctrl = QLineEdit(self)
        self.kw_ctrl.setPlaceholderText("Part # or description...")
        self.kw_ctrl.textChanged.connect(self._on_kw_changed)
        top.addWidget(self.kw_ctrl, 1)

        clear_btn = QPushButton("Clear All", self)
        clear_btn.clicked.connect(self._on_clear_all)
        top.addWidget(clear_btn)

        outer.addLayout(top)

        # Horizontally scrolling filter strip
        self.filter_scroll = QScrollArea(self)
        self.filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setFixedHeight(PANEL_H + 20)

        self._filter_container = QWidget()
        self.filter_sizer = QHBoxLayout(self._filter_container)
        self.filter_sizer.setAlignment(Qt.AlignLeft)
        self.filter_scroll.setWidget(self._filter_container)

        outer.addWidget(self.filter_scroll)

        bottom = QHBoxLayout()
        self.status = QLabel("0 results", self)
        bottom.addWidget(self.status)
        bottom.addStretch(1)
        outer.addLayout(bottom)

        self.results = self.page_class(self, self.mainframe, '', self.table)

        # Replace editor-mode list selection handlers with search-mode ones.
        # The page class connects these via standard Qt list signals.
        try:
            self.results.itemSelectionChanged.disconnect()
        except Exception:
            pass
        try:
            self.results.itemActivated.disconnect()
        except Exception:
            pass

        self.results.itemSelectionChanged.connect(self._on_selection_changed)
        self.results.itemActivated.connect(self._on_row_activated)

        outer.addWidget(self.results, 1)

    def _build_filters_for(self, table: str) -> None:
        for panel in self.filters.values():
            panel.deleteLater()

        self.filters.clear()

        # Remove all items from the layout
        while self.filter_sizer.count():
            item = self.filter_sizer.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cur = self.conn

        for idx in sorted(self.page_class.column_mapping.keys()):
            label, alias = self.page_class.column_mapping[idx]
            resolved = self.info.resolve_alias(alias)
            if resolved is None:
                continue

            col, disp_col = resolved

            if disp_col is not None:
                ref_table = self.info.fk_target.get(col)
                if not ref_table:
                    continue

                cur.execute(f'SELECT DISTINCT r.{disp_col} '
                            f'FROM {table} t '
                            f'JOIN {ref_table} r ON t.{col} = r.id '
                            f'WHERE r.{disp_col} IS NOT NULL '
                            f'ORDER BY r.{disp_col} COLLATE NOCASE;')

                rows = cur.fetchall()

                if len(rows) < MIN_DISTINCT_FOR_FILTER:
                    continue

                p = FKFilterPanel(self._filter_container, col, ref_table,
                                  disp_col, label, self._on_filter_changed)
                p.populate([r[0] for r in rows])
                panel = p

            else:
                col_type = self.info.columns.get(col, "")
                cur.execute(f'SELECT DISTINCT {col} FROM {table} '
                            f'WHERE {col} IS NOT NULL ORDER BY {col};')

                rows = cur.fetchall()

                values = [r[0] for r in rows]
                if len(values) < MIN_DISTINCT_FOR_FILTER:
                    continue

                is_int_type = "INT" in col_type
                is_real_type = any(t in col_type for t in
                                   ("REAL", "FLOA", "DOUB", "NUMERIC"))

                if not is_int_type and not is_real_type:
                    continue

                if is_int_type and len(values) <= MAX_DISTINCT_FOR_ENUM:
                    p = EnumFilterPanel(self._filter_container, col, label,
                                        self._on_filter_changed)
                    p.populate(values)
                    panel = p
                else:
                    cur.execute(f'SELECT MIN({col}), MAX({col}) '
                                f'FROM {table} WHERE {col} IS NOT NULL;')
                    rows = cur.fetchall()

                    lo, hi = (None, None) if not rows else rows[0]
                    if lo is None or hi is None or lo == hi:
                        continue

                    p = RangeFilterPanel(self._filter_container, col, is_int_type,
                                         label, self._on_filter_changed)
                    p.update_bounds(lo, hi)
                    panel = p

            self.filters[col] = panel
            self.filter_sizer.addWidget(panel)

    def _on_kw_changed(self) -> None:
        if hasattr(self, "_kw_timer"):
            self._kw_timer.stop()
        else:
            self._kw_timer = QTimer(self)
            self._kw_timer.setSingleShot(True)
            self._kw_timer.timeout.connect(self._refresh_all)

        self._kw_timer.start(180)

    def _on_filter_changed(self, _changed_panel) -> None:
        self._refresh_all()

    def _on_clear_all(self) -> None:
        self.kw_ctrl.blockSignals(True)
        self.kw_ctrl.clear()
        self.kw_ctrl.blockSignals(False)

        for p in self.filters.values():
            p.clear()

        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_filter_availability()
        self._push_filter_to_page()

    def _build_predicates(
        self,
        exclude: Optional[str] = None
    ) -> Tuple[List[str], List[Any]]:

        clauses, params = [], []
        kw = self.kw_ctrl.text().strip()

        if kw:
            cols = self.info.columns
            kw_clauses = []

            if "part_number" in cols:
                kw_clauses.append('t.part_number LIKE ?')
                params.append(f'%{kw.replace(" ", "%")}%')

            if "description" in cols:
                kw_clauses.append('t.description LIKE ?')
                params.append(f'%{kw.replace(" ", "%")}%')

            if kw_clauses:
                clauses.append("(" + " OR ".join(kw_clauses) + ")")

        for col, panel in self.filters.items():
            if col == exclude:
                continue

            pred = panel.get_predicate()
            if pred is None:
                continue

            sql, p = pred
            clauses.append(sql)
            params.extend(p)

        return clauses, params

    def _refresh_filter_availability(self) -> None:
        cur = self.conn
        table = self.current_table

        for col, panel in self.filters.items():
            clauses, params = self._build_predicates(exclude=col)

            if clauses:
                where = ("WHERE " + " AND ".join(clauses))
            else:
                where = ""

            if isinstance(panel, FKFilterPanel):
                if clauses:
                    where_extra = (" AND " + " AND ".join(clauses))
                else:
                    where_extra = ""

                sql = (f'SELECT DISTINCT r.{panel.display_col} '
                       f'FROM {table} t '
                       f'JOIN {panel.ref_table} r ON t.{col} = r.id '
                       f'WHERE r.{panel.display_col} IS NOT NULL '
                       f'{where_extra};')

                cur.execute(sql, params)
                rows = cur.fetchall()
                panel.update_availability([r[0] for r in rows if r[0] is not None])

            elif isinstance(panel, EnumFilterPanel):
                sql = (f'SELECT DISTINCT t.{col} '
                       f'FROM {table} t {where};')
                cur.execute(sql, params)
                rows = cur.fetchall()
                panel.update_availability([r[0] for r in rows if r[0] is not None])

            elif isinstance(panel, RangeFilterPanel):
                sql = (f'SELECT MIN(t.{col}), MAX(t.{col}) '
                       f'FROM {table} t {where};')
                cur.execute(sql, params)
                rows = cur.fetchall()
                lo, hi = (None, None) if not rows else rows[0]
                panel.update_bounds(lo, hi)

    def _push_filter_to_page(self) -> None:
        clauses, params = self._build_predicates()

        if clauses:
            where_clause = " AND ".join(clauses)
        else:
            where_clause = ""

        self.results.set_filter(where_clause, params)

        total = self.results.record_count
        self.status.setText(f"{total:,} result{'s' if total != 1 else ''}")

    def _on_selection_changed(self) -> None:
        sel = self.results.selectedItems()
        if sel:
            self.results.selected = self.results.row(sel[0])
        else:
            self.results.selected = None

    def _on_row_activated(self, item) -> None:
        self.results.selected = self.results.row(item)
        if self.GetValue() is not None:
            self.accept()
