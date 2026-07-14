# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Optional, List

import threading
import os
import pandas as pd

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from harness_designer import app as _app
from ...logger.log_handler import RotationEvent

if TYPE_CHECKING:
    from ... import logger as _logger
    from .. import mainframe as _mainframe


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

        view = opt.widget
        if view is not None and hasattr(view, '_ensure_row_height_for_index'):
            view._ensure_row_height_for_index(index)

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

    # Column order is fixed and matches self._data's column order exactly
    # (build_message(), _create_logfile() and the CSV header all agree on
    # it), so index.column() can be used as a DataFrame column position
    # directly instead of going through a name.
    _HEADERS = ['Timestamp', 'Level', 'Message']
    _COLS = ['timestamp', 'level', 'message']
    _LEVEL_COL = _COLS.index('level')

    def __init__(self, parent=None):
        """
        Initialise the :class:`_LogModel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        super().__init__(parent)
        self._data = pd.DataFrame(columns=['timestamp', 'level', 'message'])

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
        row = index.row()
        if not index.isValid() or row >= len(self._data):
            return None

        # .iat is pandas' positional scalar accessor - row/column indexes
        # straight in, no intermediate Series and no name lookup. data()
        # runs once per visible cell on every repaint/scroll, so avoiding
        # that per-call Series allocation actually matters here.
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return str(self._data.iat[row, index.column()])

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            level = str(self._data.iat[row, self._LEVEL_COL]).upper()
            for key, colour in _LEVEL_COLOURS.items():
                if key in level:
                    return colour

        return None

    def set_data(self, df: pd.DataFrame):
        """
        Set the data.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        """

        self.beginResetModel()

        # No copy: nothing here or downstream ever mutates a column on this
        # DataFrame in place, and every source (log_handler.write(),
        # read_log(), the filter helpers below) already hands over a
        # correctly-typed, independently-owned DataFrame.
        if not df.empty:
            self._data = df
        else:
            self._data = pd.DataFrame(columns=['timestamp', 'level', 'message'])

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

        first = len(self._data)
        last = first + len(df) - 1
        self.beginInsertRows(QtCore.QModelIndex(), first, last)
        self._data = pd.concat([self._data, df], ignore_index=True)
        self.endInsertRows()


class VirtualLogListCtrl(QtWidgets.QTableView):
    """Replaces wx.ListCtrl (LC_REPORT | LC_VIRTUAL | LC_SINGLE_SEL)."""

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

        self._default_row_height = max(
            self.fontMetrics().height() + 8,
            self.verticalHeader().defaultSectionSize()
        )
        self.verticalHeader().setDefaultSectionSize(self._default_row_height)
        self._multiline_height_cache: dict[int, int] = {}
        self._height_update_guard = False

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

    def _ensure_row_height_for_index(self, index: QtCore.QModelIndex):
        if self._height_update_guard or not index.isValid():
            return

        row = index.row()
        if row < 0:
            return

        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not text or '\n' not in text:
            return

        height = self._multiline_height_cache.get(row)
        if height is None:
            height = max(self._default_row_height, self._row_height_for_text(text))
            self._multiline_height_cache[row] = height

        if self.rowHeight(row) == height:
            return

        self._height_update_guard = True
        try:
            self.setRowHeight(row, height)
        finally:
            self._height_update_guard = False

    def is_at_bottom(self) -> bool:
        """Whether the view is currently scrolled to its last row."""
        scrollbar = self.verticalScrollBar()
        return scrollbar.value() >= scrollbar.maximum()

    def AppendData(self, data: pd.DataFrame):
        """Append rows to the model, keeping the view scrolled to the
        bottom if it already was there. Caller must already be on the main
        thread - LogViewerPanel.new_data() only reaches here via CallAfter."""

        if self._is_destroyed:
            return

        was_at_bottom = self.is_at_bottom()
        self._model.append_data(data)
        self.viewport().update()

        if was_at_bottom:
            self.scrollToBottom()

    def SetData(self, df: pd.DataFrame):
        """
        Execute the set data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param df: Value for ``df``.
        :type df: :class:`pd.DataFrame`
        """

        self._multiline_height_cache.clear()
        self._model.set_data(df)
        self.viewport().update()

    def _on_section_resized(self, logical_index: int,
                            _old_size: int, _new_size: int):

        # Row height depends only on explicit newline count, not column width.
        return


# ---------------------------------------------------------------------------
# LogViewerPanel — QSplitter replacing wx.SplitterWindow
# ---------------------------------------------------------------------------

class ViewerPanel(QtWidgets.QSplitter):
    """
    Represent a log viewer panel in :mod:`harness_designer.ui.log_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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
        self._is_destroyed = False
        self.current_data = pd.DataFrame()
        self.expanded_items: set = set()

        # The full, ever-growing content of the currently-active (still
        # being written to) log file. Kept up to date by new_data() below,
        # which only ever runs on this thread (see the bind() call further
        # down), so nothing needs to lock access to it. Selecting the
        # active file's tree node reads from here instead of re-parsing it
        # off disk, and avoids re-reading a file the writer thread might
        # be appending to at that exact moment.
        self._active_buffer = pd.DataFrame(columns=['timestamp', 'level', 'message'])
        # True only when the tree's unfiltered active-file node is what's
        # currently selected - date/hour-filtered views and other files
        # are snapshots and don't live-update.
        self._viewing_active = False

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

        # new_data() below is always invoked via CallAfter (from write()'s
        # worker thread or from this thread on rotation), so it always
        # runs on the main thread regardless of caller.
        logger.log_handler.bind(self.new_data)

        def _do():
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.WaitCursor)

            try:
                self.load()
                self._load_current_log_initial()
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

        # Defers _do() until the event loop regains control - this call is
        # already on the main thread (construction always is), so it's
        # CallLater's job, not CallAfter's.
        _app.CallLater(_do)

    def Destroy(self):
        """
        Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """

        self._is_destroyed = True
        self.log_list.Destroy()
        self.deleteLater()

    def _clear_active_buffer(self):
        """Empty the active-file buffer - called when a new, empty log
        file starts, so nothing from the rotated-out file lingers in it."""
        self._active_buffer = pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _extend_active_buffer(self, df: pd.DataFrame):
        """Add rows to the active-file buffer.

        Used both for the initial full read of the active file at startup
        and for individual live entries as they're written - a concat onto
        the (empty, at startup) buffer handles a thousand-row DataFrame the
        same way it handles a single-row one, so there's no separate
        "initial load" code path.
        """
        self._active_buffer = pd.concat(
            [self._active_buffer, df], ignore_index=True)

    def _load_current_log_initial(self):
        """
        Load the current log initial.

        UNKNOWN details are inferred from the callable name and signature.
        """

        try:
            current_log_path = self.logger.log_handler.get_current_log_path()
            if current_log_path and os.path.exists(current_log_path):
                df = self._read_log_file(current_log_path)
                self._extend_active_buffer(df)
                self._viewing_active = True
                self.current_data = self._active_buffer
                self.log_list.SetData(self._active_buffer)

        except Exception as e:
            self.logger.error(f"Failed to load initial log: {e}")

    def new_data(self, data=None):
        """Called via CallAfter, always on the main thread: `data` is a
        DataFrame for a new entry, or a RotationEvent for a rotation - see
        LogHandler.bind()."""

        if self._is_destroyed:
            return

        if isinstance(data, RotationEvent):
            self._handle_rotation(data)
        else:
            self._handle_new_row(data)

    def _handle_new_row(self, df: pd.DataFrame):
        """A single entry was written to the still-open active file."""
        self._extend_active_buffer(df)
        if self._viewing_active:
            # AppendData scrolls the new row into view only if the view
            # was already scrolled to the bottom.
            self.log_list.AppendData(df)

    def _handle_rotation(self, event: RotationEvent):
        """The active file hit its size limit and rotated to a new one.

        `event.closed_path` is where the old active file's content now
        lives on its own; if that same rotation also archived it (and
        other closed files), `event.archive_path` is set and
        `closed_path` only exists as a member of that archive now -
        needed either way to keep following it correctly if the user was
        reading its history rather than watching its tail.
        """
        # Was the tail of the file that just rotated out what was on
        # screen? Check before clearing anything - AppendData() for the
        # entry that triggered this rotation has already run by this
        # point (write() notifies before checking the size), so this
        # reflects "were they following the file that just closed."
        was_following_tail = self._viewing_active and self.log_list.is_at_bottom()
        was_viewing_active = self._viewing_active

        self._clear_active_buffer()
        self.load()

        if was_following_tail:
            # Keep following: switch to the new (currently empty) active
            # file. _viewing_active stays True.
            active_path = self.logger.log_handler.get_current_log_path()
            self._select_tree_item_for_path(active_path)
            self.current_data = self._active_buffer
            self.log_list.SetData(self._active_buffer)
        elif was_viewing_active:
            # Was reading the file that just rotated out, scrolled away
            # from its tail - leave the displayed content exactly as-is,
            # just point the tree selection at wherever it lives now
            # instead of the now-stale "pending" one load() just dropped.
            self._viewing_active = False
            if event.archive_path is not None:
                self._select_archived_file(
                    event.archive_path, os.path.basename(event.closed_path))
            else:
                self._select_tree_item_for_path(event.closed_path)
        # else: viewing something else entirely (another file, a filtered
        # view, an archive) - the active file rotating doesn't concern
        # this view beyond the tree refresh above.

    def _select_tree_item_for_path(self, path: str) -> bool:
        """Select the tree item for `path` without triggering the normal
        tree-selection-changed reload - _handle_rotation() above already
        decided what the displayed data should be."""
        for i in range(self.root.childCount()):
            child = self.root.child(i)
            item_data = child.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if item_data and item_data.get('type') == 'file' \
                    and item_data.get('path') == path:
                self.treectrl.blockSignals(True)
                try:
                    self.treectrl.setCurrentItem(child)
                finally:
                    self.treectrl.blockSignals(False)
                return True
        return False

    def _select_archived_file(self, archive_path: str, filename: str) -> bool:
        """Find the archive's (just-created, so not yet expanded) tree
        item, load its member list, and select `filename` inside it -
        same "don't trigger the normal reload" reasoning as
        _select_tree_item_for_path()."""
        for i in range(self.root.childCount()):
            archive_item = self.root.child(i)
            item_data = archive_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not item_data or item_data.get('type') != 'archive' \
                    or item_data.get('path') != archive_path:
                continue

            self._load_archive_files(archive_item, archive_path, id(archive_item))

            for j in range(archive_item.childCount()):
                file_item = archive_item.child(j)
                file_data = file_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if file_data and file_data.get('filename') == filename:
                    self.treectrl.blockSignals(True)
                    try:
                        archive_item.setExpanded(True)
                        self.treectrl.setCurrentItem(file_item)
                    finally:
                        self.treectrl.blockSignals(False)
                    return True
            return False

        return False

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
        is_active_file = (
            item_type == 'file'
            and data['path'] == self.logger.log_handler.get_current_log_path())
        self._viewing_active = is_active_file

        if is_active_file:
            # Already have the full, up-to-date content in memory via
            # new_data() - no need to re-read it off disk (and no risk of
            # reading it while the writer thread is mid-append).
            self.current_data = self._active_buffer
            self.log_list.SetData(self._active_buffer)
        elif item_type == 'file':
            self._load_log_data(data['path'])
        elif item_type == 'date':
            self._load_log_data(data['file'], date_filter=data['date'])
        elif item_type == 'hour':
            self._load_log_data(
                data['file'], date_filter=data['date'], hour_filter=data['hour'])
        elif item_type == 'archive_file':
            self._load_archive_file(data['archive_path'], data['filename'])
        elif item_type == 'archive_date':
            self._load_archive_file(
                data['archive_path'], data['filename'], date_filter=data['date'])
        elif item_type == 'archive_hour':
            self._load_archive_file(
                data['archive_path'], data['filename'],
                date_filter=data['date'], hour_filter=data['hour'])

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
                item, data['archive_path'], data['filename'], item_id)
        elif item_type == 'archive_date':
            self._load_hours_for_archive_date(
                item, data['archive_path'], data['filename'], data['date'], item_id)

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
            _app.CallAfter(self._populate_dates, file_item, log_path, dates, item_id)

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
            _app.CallAfter(self._populate_hours,
                           date_item, log_path, date_str, hours, item_id, False)

        threading.Thread(target=load_hours, daemon=True).start()

    def _populate_hours(self, parent_item: QtWidgets.QTreeWidgetItem,
                        log_path: Optional[str], date_str: str,
                        hours: List[int], item_id: int, is_archive: bool,
                        archive_path=None, filename=None):
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
                                   'archive_path': archive_path, 'filename': filename,
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
            names = self.logger.log_handler.list_archive_contents(archive_path)
            self.expanded_items.add(item_id)
            for name in names:
                if name.endswith('.log'):
                    child = QtWidgets.QTreeWidgetItem(archive_item, [name])
                    child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                                  {'type': 'archive_file',
                                   'archive_path': archive_path, 'filename': name})

                    QtWidgets.QTreeWidgetItem(child, ['Loading...'])
        except Exception as e:
            self.logger.error(f"Failed to load archive {archive_path}: {e}")
            QtWidgets.QTreeWidgetItem(archive_item, ['(Error loading archive)'])

    def _load_dates_for_archive_file(self, file_item: QtWidgets.QTreeWidgetItem,
                                     archive_path: str, filename: str, item_id: int):
        """Load the dates for archive file."""

        file_item.takeChildren()
        QtWidgets.QTreeWidgetItem(file_item, ['Loading dates...'])

        def load_dates():
            dates = self._get_dates_in_archive(archive_path, filename)

            _app.CallAfter(self._populate_archive_dates,
                           file_item, archive_path, filename, dates, item_id)

        threading.Thread(target=load_dates, daemon=True).start()

    def _populate_archive_dates(self, parent_item: QtWidgets.QTreeWidgetItem,
                                archive_path: str, filename: str,
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
                              {'type': 'archive_date', 'archive_path': archive_path,
                               'filename': filename, 'date': date_str})

            QtWidgets.QTreeWidgetItem(date_item, ['Loading...'])

    def _load_hours_for_archive_date(self, date_item: QtWidgets.QTreeWidgetItem,
                                     archive_path: str, filename: str,
                                     date_str: str, item_id: int):
        """Load the hours for archive date."""

        date_item.takeChildren()
        QtWidgets.QTreeWidgetItem(date_item, ['Loading hours...'])

        def load_hours():
            hours = self._get_hours_in_archive_date(archive_path, filename, date_str)

            _app.CallAfter(self._populate_hours,
                           date_item, None, date_str, hours, item_id,
                           True, archive_path, filename)

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

            _app.CallAfter(self._display_log_data, df)

        threading.Thread(target=load_data, daemon=True).start()

    def _load_archive_file(self, archive_path: str, filename: str,
                           date_filter: Optional[str] = None,
                           hour_filter: Optional[int] = None):
        """Load the archive file."""

        def load_data():
            df = self._read_archive_file(archive_path, filename)
            if date_filter and hour_filter is not None:
                df = self._filter_by_date_and_hour(df, date_filter, hour_filter)
            elif date_filter:
                df = self._filter_by_date(df, date_filter)

            _app.CallAfter(self._display_log_data, df)

        threading.Thread(target=load_data, daemon=True).start()

    def _display_log_data(self, df: pd.DataFrame):
        """Execute the display log data operation."""

        self.current_data = df
        self.log_list.SetData(df)

    # ------------------------------------------------------------------
    # File / data helpers (I/O delegated to LogHandler; this layer just
    # adds the UI-facing error handling and empty-DataFrame fallback).
    # ------------------------------------------------------------------

    def _read_log_file(self, log_path: str) -> pd.DataFrame:
        """Execute the read log file operation."""

        try:
            return self.logger.log_handler.read_log(log_path)
        except Exception as e:
            self.logger.error(f"Failed to read log file {log_path}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _read_archive_file(self, archive_path: str, filename: str) -> pd.DataFrame:
        """Execute the read archive file operation."""

        try:
            return self.logger.log_handler.read_archived_log(archive_path, filename)
        except Exception as e:
            self.logger.error(f"Failed to read archive file {filename}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _get_dates_in_log(self, log_path: str) -> List[str]:
        df = self._read_log_file(log_path)
        if df.empty:
            return []

        dates = df['timestamp'].dt.date.unique()
        return sorted([str(d) for d in dates], reverse=True)

    def _get_dates_in_archive(self, archive_path: str, filename: str) -> List[str]:
        df = self._read_archive_file(archive_path, filename)
        if df.empty:
            return []

        dates = df['timestamp'].dt.date.unique()
        return sorted([str(d) for d in dates], reverse=True)

    def _get_hours_in_date(self, log_path: str, date_str: str) -> List[int]:
        df = self._read_log_file(log_path)
        if df.empty:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]
        if df_date.empty:
            return []

        return sorted(df_date['timestamp'].dt.hour.unique().tolist())

    def _get_hours_in_archive_date(self, archive_path: str, filename: str,
                                   date_str: str) -> List[int]:

        df = self._read_archive_file(archive_path, filename)
        if df.empty:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]
        if df_date.empty:
            return []

        return sorted(df_date['timestamp'].dt.hour.unique().tolist())

    @staticmethod
    def _filter_by_date(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        if df.empty:
            return df

        target_date = pd.to_datetime(date_str).date()
        return df[df['timestamp'].dt.date == target_date].copy()

    @staticmethod
    def _filter_by_date_and_hour(df: pd.DataFrame, date_str: str,
                                 hour: int) -> pd.DataFrame:

        if df.empty:
            return df

        target_date = pd.to_datetime(date_str).date()
        return df[(df['timestamp'].dt.date == target_date) &
                  (df['timestamp'].dt.hour == hour)].copy()

    def load(self):
        self.treectrl.clear()
        self.expanded_items.clear()
        self.root = QtWidgets.QTreeWidgetItem(self.treectrl, ['Logs'])
        self.treectrl.addTopLevelItem(self.root)

        # File/archive names already encode the date range they cover, so
        # that's used directly as the tree label instead of file metadata.
        for archive_path in self.get_archives():
            label = os.path.splitext(os.path.basename(archive_path))[0]
            child = QtWidgets.QTreeWidgetItem(self.root, [label])

            child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                          {'type': 'archive', 'path': archive_path})

            QtWidgets.QTreeWidgetItem(child, ['Loading...'])

        for log_path in self.get_logfiles():
            label = os.path.splitext(os.path.basename(log_path))[0]
            child = QtWidgets.QTreeWidgetItem(self.root, [label])

            child.setData(0, QtCore.Qt.ItemDataRole.UserRole,
                          {'type': 'file', 'path': log_path})

            QtWidgets.QTreeWidgetItem(child, ['Loading...'])

        self.root.setExpanded(True)

    def get_archives(self):
        """Return archive paths, newest first."""
        return list(reversed(self.logger.log_handler.list_archives()))

    def get_logfiles(self):
        """Return current (non-archived) log file paths, newest first."""
        return list(reversed(self.logger.log_handler.list_logfiles()))

