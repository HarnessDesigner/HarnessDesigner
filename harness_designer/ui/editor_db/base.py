# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import time
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QTableView, QAbstractItemView, QHeaderView

from . import edit_dialog as _edit_dialog
from ... import config as _config
from ... import image as _image


def _inject_where_placeholder(query: str) -> str:
    """
    Insert a ``{where_clause}`` format placeholder into one of the
    EditorList page query templates, immediately before the close-paren
    that terminates the innermost SELECT.

    Every page template in this module has the shape::

        SELECT * FROM (
            SELECT Row_Number() OVER (ORDER BY ...) AS RowNum, *
            FROM (
                SELECT t.id, t.part_number, ...
                FROM <table> AS t
                LEFT JOIN ...
                LEFT JOIN ...
            )                              <-- innermost close
        ) WHERE RowNum BETWEEN ... AND ...;

    The injection point is right before that innermost close-paren so a
    WHERE clause is applied BEFORE pagination.
    """
    pos = query.find('WHERE RowNum BETWEEN')
    if pos == -1:
        return query

    outer_close = query.rfind(')', 0, pos)
    if outer_close == -1:
        return query

    inner_close = query.rfind(')', 0, outer_close)
    if inner_close == -1:
        return query

    return query[:inner_close] + '{where_clause}\n        ' + query[inner_close:]


class EditorDBConfig(metaclass=_config.ConfigDB):
    """Represent an editor database config in :mod:`harness_designer.ui.editor_db.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    pass


class ScrollTracker:
    """Represent a scroll tracker in :mod:`harness_designer.ui.editor_db.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    min_buffer = 10
    max_buffer = 500

    def __init__(self):
        """Initialise the :class:`ScrollTracker` instance.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.last_row = 0
        self.last_time = time.monotonic_ns()
        self._start_query = time.monotonic_ns()
        self._query_elapsed = 0

    def start_query(self):
        """Start the query.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._start_query = time.monotonic_ns()

    def stop_query(self):
        """Stop the query.

        UNKNOWN details are inferred from the callable name and signature.
        """
        now = time.monotonic_ns()
        self._query_elapsed += (now - self._start_query) * 1e-9

    def get_buffer_size(self, current_row):
        """Return the buffer size.

        UNKNOWN details are inferred from the callable name and signature.

        :param current_row: Value for ``current_row``.
        :type current_row: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        now = time.monotonic_ns()
        elapsed = (now - self.last_time) * 1e-9
        elapsed -= self._query_elapsed

        self._query_elapsed = 0

        if elapsed:
            velocity = abs(current_row - self.last_row) / elapsed
        else:
            velocity = 0

        self.last_row = current_row
        self.last_time = now

        res = int(min(self.max_buffer, max(self.min_buffer, velocity * 1.5) * 5))

        return res


class _EditorModel(QAbstractTableModel):
    """
    Qt model backing EditorList

    Feeds data on demand from the DB via
    the same row-cache and buffer strategy as the original wx.ListCtrl
    virtual implementation.
    """

    def __init__(self, editor_list):
        """Initialise the :class:`_EditorModel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param editor_list: Value for ``editor_list``.
        :type editor_list: UNKNOWN
        """
        super().__init__()
        self._list = editor_list

    def rowCount(self, parent=QModelIndex()):
        """Execute the row count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if parent.isValid():
            return 0

        return self._list._row_count  # NOQA

    def columnCount(self, parent=QModelIndex()):
        """Execute the column count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if parent.isValid():
            return 0

        # +1 for icon column
        return len(self._list.column_mapping) + 1

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Execute the header data operation.

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
            orientation != Qt.Orientation.Horizontal or
            role != Qt.ItemDataRole.DisplayRole
        ):
            return

        if section == 0:
            return ''

        col_key = section - 1
        if col_key not in self._list.column_mapping:
            return

        label = self._list.column_mapping[col_key][0]

        # Find this column in the sort stack and annotate the label.
        col_name = self._list.column_mapping[col_key][1]

        enumerated_data = enumerate(self._list.sort_columns, start=1)
        for priority, (sort_col, direction) in enumerated_data:
            if sort_col == col_name:
                # ASC = A at top, Z at bottom → triangle points down ▼
                # DESC = Z at top, A at bottom → triangle points up ▲
                triangle = '▼' if direction == 'ASC' else '▲'
                if len(self._list.sort_columns) > 1:
                    return f'{label} {triangle}({priority})'

                return f'{label} {triangle}'

        return label

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Execute the data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :param role: Value for ``role``.
        :type role: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if not index.isValid():
            return

        row_id = index.row()
        col_id = index.column()

        if role == Qt.ItemDataRole.DecorationRole and col_id == 0:
            return self._list._get_icon(row_id)  # NOQA

        if role == Qt.ItemDataRole.DisplayRole:
            if col_id == 0:
                return

            return self._list._get_cell_text(row_id, col_id)  # NOQA

        if role == Qt.ItemDataRole.TextAlignmentRole:
            col_key = col_id - 1
            if col_key in self._list.column_mapping:
                _, col_name = self._list.column_mapping[col_key][:2]
                if col_name == 'model3d_id':
                    return Qt.AlignmentFlag.AlignCenter

            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def invalidate_row(self, row_id):
        """Execute the invalidate row operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param row_id: Identifier for the row.
        :type row_id: UNKNOWN
        """
        self.dataChanged.emit(self.index(row_id, 0),
                              self.index(row_id, self.columnCount() - 1))

    def invalidate_icon(self, row_id):
        idx = self.index(row_id, 0)
        self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DecorationRole])

    def reset_all(self):
        """Execute the reset all operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.beginResetModel()
        self.endResetModel()


