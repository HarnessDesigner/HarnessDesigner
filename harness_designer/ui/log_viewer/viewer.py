# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Optional, List

import threading
import os
import time
import zipfile
import io
import pandas as pd

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

if TYPE_CHECKING:
    from ... import logger as _logger
    from .. import mainframe as _mainframe

from ... import config as _config

Config = _config.Config.logging


# ---------------------------------------------------------------------------
# Log level colours (replaces wx.ItemAttr colour mapping)
# ---------------------------------------------------------------------------

_LEVEL_COLOURS = {
    'ERROR':     QtGui.QColor(QtCore.Qt.GlobalColor.red),
    'TRACEBACK': QtGui.QColor(QtCore.Qt.GlobalColor.red),
    'WARNING':   QtGui.QColor(255, 140, 0),
    'WARN':      QtGui.QColor(255, 140, 0),
    'NOTICE':    QtGui.QColor(0, 100, 200),
    'DEBUG':     QtGui.QColor(128, 128, 128),
}


class _LogMessageDelegate(QtWidgets.QStyledItemDelegate):
    """Paint explicit multiline log messages without soft wrapping."""

    _TEXT_HORIZONTAL_PADDING = 6
    _TEXT_VERTICAL_PADDING = 4

    def paint(self, painter, option, index):
        if index.column() != 2:
            super().paint(painter, option, index)
            return

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        text = opt.text
        opt.text = ''

        if opt.widget is not None:
            style = opt.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem,
                          opt, painter, opt.widget)

        text_rect = style.subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        text_rect.adjust(self._TEXT_HORIZONTAL_PADDING,
                         self._TEXT_VERTICAL_PADDING,
                         -self._TEXT_HORIZONTAL_PADDING,
                         -self._TEXT_VERTICAL_PADDING)

        painter.save()
        painter.setFont(opt.font)
        if opt.state & QtWidgets.QStyle.StateFlag.State_Selected:
            painter.setPen(
                opt.palette.color(QtGui.QPalette.ColorRole.HighlightedText))
        else:
            foreground = index.data(QtCore.Qt.ItemDataRole.ForegroundRole)
            if isinstance(foreground, QtGui.QBrush):
                painter.setPen(foreground.color())
            elif isinstance(foreground, QtGui.QColor):
                painter.setPen(foreground)
            else:
                painter.setPen(opt.palette.color(QtGui.QPalette.ColorRole.Text))

        flags = (QtCore.Qt.AlignmentFlag.AlignLeft |
                 QtCore.Qt.AlignmentFlag.AlignTop |
                 QtCore.Qt.TextFlag.TextExpandTabs |
                 QtCore.Qt.TextFlag.TextDontClip)

        painter.drawText(text_rect, flags, text)
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        if index.column() != 2:
            return size

        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not text:
            return size

        font_metrics = option.fontMetrics
        lines = str(text).splitlines() or ['']
        line_count = max(1, len(lines))
        height = (
            font_metrics.lineSpacing() * line_count +
            (self._TEXT_VERTICAL_PADDING * 2)
        )
        width = size.width()

        longest_line = max(lines, key=len, default='')
        width = max(
            width,
            font_metrics.horizontalAdvance(longest_line) +
            (self._TEXT_HORIZONTAL_PADDING * 2)
        )

        return QtCore.QSize(width, height)


# ---------------------------------------------------------------------------
# VirtualLogListCtrl replacement: QAbstractTableModel + QTableView
# ---------------------------------------------------------------------------

