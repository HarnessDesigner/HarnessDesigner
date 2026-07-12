# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import time
from collections import deque

from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex, QPoint,
                            QTimer, QSize, Signal)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (QTableView, QAbstractItemView, QHeaderView,
                               QApplication, QWidget, QLabel, QLineEdit,
                               QPushButton, QHBoxLayout)

from . import edit_dialog as _edit_dialog
from ... import config as _config
from ... import image as _image


class _HeaderSearchPopup(QWidget):
    """Small popup shown on right-clicking a column header, letting the
    user type a per-column search value.

    Uses the ``Qt.Popup`` window flag, which Qt closes automatically on
    any click outside the widget or loss of focus -- "click outside
    cancels" needs no extra event handling because of it.
    """

    def __init__(self, parent, initial_text: str, on_ok):
        """Initialise the :class:`_HeaderSearchPopup` instance.

        :param parent: Parent widget the popup is anchored near.
        :type parent: QWidget
        :param initial_text: Current search text for the column, if any.
        :type initial_text: str
        :param on_ok: Called with the entered text when OK is pressed
            (Enter in the field, or the button).
        :type on_ok: Callable[[str], None]
        """
        super().__init__(parent, Qt.WindowType.Popup)
        self._on_ok = on_ok

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)

        lay.addWidget(QLabel('Search:', self))

        self._edit = QLineEdit(self)
        self._edit.setText(initial_text)
        self._edit.setMinimumWidth(160)
        self._edit.returnPressed.connect(self._accept)  # NOQA
        lay.addWidget(self._edit)

        ok_btn = QPushButton('OK', self)
        ok_btn.clicked.connect(self._accept)  # NOQA
        lay.addWidget(ok_btn)

        self._edit.selectAll()

    def showEvent(self, event):
        """Grab focus into the text field once the popup is actually shown.

        :param event: Show event.
        :type event: QtGui.QShowEvent
        """
        super().showEvent(event)
        self._edit.setFocus()

    def _accept(self):
        """Report the entered text and close the popup."""
        self._on_ok(self._edit.text())
        self.close()


