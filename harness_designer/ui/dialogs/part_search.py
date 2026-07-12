# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from collections import OrderedDict
import sqlite3

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import dialog_base as _dialog_base
from ... import logger as _logger


if TYPE_CHECKING:
    from ... import ui as _ui

RESOLUTION_SUFFIXES: Tuple[str, ...] = ("name", "symbol", "description")

FK_FILTER = "fk"
ENUM_FILTER = "enum"
RANGE_FILTER = "range"


class _QueryWorker(QtCore.QObject):
    """Run SQL on a dedicated worker thread against its own SQLite connection.

    ``parent.db_connector`` is a single shared connection with a single
    shared cursor used throughout the app; handing that same cursor to a
    second thread would corrupt its state the moment anything else touched
    it concurrently. SQLite has no problem with multiple independent
    connections to the same file used concurrently for reads, so this
    worker opens its own connection (from within its own thread, once the
    thread's event loop has started) and never touches the shared one.
    """

    resultReady = QtCore.Signal(int, object, object)  # request_id, rows, error

    def __init__(self, db_path: str):
        """Initialise the :class:`_QueryWorker` instance.

        :param db_path: Filesystem path to the SQLite database file.
        :type db_path: str
        """
        super().__init__()
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @QtCore.Slot()
    def open(self) -> None:
        """Open this worker's own connection. Must run on the worker thread."""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)

    @QtCore.Slot(int, str, list)
    def run_query(self, request_id: int, sql: str, params: list) -> None:
        """Execute one query and report the result back to the main thread.

        :param request_id: Token used by the caller to match this result
            back to the request that triggered it.
        :type request_id: int
        :param sql: SQL statement to execute.
        :type sql: str
        :param params: Bound parameters for ``sql``.
        :type params: list
        """
        try:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        except Exception as err:  # NOQA
            self.resultReady.emit(request_id, None, err)
            return

        self.resultReady.emit(request_id, rows, None)

    def request_stop(self) -> None:
        """Abort any in-flight query so the worker thread can exit promptly.

        Called directly from the main thread (not via a signal), so unlike
        every other method here it must NOT touch ``self._conn`` in a way
        that isn't documented as cross-thread safe.
        ``sqlite3.Connection.interrupt`` specifically is safe to call from
        a different thread than the one running the query -- it's the
        sqlite3 module's designated way to cancel a long-running statement
        from outside. Without this, closing the dialog while a slow
        housings query is mid-flight would leave the worker thread stuck
        running it, and :meth:`QThread.wait` in :meth:`SearchDialog.done`
        would block the main thread for the query's full duration -- the
        exact freeze this worker thread exists to avoid.
        """
        if self._conn is not None:
            self._conn.interrupt()


class _MainTableInfo:
    """Represent a main table info in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, conn, table_name: str):
        """Initialise the :class:`_MainTableInfo` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param conn: Value for ``conn``.
        :type conn: UNKNOWN
        :param table_name: Value for ``table_name``.
        :type table_name: str
        """
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
        """Return the exists.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self.columns)

    def resolve_alias(self, alias: str) -> Optional[Tuple[str, Optional[str]]]:
        """Execute the resolve alias operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param alias: Value for ``alias``.
        :type alias: str
        :returns: Return value. UNKNOWN details.
        :rtype: Optional[Tuple[str, Optional[str]]]
        """
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
DISABLED_COLOUR = QtGui.QColor(160, 160, 160)