class _LogModel(QtCore.QAbstractTableModel):
    """
    Represent a log model in :mod:`harness_designer.ui.log_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _HEADERS = ['Timestamp', 'Level', 'Message']
    _COLS = ['timestamp_str', 'level', 'message']

    def __init__(self, parent=None):
        """
        Initialise the :class:`_LogModel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        super().__init__(parent)
        self._data = pd.DataFrame(
            columns=['timestamp', 'level', 'message', 'timestamp_str'])

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        Execute the row count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return len(self._data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        Execute the column count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return 3

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        """
        Execute the header data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param section: Value for ``section``.
        :type section: UNKNOWN
        :param orientation: Value for ``orientation``.
        :type orientation: UNKNOWN
        :param role: Value for ``role``.
        :type role: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        if (
            orientation == QtCore.Qt.Orientation.Horizontal and
            role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self._HEADERS[section]

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        """
        Execute the data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :param role: Value for ``role``.
        :type role: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        if not index.isValid() or index.row() >= len(self._data):
            return None

        row = self._data.iloc[index.row()]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            col = self._COLS[index.column()]
            return str(row.get(col, ''))

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            level = str(row.get('level', '')).upper()
            for key, colour in _LEVEL_COLOURS.items():
                if key in level:
                    return colour

        return None

    def _ensure_timestamp_str(self, df: pd.DataFrame) -> pd.DataFrame:  # NOQA
        """
        Ensure the timestamp str.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`pd.DataFrame`
        """

        if not df.empty and 'timestamp' in df.columns:
            df = df.copy()
            df['timestamp_str'] = df['timestamp'].astype(str)

        return df

    def set_data(self, df: pd.DataFrame):
        """
        Set the data.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        """

        self.beginResetModel()

        if not df.empty:
            new_df = df.copy()
        else:
            new_df = pd.DataFrame(columns=['timestamp', 'level', 'message'])

        self._data = self._ensure_timestamp_str(new_df)
        self.endResetModel()

    def append_data(self, df: pd.DataFrame):
        """
        Execute the append data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        """

        if df.empty:
            return

        df = self._ensure_timestamp_str(df)
        first = len(self._data)
        last = first + len(df) - 1
        self.beginInsertRows(QtCore.QModelIndex(), first, last)
        self._data = pd.concat([self._data, df], ignore_index=True)
        self.endInsertRows()


class VirtualLogListCtrl(QtWidgets.QTableView):
    """Replaces wx.ListCtrl (LC_REPORT | LC_VIRTUAL | LC_SINGLE_SEL)."""

    _append_ready: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent):
        """
        Initialise the :class:`VirtualLogListCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        super().__init__(parent)

        self._model = _LogModel(self)
        self.setModel(self._model)

        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)

        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed)

        self.setItemDelegateForColumn(2, _LogMessageDelegate(self))

        hdr = self.horizontalHeader()
        hdr.resizeSection(0, 180)
        hdr.resizeSection(1, 100)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hdr.sectionResized.connect(self._on_section_resized)

        self._is_destroyed = False
        self._append_ready.connect(
            self._do_append, QtCore.Qt.ConnectionType.QueuedConnection)

    def Destroy(self):
        """
        Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """

        self._is_destroyed = True
        self.deleteLater()

    def _row_height_for_text(self, text: str) -> int:
        font_metrics = self.fontMetrics()
        lines = str(text).splitlines() or ['']
        line_count = max(1, len(lines))
        top_bottom_margins = 8
        return (font_metrics.lineSpacing() * line_count) + top_bottom_margins

    def _resize_row_heights(self, first_row: int = 0,
                            last_row: int | None = None):

        row_count = self._model.rowCount()
        if row_count <= 0:
            return

        if last_row is None:
            last_row = row_count - 1

        first_row = max(0, int(first_row))
        last_row = min(int(last_row), row_count - 1)
        if last_row < first_row:
            return

        default_height = max(self.fontMetrics().height() + 8,
                             self.verticalHeader().defaultSectionSize())

        self.setUpdatesEnabled(False)
        try:
            for row in range(first_row, last_row + 1):
                index = self._model.index(row, 2)
                text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
                if text is None:
                    self.setRowHeight(row, default_height)
                    continue

                self.setRowHeight(
                    row, max(default_height, self._row_height_for_text(text)))
        finally:
            self.setUpdatesEnabled(True)

    def _do_append(self, new_data: pd.DataFrame):
        """
        Execute the do append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param new_data: Value for ``new_data``.
        :type new_data: :class:`pd.DataFrame`
        """

        if not self._is_destroyed:
            first_row = self._model.rowCount()
            self._model.append_data(new_data)
            last_row = self._model.rowCount() - 1
            self._resize_row_heights(first_row, last_row)

    def AppendData(self, data: pd.DataFrame):
        """
        Execute the append data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param data: Data payload.
        :type data: :class:`pd.DataFrame`
        """

        # Emit the signal so the append always runs on the main thread,
        # even when AppendData is called from a worker thread.
        self._append_ready.emit(data)

    def SetData(self, df: pd.DataFrame):
        """
        Execute the set data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        """

        self._model.set_data(df)
        self._resize_row_heights()

    def _on_section_resized(self, logical_index: int,
                            _old_size: int, _new_size: int):

        # Row height depends only on explicit newline count, not column width.
        # Recomputing every row while the splitter is dragged causes severe lag.
        return