class EditorList(QTableView):
    """Represent an editor list in :mod:`harness_designer.ui.editor_db.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _no_image: QIcon = None
    _download_0: QIcon = None
    _download_1: QIcon = None
    _download_2: QIcon = None
    _download_3: QIcon = None
    _download_4: QIcon = None
    _download_5: QIcon = None
    _has_image = True
    _has_model_3d = True
    __table_name__ = ''
    __query__ = ''
    column_mapping = {}

    # kept for compat; not used in Qt path
    resize_registered = False

    # ------------------------------------------------------------------
    # Public interface expected by the rest of the codebase
    # ------------------------------------------------------------------

    def GetLabel(self):
        """Execute the get label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._label

    def GetSelection(self):
        """Execute the get selection operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        indexes = self.selectedIndexes()
        if not indexes:
            return None

        row = self.get_row(indexes[0].row())
        return row[1]

    def set_filter(self, where_clause: str = '', where_params=None):
        """Replace the active WHERE clause and refresh the list."""

        self._where_clause = where_clause or ''
        self._where_params = list(where_params or [])
        self.rows.clear()
        self.bitmap_indexes.clear()
        self.selected = None
        self._row_count = self.record_count
        self._model.reset_all()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    @property
    def record_count(self):
        """Return the record count.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        sql = f'SELECT COUNT(*) FROM {self.table_name} AS t'
        if self._where_clause:
            sql += f' WHERE {self._where_clause}'
            self.table.execute(sql + ';', self._where_params)
        else:
            self.table.execute(sql + ';')
        return self.table.fetchall()[0][0]

    # ------------------------------------------------------------------
    # Multi-column sort helpers
    # ------------------------------------------------------------------

    @property
    def sort_clause(self) -> str:
        """
        Build the ORDER BY expression from the current sort stack.

        ``sort_columns`` is a list of ``(column_name, 'ASC'|'DESC')``
        pairs in priority order.  When empty we fall back to ``id ASC``
        so the window function always has a deterministic ordering.
        """

        if not self.sort_columns:
            return 'id ASC'

        return ', '.join(
            f'{col} {direction}' for col, direction in self.sort_columns)

    def _column_is_unique(self, column_name: str) -> bool:
        """
        Return True when *column_name* is marked unique in
        ``column_mapping``.  The mapping entry must be a 3-tuple
        ``(label, db_column, unique)``; older 2-tuple entries are
        treated as non-unique.
        """

        for entry in self.column_mapping.values():
            if entry[1] != column_name:
                continue

            if len(entry) == 3:
                return entry[2]

        return False

    def _sorted_column_index(self, column_name: str) -> int:
        """
        Return the 0-based position of *column_name* in
        ``sort_columns``, or -1 when not present.
        """

        for i, (col, _dir) in enumerate(self.sort_columns):
            if col == column_name:
                return i

        return -1

    def _active_unique_column(self) -> str | None:
        """
        Return the column name if a unique column is currently the
        **last** entry in the sort stack (i.e. it would block further
        additions), otherwise None.
        """

        if not self.sort_columns:
            return None

        last_col, _ = self.sort_columns[-1]
        if self._column_is_unique(last_col):
            return last_col

        return None

    def _rebuild_sort_indicators(self):
        """
        Trigger a header repaint so every section re-fetches its label
        from ``_EditorModel.headerData``, which now embeds the arrow and
        priority number directly in the label text.

        Qt's native single-column sort indicator is not used (it can only
        mark one section at a time).  All visual feedback is carried by
        the label string itself, e.g. ``"Part Number ↓2"``.
        """

        self._model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0,
                                           self._model.columnCount() - 1)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def get_obj_id(self, row):
        """Return the obj ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self._where_clause:
            where_sql = f'WHERE {self._where_clause}'
        else:
            where_sql = ''

        sql = self._effective_query.format(sort_clause=self.sort_clause,
                                           row=row, start_row=row, end_row=row,
                                           where_clause=where_sql)

        if self._where_params:
            self.table.execute(sql, self._where_params)
        else:
            self.table.execute(sql)

        rows = self.table.fetchall()

        if rows:
            # rows[0][0] is RowNum; actual id is at index 1
            return rows[0][1]

    def get_row(self, row):
        """Return the row.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if row not in self.rows:
            self.buffer_size = self.scroll_tracker.get_buffer_size(row)
            start_row = max(0, row - self.buffer_size // 2)
            end_row = start_row + self.buffer_size
            self.get_rows(start_row, end_row)
            self.current_row = row
            self.needs_pruning = True

        return self.rows.get(row, None)

    def get_rows(self, start, stop):
        """Return the rows.

        UNKNOWN details are inferred from the callable name and signature.

        :param start: Value for ``start``.
        :type start: UNKNOWN
        :param stop: Value for ``stop``.
        :type stop: UNKNOWN
        """
        self.scroll_tracker.start_query()

        if self._where_clause:
            where_sql = f'WHERE {self._where_clause}'
        else:
            where_sql = ''

        sql = self._effective_query.format(sort_clause=self.sort_clause,
                                           start_row=start, end_row=stop,
                                           where_clause=where_sql)

        if self._where_params:
            self.table.execute(sql, self._where_params)
        else:
            self.table.execute(sql)

        rows = self.table.fetchall()

        if rows:
            self.rows.update({i + start: rows[i] for i in range(len(rows))})

        self.scroll_tracker.stop_query()

    def prune_cache(self, current_row, buffer_size):
        """Execute the prune cache operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param current_row: Value for ``current_row``.
        :type current_row: UNKNOWN
        :param buffer_size: Value for ``buffer_size``.
        :type buffer_size: UNKNOWN
        """
        keep_range = buffer_size * 2
        min_row = current_row - keep_range
        max_row = current_row + keep_range

        self.rows = {k: v for k, v in self.rows.items()
                     if min_row <= k <= max_row}

    # ------------------------------------------------------------------
    # Model data helpers (called from _EditorModel)
    # ------------------------------------------------------------------

    def _get_cell_text(self, row_id, col_id):
        """Return the cell text.

        UNKNOWN details are inferred from the callable name and signature.

        :param row_id: Identifier for the row.
        :type row_id: UNKNOWN
        :param col_id: Identifier for the col.
        :type col_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if row_id < 0:
            return ''

        row = self.get_row(row_id)

        if row is None:
            return ''

        if self._has_model_3d:
            col_name = self.column_lookup.get(col_id, '')
            if col_name == 'model3d_id':
                return '\u2714' if row[-2] is not None else ''

        # row[0] is RowNum (the window-function prefix);
        # actual data starts at row[1]. col_id is already offset by 1 for
        # the icon column, so net index is col_id.
        return str(row[col_id])

    def _update_progress(self, image, step):
        db_id = image.db_id
        if db_id not in self.downloading_images:
            return

        row_id = self.downloading_images[db_id][1]

        if step == -1:
            self.downloading_images[db_id][0] = EditorList._no_image
        else:
            self.downloading_images[db_id][0] = getattr(self, f'_download_{step}')

        QTimer.singleShot(0, lambda row=row_id: self._model.invalidate_icon(row))

    def _load_icon(self, image, pixmap: QPixmap):
        db_id = image.db_id
        pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)

        self.bitmap_indexes[db_id] = QIcon(pixmap)
        row_id = self.downloading_images[db_id][1]
        del self.downloading_images[db_id]

        QTimer.singleShot(0, lambda row=row_id: self._model.invalidate_icon(row))

        # from ... import app
        # app.CallAfter(self._model.invalidate_row, row_id)

    def _get_icon(self, row_id):
        """Return the icon.

        UNKNOWN details are inferred from the callable name and signature.

        :param row_id: Identifier for the row.
        :type row_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if row_id < 0:
            return None

        row = self.get_row(row_id)
        if row is None:
            return None

        # row[0] is RowNum; actual id is at index 1
        db_id = row[1]

        if db_id in self.downloading_images:
            return self.downloading_images[db_id][0]

        if db_id in self.bitmap_indexes:
            return self.bitmap_indexes[db_id]

        if not self._has_image:
            self.bitmap_indexes[db_id] = EditorList._no_image
            return EditorList._no_image

        image_id = row[-1]
        if image_id is None:
            self.bitmap_indexes[db_id] = EditorList._no_image
            return EditorList._no_image

        if image_id not in self.downloading_images:
            self.downloading_images[image_id] = [self._download_0, row_id]
            image = self.table.db.images_table[image_id]
            image.load(row[4], row[2], self._load_icon, self._update_progress)

        return self.downloading_images.get(image_id, [self.bitmap_indexes.get(image_id, EditorList._no_image)])[0]

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        """Execute the resize event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        super().resizeEvent(event)

        def _do():
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.
            """
            count = self.rowsPerPage()
            if count > 0:
                ScrollTracker.min_buffer = (count + 1) * 2
                ScrollTracker.max_buffer = (count + 1) * 2 * 60

        QTimer.singleShot(0, _do)

    def rowsPerPage(self):
        """Execute the rows per page operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self._row_height > 0:
            row_h = self._row_height
        else:
            row_h = 68

        return max(1, self.viewport().height() // row_h)

    def contextMenuEvent(self, event):
        """Execute the context menu event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        # stub; subclasses may override
        pass

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_selection_changed(self, selected, deselected):
        """Handle the selection changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        :param deselected: Value for ``deselected``.
        :type deselected: UNKNOWN
        """
        indexes = selected.indexes()

        if indexes:
            self.selected = indexes[0].row()
        else:
            self.selected = None

    def _on_activated(self, index):
        """Handle the activated event.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        """
        row_id = index.row()
        self.selected = row_id
        db_id = self.get_obj_id(row_id)
        obj = self.table[db_id]

        dlg = _edit_dialog.EditDialog(
            self.mainframe, 'Edit ' + self._label, obj)

        dlg.exec()

        if row_id in self.rows:
            del self.rows[row_id]

        self._model.invalidate_row(row_id)

    def _on_header_clicked(self, logical_index):
        """Handle the header clicked event.

        UNKNOWN details are inferred from the callable name and signature.

        :param logical_index: Value for ``logical_index``.
        :type logical_index: UNKNOWN
        """
        if logical_index not in self.column_lookup:
            return

        col_name = self.column_lookup[logical_index]
        pos = self._sorted_column_index(col_name)

        if pos == -1:
            # Column not currently sorted — try to append it.
            # Block if the last sorted column is unique (it already
            # produces a deterministic order on its own).
            blocking = self._active_unique_column()
            if blocking is not None:
                # Silently ignore; callers may connect a status-bar
                # message here if desired.
                return

            # First click → ASC
            self.sort_columns.append((col_name, 'ASC'))

        else:
            current_dir = self.sort_columns[pos][1]
            if current_dir == 'ASC':
                # Second click → DESC
                self.sort_columns[pos] = (col_name, 'DESC')
            else:
                # Third click → remove from sort stack entirely.
                # Re-number remaining entries (list order is preserved).
                self.sort_columns.pop(pos)

        self._rebuild_sort_indicators()
        self.rows.clear()
        self.selected = None
        self._model.reset_all()

    def _on_idle(self):
        """Handle the idle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self.needs_pruning:
            self.prune_cache(self.current_row, self.buffer_size)
            self.needs_pruning = False

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, parent, mainframe, label, table):
        """Initialise the :class:`EditorList` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param table: Value for ``table``.
        :type table: UNKNOWN
        """
        self._where_clause = ''
        self._where_params: list = []
        self._effective_query = _inject_where_placeholder(self.__query__)

        self._label = label
        self.table_name = table.__table_name__
        self.table = table
        self.visible_row = 0
        self.scroll_tracker = ScrollTracker()
        self.bitmap_indexes = {}
        self.rows = {}
        self.selected = None
        self.mainframe = mainframe
        self.downloading_images = {}

        # [(col_name, 'ASC'|'DESC'), ...]
        self.sort_columns: list[tuple[str, str]] = []

        self.needs_pruning = False
        self.current_row = 0
        self._row_height = 68

        super().__init__(parent)

        self._row_count = self.record_count
        self._model = _EditorModel(self)
        self.setModel(self._model)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # manual sort via header click
        self.setSortingEnabled(False)

        self.setIconSize(QSize(64, 64))
        self.verticalHeader().setDefaultSectionSize(68)
        self.verticalHeader().hide()

        header = self.horizontalHeader()
        header.setSectionsClickable(True)

        # arrows embedded in label text instead
        header.setSortIndicatorShown(False)

        self.column_lookup = {}

        # icon column
        self.setColumnWidth(0, 72)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)

        fm = self.fontMetrics()
        for i in sorted(self.column_mapping.keys()):
            label_text, column_name = self.column_mapping[i][:2]

            # offset for icon column
            logical = i + 1
            self.column_lookup[logical] = column_name

            if column_name == 'model3d_id':
                header.setSectionResizeMode(logical, QHeaderView.ResizeMode.Fixed)
            else:
                header.setSectionResizeMode(logical, QHeaderView.ResizeMode.Interactive)

            offset = 100 if label_text == 'Description' else 25
            self.setColumnWidth(
                logical, fm.horizontalAdvance(label_text) + offset)

        self.max_column_count = len(self.column_mapping)
        self.buffer_size = self.rowsPerPage()

        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.activated.connect(self._on_activated)
        header.sectionClicked.connect(self._on_header_clicked)

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(200)
        self._idle_timer.timeout.connect(self._on_idle)
        self._idle_timer.start()

        if EditorList._no_image is None:
            img = _image.images.no_image.resize(64, 64)
            EditorList._no_image = QIcon(img.pixmap)

            img = _image.images.download_0.resize(64, 64)
            EditorList._download_0 = QIcon(img.pixmap)

            img = _image.images.download_1.resize(64, 64)
            EditorList._download_1 = QIcon(img.pixmap)

            img = _image.images.download_2.resize(64, 64)
            EditorList._download_2 = QIcon(img.pixmap)

            img = _image.images.download_3.resize(64, 64)
            EditorList._download_3 = QIcon(img.pixmap)

            img = _image.images.download_4.resize(64, 64)
            EditorList._download_4 = QIcon(img.pixmap)

            img = _image.images.download_5.resize(64, 64)
            EditorList._download_5 = QIcon(img.pixmap)

    # ------------------------------------------------------------------
    # Compatibility shims
    # ------------------------------------------------------------------

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self._model.reset_all()
        self.viewport().update()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._idle_timer.stop()
        self.deleteLater()