class _FilterPanelBase(QtWidgets.QWidget):
    """Represent a filter panel base in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    kind: str = ""

    def __init__(self, parent: QtWidgets.QWidget, label: str, on_change):
        """Initialise the :class:`_FilterPanelBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        :param label: Value for ``label``.
        :type label: str
        :param on_change: Value for ``on_change``.
        :type on_change: UNKNOWN
        """
        super().__init__(parent)
        self.label = label
        self.on_change = on_change
        self.setMinimumSize(PANEL_W, PANEL_H)
        self.setMaximumWidth(PANEL_W)
        self.setFrameShape = lambda *a: None  # compat stub

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        """Return the predicate.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: Optional[Tuple[str, List[Any]]]
        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def clear(self) -> None:
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def add_reset_button(self, layout):
        """Add a reset button.

        UNKNOWN details are inferred from the callable name and signature.

        :param layout: Value for ``layout``.
        :type layout: UNKNOWN
        """
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        button = QtWidgets.QPushButton('Reset', self)
        button.clicked.connect(self._on_reset_button)

        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        row.addWidget(button)

        layout.addWidget(line)
        layout.addLayout(row)

    def _on_reset_button(self):
        """Handle the reset button event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.clear()


class FKFilterPanel(_FilterPanelBase):
    """Represent a fk filter panel in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    kind = FK_FILTER

    def __init__(self, parent, column, ref_table,
                 display_col, label, on_change):
        """Initialise the :class:`FKFilterPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param column: Value for ``column``.
        :type column: UNKNOWN
        :param ref_table: Value for ``ref_table``.
        :type ref_table: UNKNOWN
        :param display_col: Value for ``display_col``.
        :type display_col: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param on_change: Value for ``on_change``.
        :type on_change: UNKNOWN
        """

        super().__init__(parent, label, on_change)
        self.column = column
        self.ref_table = ref_table
        self.display_col = display_col
        self._available: Optional[set] = None
        self._syncing = False

        lay = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        self.list = QtWidgets.QListWidget(self)
        self.list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        lay.addWidget(self.list, 1)

        self.add_reset_button(lay)

        self.list.itemChanged.connect(self._on_check)

    def populate(self, displays: List[str]) -> None:
        """Execute the populate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param displays: Value for ``displays``.
        :type displays: List[str]
        """
        self.list.blockSignals(True)
        self.list.clear()
        for d in displays:
            item = QtWidgets.QListWidgetItem(str(d))
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def update_availability(self, available) -> None:
        """Update the availability.

        UNKNOWN details are inferred from the callable name and signature.

        :param available: Value for ``available``.
        :type available: UNKNOWN
        """
        if isinstance(available, list):
            available = set(available)

        self._available = available
        normal = self.palette().color(self.foregroundRole())

        for i in range(self.list.count()):
            item = self.list.item(i)
            ok = available is None or item.text() in available
            item.setForeground(normal if ok else DISABLED_COLOUR)

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        """Return the predicate.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: Optional[Tuple[str, List[Any]]]
        """
        displays = [
            self.list.item(i).text()
            for i in range(self.list.count())
            if self.list.item(i).checkState() == QtCore.Qt.CheckState.Checked
        ]

        if not displays:
            return None

        placeholders = ",".join(["?"] * len(displays))
        sql = (f't.{self.column} IN ('
               f'SELECT id FROM {self.ref_table} '
               f'WHERE {self.display_col} IN ({placeholders}))')

        return sql, displays

    def clear(self) -> None:
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.list.blockSignals(False)

    def _on_check(self, _):
        """Handle the check event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        if self._syncing:
            return

        QtCore.QTimer.singleShot(0, self._sync_and_notify)

    def _sync_and_notify(self):
        """Execute the sync and notify operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._syncing = True
        try:
            if self._available is not None:
                for i in range(self.list.count()):
                    item = self.list.item(i)
                    if (
                        item.checkState() == QtCore.Qt.CheckState.Checked and
                        item.text() not in self._available
                    ):
                        item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        finally:
            self._syncing = False

        self.on_change(self)


class EnumFilterPanel(_FilterPanelBase):
    """Represent an enum filter panel in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    kind = ENUM_FILTER

    def __init__(self, parent, column, label, on_change):
        """Initialise the :class:`EnumFilterPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param column: Value for ``column``.
        :type column: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param on_change: Value for ``on_change``.
        :type on_change: UNKNOWN
        """
        super().__init__(parent, label, on_change)
        self.column = column
        self._available: Optional[set] = None
        self._syncing = False

        lay = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        self.list = QtWidgets.QListWidget(self)
        self.list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        lay.addWidget(self.list, 1)

        self.add_reset_button(lay)

        self.list.itemChanged.connect(self._on_check)

    def populate(self, values: List[int]) -> None:
        """Execute the populate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param values: Values to store or process.
        :type values: List[int]
        """
        self.list.blockSignals(True)
        self.list.clear()

        for v in values:
            item = QtWidgets.QListWidgetItem(str(v))
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.list.addItem(item)

        self.list.blockSignals(False)

    def update_availability(self, available) -> None:
        """Update the availability.

        UNKNOWN details are inferred from the callable name and signature.

        :param available: Value for ``available``.
        :type available: UNKNOWN
        """
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
        """Return the predicate.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: Optional[Tuple[str, List[Any]]]
        """
        vals: List[int] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                try:
                    vals.append(int(item.text()))
                except ValueError:
                    pass

        if not vals:
            return None

        placeholders = ",".join(["?"] * len(vals))
        return f't.{self.column} IN ({placeholders})', vals

    def clear(self) -> None:
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.list.blockSignals(False)

    def _on_check(self, _):
        """Handle the check event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        if self._syncing:
            return

        QtCore.QTimer.singleShot(0, self._sync_and_notify)

    def _sync_and_notify(self):
        """Execute the sync and notify operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._syncing = True
        try:
            if self._available is not None:
                for i in range(self.list.count()):
                    item = self.list.item(i)
                    if item.checkState() != QtCore.Qt.CheckState.Checked:
                        continue
                    try:
                        v = int(item.text())
                    except ValueError:
                        continue
                    if v not in self._available:
                        item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        finally:
            self._syncing = False

        self.on_change(self)