# ---------------------------------------------------------------------------
# LogViewerPanel — QSplitter replacing wx.SplitterWindow
# ---------------------------------------------------------------------------

class LogViewerPanel(QtWidgets.QSplitter):
    """
    Represent a log viewer panel in :mod:`harness_designer.ui.log_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # Signal used to marshal worker-thread results back onto the main thread.
    # QTimer.singleShot called from a plain threading.Thread (which has no Qt
    # event loop) never fires, so we use a queued signal connection instead.

    # carries a zero-argument callable
    _callback_ready: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, logger: "_logger.Log"):
        """
        Initialise the :class:`LogViewerPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param logger: Value for ``logger``.
        :type logger: :class:`_logger.Log`
        """

        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)

        self.logger = logger
        self._curr_log = None
        self._is_destroyed = False
        self.current_data = pd.DataFrame()
        self.expanded_items: set = set()

        # Left pane: tree
        self.treectrl = QtWidgets.QTreeWidget(self)
        self.treectrl.setHeaderHidden(True)
        self.treectrl.setRootIsDecorated(True)
        self.root = QtWidgets.QTreeWidgetItem(self.treectrl, ['Logs'])
        self.treectrl.addTopLevelItem(self.root)

        # Right pane: log list
        self.log_list = VirtualLogListCtrl(self)

        self.addWidget(self.treectrl)
        self.addWidget(self.log_list)
        self.setSizes([200, 800])
        self.setCollapsible(0, False)
        self.setCollapsible(1, False)

        self.treectrl.itemSelectionChanged.connect(
            self._on_tree_selection_changed)

        self.treectrl.itemExpanded.connect(self.on_tree_expanding)
        self.treectrl.itemCollapsed.connect(self.on_tree_collapsed)

        # Route worker-thread callbacks safely to the main thread via a queued
        # signal connection (QTimer.singleShot from a plain threading.Thread has
        # no event loop to fire in, so it silently never runs).
        self._callback_ready.connect(
            self._run_callback, QtCore.Qt.ConnectionType.QueuedConnection)

        logger.log_handler.bind(self.new_data)

        def _do():
            """
            Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.
            """

            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.WaitCursor)

            try:
                self.load()
                self._load_current_log_initial()
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

        QtCore.QTimer.singleShot(0, _do)

    def Destroy(self):
        """
        Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """

        self._is_destroyed = True
        self.log_list.Destroy()
        self.deleteLater()

    def _run_callback(self, fn):  # NOQA
        """Slot that executes a callable posted from a worker thread."""
        fn()

    def _load_current_log_initial(self):
        """
        Load the current log initial.

        UNKNOWN details are inferred from the callable name and signature.
        """

        try:
            current_log_path = self.logger.log_handler.get_current_log_path()
            if current_log_path and os.path.exists(current_log_path):
                df = self._read_log_file(current_log_path)
                self.current_data = df
                self.log_list.SetData(df)

        except Exception as e:
            self.logger.error(f"Failed to load initial log: {e}")

    def new_data(self, data=None):
        """
        Execute the new data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param data: Data payload.
        :type data: UNKNOWN
        """

        if self._is_destroyed:
            return

        if data is None:
            self.load()
        else:
            if self._curr_log is not None:
                self.log_list.AppendData(data)

    # ------------------------------------------------------------------
    # Tree selection
    # ------------------------------------------------------------------

    def _on_tree_selection_changed(self):
        """
        Handle the tree selection changed event.

        UNKNOWN details are inferred from the callable name and signature.
        """

        items = self.treectrl.selectedItems()
        if not items:
            return

        item = items[0]
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get('type')
        if item_type == 'file':
            self._load_log_data(data['path'])
        elif item_type == 'date':
            self._load_log_data(data['file'], date_filter=data['date'])
        elif item_type == 'hour':
            self._load_log_data(
                data['file'], date_filter=data['date'], hour_filter=data['hour'])
        elif item_type == 'archive_file':
            self._load_archive_file(data['zipfile'], data['filename'])

    def on_tree_expanding(self, item: QtWidgets.QTreeWidgetItem):
        """
        Handle the tree expanding event.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        item_id = id(item)
        if item_id in self.expanded_items:
            return

        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get('type')
        if item_type == 'file':
            self._load_dates_for_file(item, data['path'], item_id)
        elif item_type == 'date':
            self._load_hours_for_date(item, data['file'], data['date'], item_id)
        elif item_type == 'archive':
            self._load_archive_files(item, data['path'], item_id)
        elif item_type == 'archive_file':
            self._load_dates_for_archive_file(
                item, data['zipfile'], data['filename'], item_id)
        elif item_type == 'archive_date':
            self._load_hours_for_archive_date(
                item, data['zipfile'], data['filename'], data['date'], item_id)

    def on_tree_collapsed(self, item: QtWidgets.QTreeWidgetItem):
        """
        Handle the tree collapsed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        item_id = id(item)
        self.expanded_items.discard(item_id)
        item.takeChildren()
        QtWidgets.QTreeWidgetItem(item, ['Loading...'])

    # ------------------------------------------------------------------
    # Lazy-load helpers
    # ------------------------------------------------------------------

    def _load_dates_for_file(self, file_item: QtWidgets.QTreeWidgetItem,
                             log_path: str, item_id: int):
        """
        Load the dates for file.

        UNKNOWN details are inferred from the callable name and signature.

        :param file_item: Value for ``file_item``.
        :type file_item: :class:`QtWidgets.QTreeWidgetItem`
        :param log_path: Value for ``log_path``.
        :type log_path: str
        :param item_id: Identifier for the item.
        :type item_id: int
        """

        file_item.takeChildren()
        QtWidgets.QTreeWidgetItem(file_item, ['Loading dates...'])

        def load_dates():
            """
            Load the dates.

            UNKNOWN details are inferred from the callable name and signature.
            """

            dates = self._get_dates_in_log(log_path)
            self._callback_ready.emit(
                lambda: self._populate_dates(file_item, log_path, dates, item_id))

        threading.Thread(target=load_dates, daemon=True).start()

    def _populate_dates(self, parent_item: QtWidgets.QTreeWidgetItem, log_path: str,
                        dates: List[str], item_id: int):
        """
        Execute the populate dates operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent_item: Value for ``parent_item``.
        :type parent_item: :class:`QtWidgets.QTreeWidgetItem`
        :param log_path: Value for ``log_path``.
        :type log_path: str
        :param dates: Value for ``dates``.
        :type dates: List[str]
        :param item_id: Identifier for the item.
        :type item_id: int
        """

        parent_item.takeChildren()
        self.expanded_items.add(item_id)

        if not dates:
            QtWidgets.QTreeWidgetItem(parent_item, ['(No dates found)'])
            return

        for date_str in dates:
            date_item = QtWidgets.QTreeWidgetItem(parent_item, [date_str])
            date_item.setData(0,
                              QtCore.Qt.ItemDataRole.UserRole,
                              {'type': 'date', 'file': log_path, 'date': date_str})

            QtWidgets.QTreeWidgetItem(date_item, ['Loading...'])

    def _load_hours_for_date(self, date_item: QtWidgets.QTreeWidgetItem, log_path: str,
                             date_str: str, item_id: int):
        """
        Load the hours for date.

        UNKNOWN details are inferred from the callable name and signature.

        :param date_item: Value for ``date_item``.
        :type date_item: :class:`QtWidgets.QTreeWidgetItem`
        :param log_path: Value for ``log_path``.
        :type log_path: str
        :param date_str: Value for ``date_str``.
        :type date_str: str
        :param item_id: Identifier for the item.
        :type item_id: int
        """

        date_item.takeChildren()
        QtWidgets.QTreeWidgetItem(date_item, ['Loading hours...'])

        def load_hours():
            """
            Load the hours.

            UNKNOWN details are inferred from the callable name and signature.
            """

            hours = self._get_hours_in_date(log_path, date_str)
            self._callback_ready.emit(lambda: self._populate_hours(
                date_item, log_path, date_str, hours, item_id, False))

        threading.Thread(target=load_hours, daemon=True).start()

    def _populate_hours(self, parent_item: QtWidgets.QTreeWidgetItem,
                        log_path: Optional[str], date_str: str,
                        hours: List[int], item_id: int, is_archive: bool,
                        zipfile_obj=None, filename=None):
        """
        Execute the populate hours operation.

        UNKNOWN details are inferred from the callable name and surrounding code.
        """

        parent_item.takeChildren()
        self.expanded_items.add(item_id)
        if not hours:
            QtWidgets.QTreeWidgetItem(parent_item, ['(No hours found)'])
            return

        for hour in hours:
            hour_label = f"{hour:02d}:00 - {hour:02d}:59"
            hour_item = QtWidgets.QTreeWidgetItem(parent_item, [hour_label])
            if is_archive:
                hour_item.setData(0,
                                  QtCore.Qt.ItemDataRole.UserRole,
                                  {'type': 'archive_hour',
                                   'zipfile': zipfile_obj, 'filename': filename,
                                   'date': date_str, 'hour': hour})

            else:
                hour_item.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                                  {'type': 'hour', 'file': log_path,
                                   'date': date_str, 'hour': hour})

    def _load_archive_files(self, archive_item: QtWidgets.QTreeWidgetItem,
                            archive_path: str, item_id: int):
        """Load the archive files."""

        archive_item.takeChildren()
        try:
            zf = zipfile.ZipFile(archive_path, 'r')
            names = zf.namelist()
            self.expanded_items.add(item_id)
            for name in names:
                if name.endswith('.csv'):
                    child = QtWidgets.QTreeWidgetItem(archive_item, [name])
                    child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                                  {'type': 'archive_file',
                                   'zipfile': zf, 'filename': name})

                    QtWidgets.QTreeWidgetItem(child, ['Loading...'])
        except Exception as e:
            self.logger.error(f"Failed to load archive {archive_path}: {e}")
            QtWidgets.QTreeWidgetItem(archive_item, ['(Error loading archive)'])

    def _load_dates_for_archive_file(self, file_item: QtWidgets.QTreeWidgetItem,
                                     zipfile_obj, filename: str, item_id: int):
        """Load the dates for archive file."""

        file_item.takeChildren()
        QtWidgets.QTreeWidgetItem(file_item, ['Loading dates...'])

        def load_dates():
            dates = self._get_dates_in_archive(zipfile_obj, filename)

            self._callback_ready.emit(
                lambda: self._populate_archive_dates(
                    file_item, zipfile_obj, filename, dates, item_id))

        threading.Thread(target=load_dates, daemon=True).start()

    def _populate_archive_dates(self, parent_item: QtWidgets.QTreeWidgetItem,
                                zipfile_obj, filename: str,
                                dates: List[str], item_id: int):
        """Execute the populate archive dates operation."""

        parent_item.takeChildren()
        self.expanded_items.add(item_id)
        if not dates:
            QtWidgets.QTreeWidgetItem(parent_item, ['(No dates found)'])
            return
        for date_str in dates:
            date_item = QtWidgets.QTreeWidgetItem(parent_item, [date_str])
            date_item.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                              {'type': 'archive_date', 'zipfile': zipfile_obj,
                               'filename': filename, 'date': date_str})

            QtWidgets.QTreeWidgetItem(date_item, ['Loading...'])

    def _load_hours_for_archive_date(self, date_item: QtWidgets.QTreeWidgetItem,
                                     zipfile_obj, filename: str,
                                     date_str: str, item_id: int):
        """Load the hours for archive date."""

        date_item.takeChildren()
        QtWidgets.QTreeWidgetItem(date_item, ['Loading hours...'])

        def load_hours():
            hours = self._get_hours_in_archive_date(zipfile_obj, filename, date_str)

            self._callback_ready.emit(
                lambda: self._populate_hours(
                    date_item, None, date_str, hours, item_id,
                    True, zipfile_obj, filename))

        threading.Thread(target=load_hours, daemon=True).start()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_log_data(self, log_path: str, date_filter: Optional[str] = None,
                       hour_filter: Optional[int] = None):
        """Load the log data."""

        def load_data():
            df = self._read_log_file(log_path)
            if date_filter and hour_filter is not None:
                df = self._filter_by_date_and_hour(df, date_filter, hour_filter)
            elif date_filter:
                df = self._filter_by_date(df, date_filter)

            self._callback_ready.emit(lambda: self._display_log_data(df))

        threading.Thread(target=load_data, daemon=True).start()

    def _load_archive_file(self, zipfile_obj, filename: str,
                           date_filter: Optional[str] = None,
                           hour_filter: Optional[int] = None):
        """Load the archive file."""

        def load_data():
            df = self._read_archive_file(zipfile_obj, filename)
            if date_filter and hour_filter is not None:
                df = self._filter_by_date_and_hour(df, date_filter, hour_filter)
            elif date_filter:
                df = self._filter_by_date(df, date_filter)

            self._callback_ready.emit(lambda: self._display_log_data(df))

        threading.Thread(target=load_data, daemon=True).start()

    def _display_log_data(self, df: pd.DataFrame):
        """Execute the display log data operation."""

        self.current_data = df
        self.log_list.SetData(df)

    # ------------------------------------------------------------------
    # File / data helpers (logic identical to original)
    # ------------------------------------------------------------------

    def _read_log_file(self, log_path: str) -> pd.DataFrame:
        """Execute the read log file operation."""

        try:
            if not os.path.exists(log_path):
                return pd.DataFrame(columns=['timestamp', 'level', 'message'])

            df = pd.read_csv(log_path, encoding='utf-8')
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            return df

        except Exception as e:
            self.logger.error(f"Failed to read log file {log_path}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _read_archive_file(self, zipfile_obj, filename: str) -> pd.DataFrame:
        """Execute the read archive file operation."""

        try:
            data = zipfile_obj.read(filename)
            df = pd.read_csv(io.BytesIO(data), encoding='utf-8')
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            return df

        except Exception as e:
            self.logger.error(f"Failed to read archive file {filename}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _get_dates_in_log(self, log_path: str) -> List[str]:
        df = self._read_log_file(log_path)
        if df.empty or 'timestamp' not in df.columns:
            return []

        dates = df['timestamp'].dt.date.unique()

        return sorted([str(d) for d in dates], reverse=True)

    def _get_dates_in_archive(self, zipfile_obj, filename: str) -> List[str]:
        df = self._read_archive_file(zipfile_obj, filename)
        if df.empty or 'timestamp' not in df.columns:
            return []

        dates = df['timestamp'].dt.date.unique()

        return sorted([str(d) for d in dates], reverse=True)

    def _get_hours_in_date(self, log_path: str, date_str: str) -> List[int]:
        df = self._read_log_file(log_path)
        if df.empty or 'timestamp' not in df.columns:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]
        if df_date.empty:
            return []

        return sorted(df_date['timestamp'].dt.hour.unique().tolist())

    def _get_hours_in_archive_date(self, zipfile_obj, filename: str,
                                   date_str: str) -> List[int]:

        df = self._read_archive_file(zipfile_obj, filename)
        if df.empty or 'timestamp' not in df.columns:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]
        if df_date.empty:
            return []

        return sorted(df_date['timestamp'].dt.hour.unique().tolist())

    @staticmethod
    def _filter_by_date(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        if df.empty or 'timestamp' not in df.columns:
            return df

        target_date = pd.to_datetime(date_str).date()

        return df[df['timestamp'].dt.date == target_date].copy()

    @staticmethod
    def _filter_by_date_and_hour(df: pd.DataFrame, date_str: str,
                                 hour: int) -> pd.DataFrame:

        if df.empty or 'timestamp' not in df.columns:
            return df

        target_date = pd.to_datetime(date_str).date()

        return df[(df['timestamp'].dt.date == target_date) &
                  (df['timestamp'].dt.hour == hour)].copy()

    def load(self):
        self.treectrl.clear()
        self.expanded_items.clear()
        self.root = QtWidgets.QTreeWidgetItem(self.treectrl, ['Logs'])
        self.treectrl.addTopLevelItem(self.root)

        archives = self.get_archives()
        for archive_name, timestamp, archive_path in archives:
            child = QtWidgets.QTreeWidgetItem(
                self.root, [f'{archive_name} ({timestamp})'])

            child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                          {'type': 'archive', 'path': archive_path})

            QtWidgets.QTreeWidgetItem(child, ['Loading...'])

        logfiles = self.get_logfiles()
        self._curr_log = None

        for log_name, timestamp, log_path in logfiles:
            child = QtWidgets.QTreeWidgetItem(
                self.root, [f'{log_name} ({timestamp})'])

            child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                          {'type': 'file', 'path': log_path})

            if self._curr_log is None:
                self._curr_log = child

            QtWidgets.QTreeWidgetItem(child, ['Loading...'])

        self.root.setExpanded(True)

    @staticmethod
    def get_archives():
        res = []
        for i in range(Config.num_archives):
            archive_name = f'log_archive-{i + 1}'
            archive_path = os.path.join(Config.save_path, archive_name + '.zip')
            if not os.path.exists(archive_path):
                break

            creation_time = os.path.getctime(archive_path)
            readable_creation_time = time.asctime(time.localtime(creation_time))
            res.append((archive_name, readable_creation_time, archive_path))

        return res

    @staticmethod
    def get_logfiles():
        res = []
        for i in range(Config.num_logfiles):
            log_name = f'log-{i + 1}'
            log_path = os.path.join(Config.save_path, log_name + '.csv')
            if not os.path.exists(log_path):
                break

            mod_time = os.path.getmtime(log_path)
            readable_mod_time = time.asctime(time.localtime(mod_time))
            res.append((log_name, readable_mod_time, log_path))

        return res


# ---------------------------------------------------------------------------
# LogViewer — dock coordinator (same pattern as Phase 9 editors)
# ---------------------------------------------------------------------------

class LogViewer:
    """
    Represent a log viewer in :mod:`harness_designer.ui.log_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`LogViewer` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self.viewer = LogViewerPanel(mainframe, mainframe.logger)
        self.mainframe = mainframe

        self._dock = mainframe._make_dock(  # NOQA
            'Log Viewer', 'log_viewer',
            self.viewer, QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        self._dock.show()

    def Show(self, show=True):
        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def Refresh(self, *_, **__):
        self.viewer.update()

    def Destroy(self):
        self.viewer.Destroy()
        self._dock.deleteLater()
