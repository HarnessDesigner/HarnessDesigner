# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Network tab: every fetch / XHR call the page has made."""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ...scraping import capture_model as _capture_model
from ... import check_types as _check_types

# The list is a rolling window: a page that polls every second would
# otherwise grow it without bound.
MAX_REQUESTS = 2000

_COLUMNS = ('#', 'Method', 'Status', 'Type', 'Size', 'Time', 'URL')
_ERROR_COLOR = QtGui.QColor(220, 80, 80)
_JSON_COLOR = QtGui.QColor(110, 180, 110)


class NetworkModel(QtCore.QAbstractTableModel):
    """The captured requests, oldest first."""

    @_check_types.do
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._requests: list[_capture_model.CapturedRequest] = []

    @_check_types.do
    def add(self, request: _capture_model.CapturedRequest) -> None:
        if len(self._requests) >= MAX_REQUESTS:
            self.beginRemoveRows(QtCore.QModelIndex(), 0, 0)
            del self._requests[0]
            self.endRemoveRows()

        row = len(self._requests)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._requests.append(request)
        self.endInsertRows()

    @_check_types.do
    def clear(self) -> None:
        self.beginResetModel()
        self._requests.clear()
        self.endResetModel()

    @_check_types.do
    def request_at(self, row: int) -> _capture_model.CapturedRequest:
        return self._requests[row]

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # NOQA -- Qt override
        if parent.isValid():
            return 0

        return len(self._requests)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # NOQA -- Qt override
        if parent.isValid():
            return 0

        return len(_COLUMNS)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,  # NOQA -- Qt override
                   role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> object:
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return _COLUMNS[section]

        return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> object:  # NOQA
        if not index.isValid():
            return None

        request = self._requests[index.row()]
        column = index.column()

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._text(request, column)

        if role == QtCore.Qt.ItemDataRole.ToolTipRole and column == 6:
            return request.url

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if request.status == 0 or request.status >= 400:
                return _ERROR_COLOR

            if column == 3 and request.is_json:
                return _JSON_COLOR

        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole and column in (0, 2, 4, 5):
            return int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        return None

    @_check_types.do
    def _text(self, request: _capture_model.CapturedRequest, column: int) -> str:
        if column == 0:
            return str(request.number)

        if column == 1:
            return request.method

        if column == 2:
            if request.status == 0:
                return 'failed'

            return str(request.status)

        if column == 3:
            if request.is_json:
                return 'json'

            return request.content_type.split('/')[-1] or '-'

        if column == 4:
            return _capture_model.describe_size(request.size)

        if column == 5:
            return f'{request.duration_ms} ms'

        return request.display_url


class _FilterModel(QtCore.QSortFilterProxyModel):
    """Rows whose URL or type contains the filter text; optionally only
    JSON responses."""

    @_check_types.do
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._text = ''
        self._json_only = False

    @_check_types.do
    def set_text(self, text: str) -> None:
        self.beginFilterChange()
        self._text = text.strip().lower()
        self.endFilterChange(QtCore.QSortFilterProxyModel.Direction.Rows)

    @_check_types.do
    def set_json_only(self, json_only: bool) -> None:
        self.beginFilterChange()
        self._json_only = json_only
        self.endFilterChange(QtCore.QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:  # NOQA -- Qt override
        model = self.sourceModel()
        request = model.request_at(source_row)

        if self._json_only and not request.is_json:
            return False

        if not self._text:
            return True

        haystack = f'{request.url} {request.content_type} {request.method}'.lower()
        return self._text in haystack


class NetworkPanel(QtWidgets.QWidget):
    """:ivar requestSelected: A row was selected (``CapturedRequest``).
    :ivar requestsCleared: The list was cleared.
    """

    requestSelected = QtCore.Signal(object)
    requestsCleared = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = NetworkModel(self)
        self._filter = _FilterModel(self)
        self._filter.setSourceModel(self._model)

        self._search = QtWidgets.QLineEdit(self)
        self._search.setPlaceholderText('Filter by URL or type')
        self._search.setClearButtonEnabled(True)
        self._json_only = QtWidgets.QCheckBox('JSON only', self)
        self._clear = QtWidgets.QPushButton('Clear', self)

        self._table = QtWidgets.QTableView(self)
        self._table.setModel(self._filter)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 55)
        self._table.setColumnWidth(3, 60)
        self._table.setColumnWidth(4, 70)
        self._table.setColumnWidth(5, 70)

        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(self._search, 1)
        bar.addWidget(self._json_only)
        bar.addWidget(self._clear)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self._table, 1)

        self._search.textChanged.connect(self._filter.set_text)
        self._json_only.toggled.connect(self._filter.set_json_only)
        self._clear.clicked.connect(self.clear)
        self._table.selectionModel().currentRowChanged.connect(self._row_changed)

    @_check_types.do
    def add_request(self, request: _capture_model.CapturedRequest) -> None:
        # Keep the view at the newest row only when it already was.
        bar = self._table.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 2

        self._model.add(request)
        if at_bottom:
            self._table.scrollToBottom()

    @_check_types.do
    def clear(self) -> None:
        self._model.clear()
        self.requestsCleared.emit()

    @_check_types.do
    def request_count(self) -> int:
        return self._model.rowCount()

    @_check_types.do
    def visible_request_count(self) -> int:
        return self._filter.rowCount()

    @_check_types.do
    def select_row(self, row: int) -> None:
        """Select the *row*-th visible row (as the user would by clicking)."""
        self._table.selectRow(row)
        self._row_changed(self._filter.index(row, 0), QtCore.QModelIndex())

    @_check_types.do
    def _row_changed(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex) -> None:
        if not current.isValid():
            return

        source = self._filter.mapToSource(current)
        self.requestSelected.emit(self._model.request_at(source.row()))