class RangeFilterPanel(_FilterPanelBase):
    """Represent a range filter panel in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    kind = RANGE_FILTER

    _INT_LIMIT = 2 ** 31 - 1
    _FLOAT_LIMIT = 1.0e15

    def __init__(self, parent, column, is_int, label, on_change):
        """Initialise the :class:`RangeFilterPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param column: Value for ``column``.
        :type column: UNKNOWN
        :param is_int: Boolean flag for whether int.
        :type is_int: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param on_change: Value for ``on_change``.
        :type on_change: UNKNOWN
        """
        super().__init__(parent, label, on_change)
        self.column = column
        self.is_int = is_int
        self._lo_default: Optional[float] = None
        self._hi_default: Optional[float] = None
        self._initialised = False

        lay = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel(f'<b>{label}</b>', self)
        lay.addWidget(title)

        from PySide6.QtWidgets import QFormLayout
        form = QFormLayout()

        if is_int:
            self.min_ctrl = QtWidgets.QSpinBox(self)
            self.min_ctrl.setRange(-self._INT_LIMIT, self._INT_LIMIT)
            self.max_ctrl = QtWidgets.QSpinBox(self)
            self.max_ctrl.setRange(-self._INT_LIMIT, self._INT_LIMIT)
        else:
            self.min_ctrl = QtWidgets.QDoubleSpinBox(self)
            self.min_ctrl.setRange(-self._FLOAT_LIMIT, self._FLOAT_LIMIT)
            self.min_ctrl.setDecimals(4)
            self.max_ctrl = QtWidgets.QDoubleSpinBox(self)
            self.max_ctrl.setRange(-self._FLOAT_LIMIT, self._FLOAT_LIMIT)
            self.max_ctrl.setDecimals(4)

        form.addRow('Min:', self.min_ctrl)
        form.addRow('Max:', self.max_ctrl)
        lay.addLayout(form)

        self.range_label = QtWidgets.QLabel('(no data)', self)
        self.range_label.setStyleSheet('color: gray;')
        lay.addWidget(self.range_label)
        lay.addStretch()

        self.min_ctrl.valueChanged.connect(self._fire)
        self.max_ctrl.valueChanged.connect(self._fire)

    def _fire(self):
        """Execute the fire operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        QtCore.QTimer.singleShot(0, lambda: self.on_change(self))

    @staticmethod
    def _good_increment(span: float) -> float:
        """Execute the good increment operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param span: Value for ``span``.
        :type span: float
        :returns: Return value. UNKNOWN details.
        :rtype: float
        """
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
        """Update the bounds.

        UNKNOWN details are inferred from the callable name and signature.

        :param lo: Value for ``lo``.
        :type lo: UNKNOWN
        :param hi: Value for ``hi``.
        :type hi: UNKNOWN
        """
        if lo is None or hi is None:
            self.range_label.setText("(no data)")
            return

        if not self._initialised:
            self._initialised = True

            # setValue() emits valueChanged for real (unlike FKFilterPanel/
            # EnumFilterPanel's populate(), which block signals around their
            # initial state). Left unblocked, every RangeFilterPanel built
            # during the chunked filter-build loop fires two spurious
            # "filter changed" events mid-construction, each kicking off a
            # full _refresh_all() pass against a still-partially-built
            # self.filters -- a storm of redundant queries that looks like
            # a hang and has nothing to do with anything the user did.
            self.min_ctrl.blockSignals(True)
            self.max_ctrl.blockSignals(True)
            try:
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
            finally:
                self.min_ctrl.blockSignals(False)
                self.max_ctrl.blockSignals(False)

        self.range_label.setText(f"In data: {lo:g} - {hi:g}")

    def get_predicate(self) -> Optional[Tuple[str, List[Any]]]:
        """Return the predicate.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: Optional[Tuple[str, List[Any]]]
        """
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
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._initialised:
            self.min_ctrl.setValue(self._lo_default)
            self.max_ctrl.setValue(self._hi_default)


MAX_DISTINCT_FOR_ENUM = 200
MIN_DISTINCT_FOR_FILTER = 2


class SearchDialog(_dialog_base.BaseDialog):
    """Represent a search dialog in :mod:`harness_designer.ui.dialogs.part_search`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # Cross-thread request signal. Connecting this to the worker's
    # ``run_query`` slot and emitting it from the main thread is the normal
    # Qt way to hand work to another thread -- Qt detects the receiver
    # lives on a different thread and auto-delivers the call as a queued
    # (thread-safe) event instead of calling it directly.
    _queryRequested = QtCore.Signal(int, str, list)

    def __init__(self, parent: "_ui.MainFrame", page_class, table, title: str, initial_results=None):
        """Initialise the :class:`SearchDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param page_class: Value for ``page_class``.
        :type page_class: UNKNOWN
        :param table: Value for ``table``.
        :type table: UNKNOWN
        :param title: Value for ``title``.
        :type title: str
        :param initial_results: Part numbers shown as the default result set
            while no keyword or filters are active (e.g. parts compatible
            with the part being attached to).
        :type initial_results: list[str]
        """
        super().__init__(parent, title=title, size=(1180, 780))

        self.table = table
        self.initial_results: List[str] = list(initial_results or [])
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

        # Filter-building/refresh queries (the ones that can run long
        # against a large catalog table) are dispatched to a worker thread
        # with its own SQLite connection, so a slow query blocks that
        # thread instead of this one -- the dialog's own event loop keeps
        # pumping, so Windows never flags it as "Not Responding", and a
        # busy cursor + progress bar (see :meth:`_begin_query`) tell the
        # user something is actually happening.
        self._next_request_id = 0
        self._pending_queries: Dict[int, Callable[[list], None]] = {}
        self._inflight_count = 0
        self._busy_cursor_active = False

        self._query_thread = QtCore.QThread(self)
        self._query_worker = _QueryWorker(self.conn.db_name)
        self._query_worker.moveToThread(self._query_thread)
        self._query_thread.started.connect(self._query_worker.open)  # NOQA
        self._queryRequested.connect(self._query_worker.run_query)  # NOQA
        self._query_worker.resultReady.connect(self._on_query_result)
        self._query_thread.start()

        # Build the empty structure (keyword field, filter strip, results
        # table) at the dialog's final size first, so the window appears
        # immediately.  The filter/result queries run right after, once the
        # event loop actually starts processing (i.e. once the dialog is
        # already visible), instead of blocking the dialog from showing at
        # all until every query finishes.
        self._build_ui()
        QtCore.QTimer.singleShot(0, self._populate)

    def done(self, result: int) -> None:
        """Shut down the query worker thread before the dialog closes.

        Overriding :meth:`QDialog.done` (rather than ``accept``/``reject``
        individually) catches every way the dialog can close, since both
        funnel through it.

        :param result: The dialog result code being finished with.
        :type result: int
        """
        if hasattr(self, '_query_thread'):
            # Interrupt first: if a slow housings query is still running on
            # the worker thread, quit()+wait() alone would block this
            # (main) thread until that query finishes on its own --
            # exactly the freeze the worker thread exists to avoid.
            self._query_worker.request_stop()
            self._query_thread.quit()
            self._query_thread.wait()

        super().done(result)

    # ------------------------------------------------------------------
    # Async query plumbing
    # ------------------------------------------------------------------

    def _run_query_async(self, sql: str, params: list,
                         callback: Callable[[list], None]) -> None:
        """Submit a query to the worker thread; ``callback`` runs on the
        main thread once the result arrives.

        :param sql: SQL statement to execute.
        :type sql: str
        :param params: Bound parameters for ``sql``.
        :type params: list
        :param callback: Called with the fetched rows (``[]`` on error).
        :type callback: Callable[[list], None]
        """
        self._next_request_id += 1
        request_id = self._next_request_id
        self._pending_queries[request_id] = callback
        self._begin_query()
        self._queryRequested.emit(request_id, sql, list(params))

    def _on_query_result(self, request_id: int, rows, error) -> None:
        """Handle a result delivered back from the worker thread.

        :param request_id: Token matching the originating request.
        :type request_id: int
        :param rows: Fetched rows, or ``None`` on error.
        :type rows: list | None
        :param error: The exception raised in the worker, if any.
        :type error: Exception | None
        """
        callback = self._pending_queries.pop(request_id, None)
        self._end_query()

        if callback is None:
            return

        if error is not None:
            _logger.error('Search dialog query failed:', error)
            callback([])
            return

        callback(rows)

    def _begin_query(self) -> None:
        """Mark one more query as in flight, entering the busy state on
        the 0-to-1 transition.
        """
        self._inflight_count += 1

        if self._inflight_count == 1 and not self._busy_cursor_active:
            self._busy_cursor_active = True
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.WaitCursor)
            self.progress.setVisible(True)

    def _end_query(self) -> None:
        """Mark one in-flight query as finished, leaving the busy state on
        the 1-to-0 transition.
        """
        self._inflight_count = max(0, self._inflight_count - 1)

        if self._inflight_count == 0 and self._busy_cursor_active:
            self._busy_cursor_active = False
            QtWidgets.QApplication.restoreOverrideCursor()
            self.progress.setVisible(False)

    def _populate(self) -> None:
        """Run the filter/result queries that fill in the dialog's
        already-visible, still-empty areas.

        Filter panels are built one column per tick (see
        :meth:`_build_next_filter_column`), which calls :meth:`_refresh_all`
        itself once every column has been processed — it must not run
        against a still-partially-built ``self.filters``.
        """
        self._build_filters_for(self.current_table)

    def GetValue(self) -> Optional[int]:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: Optional[int]
        """
        sel = getattr(self.results, "selected", None)

        if sel is None:
            return None

        try:
            # get_obj_id's query matches against SQL's 1-indexed RowNum;
            # self.results.selected is Qt's 0-indexed row.
            return self.results.get_obj_id(sel + 1)
        except Exception:  # NOQA
            return None

    def _build_ui(self) -> None:
        """Build the UI.

        UNKNOWN details are inferred from the callable name and signature.
        """
        outer = QtWidgets.QVBoxLayout(self.panel)

        top = QtWidgets.QHBoxLayout()
        st = QtWidgets.QLabel("Keyword:", self.panel)
        top.addWidget(st)

        self.kw_ctrl = QtWidgets.QLineEdit(self.panel)
        self.kw_ctrl.setPlaceholderText("Part # or description...")
        self.kw_ctrl.textChanged.connect(self._on_kw_changed)
        top.addWidget(self.kw_ctrl, 1)

        clear_btn = QtWidgets.QPushButton("Clear All", self.panel)
        clear_btn.clicked.connect(self._on_clear_all)
        top.addWidget(clear_btn)

        outer.addLayout(top)

        # Horizontally scrolling filter strip
        self.filter_scroll = QtWidgets.QScrollArea(self.panel)
        self.filter_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.filter_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setFixedHeight(PANEL_H + 20)

        self._filter_container = QtWidgets.QWidget(self.panel)
        self.filter_sizer = QtWidgets.QHBoxLayout(self._filter_container)
        self.filter_sizer.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.filter_scroll.setWidget(self._filter_container)

        outer.addWidget(self.filter_scroll)

        bottom = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel("0 results", self.panel)
        bottom.addWidget(self.status)

        # Indeterminate (busy) progress bar, shown only while a query is
        # in flight on the worker thread -- see _begin_query/_end_query.
        self.progress = QtWidgets.QProgressBar(self.panel)
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(120)
        self.progress.setFixedHeight(self.status.sizeHint().height())
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        bottom.addWidget(self.progress)

        bottom.addStretch(1)
        outer.addLayout(bottom)

        self.results = self.page_class(self.panel, self.mainframe, '', self.table)

        # The page class is an EditorList (QTableView). It already keeps
        # ``results.selected`` in sync via its own selection handler, but
        # its activation handler opens the editor's edit dialog — replace
        # that with search-mode accept.
        try:
            self.results.activated.disconnect()
        except Exception:  # NOQA
            pass

        self.results.activated.connect(self._on_row_activated)

        outer.addWidget(self.results, 1)

        # OK must not accept an empty selection — without this, clicking OK
        # after filtering but before actually selecting a row silently
        # closes the dialog as "Accepted" with GetValue() returning None,
        # which every caller already treats identically to a cancel.
        ok_btn = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_btn.setEnabled(False)
        self.results.itemSelected.connect(lambda _row: ok_btn.setEnabled(True))
        self.results.itemUnselected.connect(lambda: ok_btn.setEnabled(False))

    def _build_filters_for(self, table: str) -> None:
        """Build the filters for.

        Each column is turned into a filter panel (or skipped) on its own
        deferred tick instead of all at once — a single synchronous loop
        that queries, populates, and adds every panel to the layout before
        Qt gets a chance to run a layout/paint pass is what caused
        everything to flash in squished, then snap to its expanded size
        once the loop finally returned.

        :param table: Value for ``table``.
        :type table: str
        """
        for panel in self.filters.values():
            panel.deleteLater()

        self.filters.clear()

        # Remove all items from the layout
        while self.filter_sizer.count():
            item = self.filter_sizer.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._filter_column_queue = list(sorted(self.page_class.column_mapping.keys()))

        # Defer even the first column so the (now-empty) filter strip gets
        # its own paint pass at its correct size before any option is
        # queried and added — otherwise the first panel still lands in the
        # same tick as the section's own creation.
        QtCore.QTimer.singleShot(0, lambda: self._build_next_filter_column(table))

    def _build_next_filter_column(self, table: str) -> None:
        """Build one column's filter panel (if warranted), then queue the
        next — or, once every column has been processed, run the initial
        filter-availability/result refresh that depends on the full set of
        filter panels existing.

        Chaining to the next column happens inside :meth:`_build_filter_column`
        itself once that column's query (if any) actually returns, rather
        than on a fixed timer -- the async dispatch to the worker thread is
        what yields back to the event loop between columns now.
        """
        if not self._filter_column_queue:
            self._refresh_all()
            return

        idx = self._filter_column_queue.pop(0)
        self._build_filter_column(table, idx)

    def _build_filter_column(self, table: str, idx: int) -> None:
        """Query one column and add its filter panel to the layout, if
        warranted. The column's query (if any) runs on the worker thread;
        :meth:`_build_next_filter_column` is invoked once it's done,
        whether that's synchronously (skipped column, no query needed) or
        from the query's result callback.
        """
        label, alias_dict = self.page_class.column_mapping[idx][:2]

        field_name = alias_dict.get('field_name', '')
        ref_table = alias_dict.get('ref_table')
        ref_field = alias_dict.get('ref_field')

        # Skip the primary key and columns absent from the actual DB table
        # (virtual/computed fields, blob arrays, model references, etc.).
        if field_name == 'id' or field_name not in self.info.columns:
            self._build_next_filter_column(table)
            return

        if ref_table and ref_field:
            # Foreign-key column — populate choices from the linked table.
            sql = (f'SELECT DISTINCT r.{ref_field} '
                   f'FROM {table} t '
                   f'JOIN {ref_table} r ON t.{field_name} = r.id '
                   f'WHERE r.{ref_field} IS NOT NULL '
                   f'ORDER BY r.{ref_field} COLLATE NOCASE;')

            def _on_fk_rows(rows):
                if len(rows) >= MIN_DISTINCT_FOR_FILTER:
                    p = FKFilterPanel(self._filter_container, field_name, ref_table,
                                      ref_field, label, self._on_filter_changed)
                    p.populate([r[0] for r in rows])
                    self.filters[field_name] = p
                    self.filter_sizer.addWidget(p)

                self._build_next_filter_column(table)

            self._run_query_async(sql, [], _on_fk_rows)
            return

        # Plain column — only numeric types get a filter widget.
        col_type = self.info.columns.get(field_name, '')
        is_int = 'INT' in col_type
        is_real = any(t in col_type for t in ('REAL', 'FLOA', 'DOUB', 'NUMERIC'))

        if not is_int and not is_real:
            self._build_next_filter_column(table)
            return

        sql = (f'SELECT DISTINCT t.{field_name} FROM {table} t '
               f'WHERE t.{field_name} IS NOT NULL ORDER BY t.{field_name};')

        def _on_values(rows):
            values = [r[0] for r in rows]

            if len(values) < MIN_DISTINCT_FOR_FILTER:
                self._build_next_filter_column(table)
                return

            if is_int and len(values) <= MAX_DISTINCT_FOR_ENUM:
                p = EnumFilterPanel(self._filter_container, field_name, label,
                                    self._on_filter_changed)
                p.populate(values)
                self.filters[field_name] = p
                self.filter_sizer.addWidget(p)
                self._build_next_filter_column(table)
                return

            minmax_sql = (f'SELECT MIN(t.{field_name}), MAX(t.{field_name}) '
                          f'FROM {table} t WHERE t.{field_name} IS NOT NULL;')

            def _on_minmax(mm_rows):
                lo, hi = (None, None) if not mm_rows else mm_rows[0]

                if lo is not None and hi is not None and lo != hi:
                    p = RangeFilterPanel(self._filter_container, field_name, is_int,
                                         label, self._on_filter_changed)
                    p.update_bounds(lo, hi)
                    self.filters[field_name] = p
                    self.filter_sizer.addWidget(p)

                self._build_next_filter_column(table)

            self._run_query_async(minmax_sql, [], _on_minmax)

        self._run_query_async(sql, [], _on_values)

    def _on_kw_changed(self) -> None:
        """Handle the kw changed event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if hasattr(self, "_kw_timer"):
            self._kw_timer.stop()
        else:
            self._kw_timer = QtCore.QTimer(self)
            self._kw_timer.setSingleShot(True)
            self._kw_timer.timeout.connect(self._refresh_all)  # NOQA

        self._kw_timer.start(180)

    def _on_filter_changed(self, _changed_panel) -> None:
        """Handle the filter changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _changed_panel: Value for ``changed_panel``.
        :type _changed_panel: UNKNOWN
        """
        self._refresh_all()

    def _on_clear_all(self) -> None:
        """Handle the clear all event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.kw_ctrl.blockSignals(True)
        self.kw_ctrl.clear()
        self.kw_ctrl.blockSignals(False)

        for p in self.filters.values():
            p.clear()

        self._refresh_all()

    def _refresh_all(self) -> None:
        """Kick off a chunked filter-availability refresh (one panel's
        query per tick, same pattern as :meth:`_build_next_filter_column`),
        then push the filtered results once every panel has been updated.

        Must not run every panel's availability query synchronously in one
        shot: housings has ~24 filterable FK/numeric columns versus a
        handful for tpa_locks/covers, and each query is an unindexed
        full-table scan (FK panels are a scan plus join) over the whole
        catalog table. Running them all back-to-back on the UI thread is
        what reads as the dialog "hanging" for housings specifically.
        """
        self._refresh_gen = getattr(self, '_refresh_gen', 0) + 1
        self._refresh_col_queue = list(self.filters.keys())
        self._refresh_next_filter_availability(self._refresh_gen)

    def _refresh_next_filter_availability(self, gen: int) -> None:
        """Refresh one filter panel's availability, then queue the next --
        or, once the queue is empty, push the filtered results to the page.

        Chaining to the next panel happens inside
        :meth:`_refresh_filter_column_availability` itself once that
        panel's query actually returns, rather than on a fixed timer.

        :param gen: Generation token captured when the refresh started;
            if a newer :meth:`_refresh_all` call has since bumped
            ``self._refresh_gen``, this chain is stale and aborts instead
            of racing the newer one or double-calling
            :meth:`_push_filter_to_page`.
        :type gen: int
        """
        if gen != self._refresh_gen:
            return

        if not self._refresh_col_queue:
            self._push_filter_to_page()
            return

        col = self._refresh_col_queue.pop(0)
        panel = self.filters.get(col)

        if panel is None:
            self._refresh_next_filter_availability(gen)
            return

        self._refresh_filter_column_availability(col, panel, gen)

    def _build_predicates(
        self,
        exclude: Optional[str] = None
    ) -> Tuple[List[str], List[Any]]:
        """Build the predicates.

        UNKNOWN details are inferred from the callable name and signature.

        :param exclude: Value for ``exclude``.
        :type exclude: Optional[str]
        :returns: Return value. UNKNOWN details.
        :rtype: Tuple[List[str], List[Any]]
        """

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

    def _refresh_filter_column_availability(self, col: str, panel: _FilterPanelBase,
                                            gen: int) -> None:
        """Run the single availability query for one filter panel, then
        continue the chunked refresh chain once it returns.

        :param col: Value for ``col``.
        :type col: str
        :param panel: Value for ``panel``.
        :type panel: _FilterPanelBase
        :param gen: Generation token; a result that arrives after a newer
            :meth:`_refresh_all` call has superseded this chain is applied
            to nothing and does not continue the (now-stale) chain.
        :type gen: int
        """
        table = self.current_table

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

            def _on_rows(rows):
                if gen != self._refresh_gen:
                    return
                panel.update_availability([r[0] for r in rows if r[0] is not None])
                self._refresh_next_filter_availability(gen)

            self._run_query_async(sql, params, _on_rows)

        elif isinstance(panel, EnumFilterPanel):
            sql = (f'SELECT DISTINCT t.{col} '
                   f'FROM {table} t {where};')

            def _on_rows(rows):
                if gen != self._refresh_gen:
                    return
                panel.update_availability([r[0] for r in rows if r[0] is not None])
                self._refresh_next_filter_availability(gen)

            self._run_query_async(sql, params, _on_rows)

        elif isinstance(panel, RangeFilterPanel):
            sql = (f'SELECT MIN(t.{col}), MAX(t.{col}) '
                   f'FROM {table} t {where};')

            def _on_rows(rows):
                if gen != self._refresh_gen:
                    return
                lo, hi = (None, None) if not rows else rows[0]
                panel.update_bounds(lo, hi)
                self._refresh_next_filter_availability(gen)

            self._run_query_async(sql, params, _on_rows)

        else:
            self._refresh_next_filter_availability(gen)

    def _push_filter_to_page(self) -> None:
        """Execute the push filter to page operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        clauses, params = self._build_predicates()

        # With no keyword or filters active, default to the compatible-part
        # list supplied by the caller; any user input searches as normal.
        if (
            not clauses and
            self.initial_results and
            "part_number" in self.info.columns
        ):
            placeholders = ",".join(["?"] * len(self.initial_results))
            clauses.append(f't.part_number IN ({placeholders})')
            params.extend(self.initial_results)

        if clauses:
            where_clause = " AND ".join(clauses)
        else:
            where_clause = ""

        self.results.set_filter(where_clause, params)

        # set_filter() already computed and cached this count as part of
        # resetting the model -- re-reading self.results.record_count here
        # would silently re-run the same COUNT query a second time.
        total = self.results._row_count  # NOQA
        self.status.setText(f"{total:,} result{'s' if total != 1 else ''}")

    def _on_row_activated(self, index) -> None:
        """Handle the row activated event.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Model index of the activated row.
        :type index: :class:`QtCore.QModelIndex`
        """
        self.results.selected = index.row()
        if self.GetValue() is not None:
            self.accept()