class EditorDBConfig(metaclass=_config.ConfigDB):
    """Represent an editor database config in :mod:`harness_designer.ui.editor_db.base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # Learned average gap (ms) between the two presses of the user's
    # double clicks. 0 means nothing has been learned yet.
    double_click_average = 0


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
        col_name = self._list.column_mapping[col_key][1]['alias']

        search_text = self._list._header_search.get(col_name)  # NOQA
        if search_text:
            label = f'{label} ["{search_text}"]'

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

        try:
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
                    col_name = self._list.column_mapping[col_key][1]['alias']
                    if col_name == 'model3d_id':
                        return Qt.AlignmentFlag.AlignCenter

                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        except:
            import traceback
            traceback.print_exc()
            raise

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

    # Emitted with the visible row index whenever a row becomes selected,
    # including when the selection moves from one row to another.
    itemSelected = Signal(int)

    # Emitted only when the state changes from a row being selected to
    # nothing being selected.
    itemUnselected = Signal()

    # Rolling sample of measured double-click gaps (ms), shared by every
    # list so all pages contribute to the same learned average.
    _dc_samples: deque = deque(maxlen=5)

    # The deselect wait is the learned average plus headroom for the
    # user's slower-than-average double clicks, never below the floor
    # and never above the OS interval.
    _DESELECT_MARGIN = 1.5
    _DESELECT_MIN_MS = 150

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
        self._clear_selection_state()
        self._row_count = self.record_count
        self._model.reset_all()

    def _header_search_predicate(self, col: str, text: str) -> tuple[str, str]:
        """Build a self-contained ``LIKE`` predicate for one header-search
        column.

        Must not reference a JOINed table's alias directly (e.g.
        ``mfg_name.name``) the way the paginated results query's own
        SELECT can -- :attr:`record_count`'s ``COUNT(*)`` query has no
        JOINs in scope, only ``t``, so an FK column is matched via a
        self-contained subquery instead (same technique already used by
        the search dialog's FK filter panels).

        :param col: Column alias, as used in ``column_mapping``.
        :type col: str
        :param text: Raw search text (unescaped, becomes a bound param).
        :type text: str
        :returns: The SQL fragment and its single bound parameter.
        :rtype: tuple[str, str]
        """
        for entry in self.column_mapping.values():
            info = entry[1]
            if info['alias'] != col:
                continue

            if 'ref_table' in info:
                sql = (f't.{info["field_name"]} IN ('
                       f'SELECT id FROM {info["ref_table"]} '
                       f'WHERE {info["ref_field"]} LIKE ?)')
            else:
                sql = f't.{info["field_name"]} LIKE ?'

            return sql, f'%{text}%'

        return f't.{col} LIKE ?', f'%{text}%'

    def _combined_where(self) -> tuple[str, list]:
        """Combine the externally-set filter (e.g. the search dialog's
        keyword box and filter panels) with any active per-column header
        searches, AND'd together.

        :returns: The combined WHERE body (no ``WHERE`` keyword) and its
            bound parameters, in the same order.
        :rtype: tuple[str, list]
        """
        clauses = []
        params: list = []

        if self._where_clause:
            clauses.append(f'({self._where_clause})')
            params.extend(self._where_params)

        for col, text in self._header_search.items():
            sql, param = self._header_search_predicate(col, text)
            clauses.append(sql)
            params.append(param)

        return " AND ".join(clauses), params

    def _on_header_context_menu(self, pos: QPoint) -> None:
        """Show the per-column search popup for the header section that
        was right-clicked.

        :param pos: Click position, in the header's own coordinates.
        :type pos: QPoint
        """
        header = self.horizontalHeader()
        logical = header.logicalIndexAt(pos)

        if logical <= 0 or logical not in self.column_lookup:
            return

        col_name = self.column_lookup[logical]
        current = self._header_search.get(col_name, '')

        popup = _HeaderSearchPopup(
            self, current,
            lambda text, col=col_name: self._apply_header_search(col, text))

        section_pos = header.sectionViewportPosition(logical)
        anchor = header.mapToGlobal(QPoint(section_pos, header.height()))
        popup.move(anchor)
        popup.show()

    def _apply_header_search(self, col: str, text: str) -> None:
        """Set (or clear, if ``text`` is blank) one column's header search
        and refresh the list.

        :param col: Column alias whose search value changed.
        :type col: str
        :param text: New search text; blank clears the search.
        :type text: str
        """
        text = text.strip()

        if text:
            self._header_search[col] = text
        else:
            self._header_search.pop(col, None)

        self.rows.clear()
        self.bitmap_indexes.clear()
        self._clear_selection_state()
        self._row_count = self.record_count
        self._model.reset_all()
        self._rebuild_sort_indicators()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _build_query(self) -> str:
        """Build the paginated SELECT template from ``column_mapping``.

        Called once at construction.  The static parts (column list, JOIN
        clauses, table name) are baked in; the dynamic parts are left as
        ``str.format`` placeholders: ``{sort_clause}``, ``{start_row}``,
        ``{end_row}``, and ``{where_clause}``.
        """
        select_cols = []
        joins = []

        for entry in self.column_mapping.values():
            info = entry[1]
            alias = info['alias']
            field_name = info['field_name']

            if 'ref_table' in info:
                select_cols.append(f'{alias}.{info["ref_field"]} AS {alias}')
                joins.append(
                    f'LEFT JOIN {info["ref_table"]} AS {alias}'
                    f' ON {alias}.id = t.{field_name}'
                )
            else:
                select_cols.append(f't.{field_name} AS {alias}')

        if self._has_image:
            select_cols.append('t.image_id AS image_id')

        query = (f'SELECT * FROM (SELECT ROW_NUMBER() OVER '
                 f'(ORDER BY {{sort_clause}}) AS RowNum, * '
                 f'FROM (SELECT {", ".join(select_cols)} '
                 f'FROM {self.__table_name__} AS t '
                 f'{" ".join(joins)} {{where_clause}}) AS base) AS paged '
                 f'WHERE RowNum BETWEEN {{start_row}} AND {{end_row}};')

        return query

    @property
    def record_count(self):
        """Return the record count.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        where_body, params = self._combined_where()

        sql = f'SELECT COUNT(*) FROM {self.table_name} AS t'
        if where_body:
            sql += f' WHERE {where_body}'
            self.table.execute(sql + ';', params)
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
            if entry[1]['alias'] != column_name:
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
        where_body, params = self._combined_where()
        where_sql = f'WHERE {where_body}' if where_body else ''

        sql = self._effective_query.format(sort_clause=self.sort_clause,
                                           row=row, start_row=row, end_row=row,
                                           where_clause=where_sql)

        if params:
            self.table.execute(sql, params)
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

        where_body, params = self._combined_where()
        where_sql = f'WHERE {where_body}' if where_body else ''

        sql = self._effective_query.format(sort_clause=self.sort_clause,
                                           start_row=start, end_row=stop,
                                           where_clause=where_sql)

        if params:
            self.table.execute(sql, params)
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
            try:
                image = self.table.db.images_table[image_id]
            except AttributeError:
                # database has been closed
                return EditorList._no_image

            self.downloading_images[image_id] = [self._download_0, row_id]
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

    def mousePressEvent(self, event):
        """Handle mouse presses, adding deselect behaviour.

        A left click on the row that is already selected, or on the empty
        area below the rows, clears the selection.

        A double click is delivered by Qt as a normal press first, so a
        click on the selected row only schedules the deselect; it is
        carried out after the double-click interval elapses with no second
        click. :meth:`mouseDoubleClickEvent` cancels it so a double click
        keeps the row selected and activates it.

        :param event: Mouse event.
        :type event: :class:`QtGui.QMouseEvent`
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._deselect_timer.stop()
            self._pending_deselect_row = None
            self._last_press_ns = time.monotonic_ns()

            index = self.indexAt(event.position().toPoint())

            if not index.isValid():
                self.clearSelection()
                event.accept()
                return

            if self.selected is not None and index.row() == self.selected:
                self._pending_deselect_row = index.row()
                self._deselect_timer.start(self._deselect_wait_ms())
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double clicks, cancelling any pending deselect.

        Double-clicking an already-selected row keeps it selected and lets
        the default activation behaviour run. The gap between the two
        presses is also sampled to refine the learned double-click speed.

        :param event: Mouse event.
        :type event: :class:`QtGui.QMouseEvent`
        """
        if (
            event.button() == Qt.MouseButton.LeftButton and
            self._last_press_ns is not None
        ):
            gap_ms = (time.monotonic_ns() - self._last_press_ns) * 1e-6
            if 0 < gap_ms <= QApplication.doubleClickInterval():
                self._record_double_click_gap(gap_ms)

        self._deselect_timer.stop()
        self._pending_deselect_row = None

        super().mouseDoubleClickEvent(event)

    @classmethod
    def _record_double_click_gap(cls, gap_ms):
        """Fold a measured double-click gap into the learned average.

        The newest gap joins a rolling window of 5 samples. The highest
        and lowest samples are discarded, the previously stored average
        (when one exists) is added back in, and the mean of what remains
        becomes the new persisted average.

        :param gap_ms: Milliseconds between the two presses.
        :type gap_ms: float
        """
        cls._dc_samples.append(gap_ms)

        samples = sorted(cls._dc_samples)
        if len(samples) >= 3:
            samples = samples[1:-1]

        stored = EditorDBConfig.double_click_average
        if stored:
            samples.append(stored)

        EditorDBConfig.double_click_average = int(
            round(sum(samples) / len(samples)))

    def _deselect_wait_ms(self) -> int:
        """Return how long a click on the selected row should wait for a
        possible second click before deselecting.

        Uses the learned double-click average plus margin, clamped between
        :attr:`_DESELECT_MIN_MS` and the OS double-click interval. Falls
        back to the OS interval until an average has been learned.

        :returns: Wait time in milliseconds.
        :rtype: int
        """
        os_interval = QApplication.doubleClickInterval()
        avg = EditorDBConfig.double_click_average

        if not avg:
            return os_interval

        return int(min(os_interval,
                       max(self._DESELECT_MIN_MS,
                           avg * self._DESELECT_MARGIN)))

    def _on_deselect_timeout(self):
        """Carry out a deselect scheduled by :meth:`mousePressEvent` once
        the double-click interval has passed with no second click.
        """
        row = self._pending_deselect_row
        self._pending_deselect_row = None

        if row is not None and self.selected == row:
            self.clearSelection()

    def keyPressEvent(self, event):
        """Handle key presses, clearing the selection on Escape.

        :param event: Key event.
        :type event: :class:`QtGui.QKeyEvent`
        """
        if (
            event.key() == Qt.Key.Key_Escape and
            self.selectionModel().hasSelection()
        ):
            self.clearSelection()
            event.accept()
            return

        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_selection_changed(self, selected, deselected):
        """Handle the selection changed event.

        Keeps :attr:`selected` in sync with the selection model and emits
        :attr:`itemSelected` / :attr:`itemUnselected`.

        :param selected: Newly selected items.
        :type selected: :class:`QtCore.QItemSelection`
        :param deselected: Newly deselected items.
        :type deselected: :class:`QtCore.QItemSelection`
        """
        indexes = self.selectionModel().selectedIndexes()
        previous = self.selected

        if indexes:
            self.selected = indexes[0].row()
            self.itemSelected.emit(self.selected)
        else:
            self.selected = None
            if previous is not None:
                self.itemUnselected.emit()

    def _clear_selection_state(self):
        """Clear :attr:`selected`, emitting ``itemUnselected`` when a row
        was selected beforehand. Used by programmatic resets that bypass
        the selection model (filter changes, sort changes).
        """
        if self.selected is not None:
            self.selected = None
            self.itemUnselected.emit()

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
        self._clear_selection_state()
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
        self._header_search: dict[str, str] = {}
        self._effective_query = self._build_query()

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

        # Right-click a header section for a per-column search popup.
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_context_menu)  # NOQA

        self.column_lookup = {}

        # icon column
        self.setColumnWidth(0, 72)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)

        fm = self.fontMetrics()
        for i in sorted(self.column_mapping.keys()):
            label_text = self.column_mapping[i][0]
            column_name = self.column_mapping[i][1]['alias']

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

        # Deferred click-to-deselect; see mousePressEvent.
        self._pending_deselect_row = None
        self._last_press_ns = None
        self._deselect_timer = QTimer(self)
        self._deselect_timer.setSingleShot(True)
        self._deselect_timer.timeout.connect(self._on_deselect_timeout)

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
