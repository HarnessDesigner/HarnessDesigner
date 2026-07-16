# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""``QAbstractTableModel``/delegate pair for one Peg Board Editor data
table overlay.

Structurally mirrors ``ui.editor_ciruit.editor_widget.CircuitTableModel``:
the image column returns ``None`` from :meth:`PegboardTableModel.data` for
``DisplayRole`` (it's entirely delegate-painted, same as that model's own
``COL_WIRE_COLOR``/``COL_FROM_CONN``), and the delegate fetches the row via
a custom ``UserRole + 1`` role -- the exact role value
``ui.editor_ciruit.editor_widget.WireDelegate`` already uses, kept
identical here rather than picked arbitrarily.

Row *identity* (which wires, in what order) is built once, up front, by
``table_rows.build_rows_for_*`` -- cheap plain-field lookups. Each row's
wire *image* is the one genuinely lazy piece: :attr:`table_rows.
WireTableRow.image_pixmap` starts ``None`` and is only filled in by
:class:`WireImageDelegate.paint` the first time that row is actually
painted, which for a ``QTableView`` only ever happens for currently
visible rows -- i.e. "images load as you scroll" falls out of Qt's normal
view/delegate painting for free, with no ``canFetchMore``/``fetchMore``
machinery needed.
"""

from PySide6 import QtCore, QtWidgets

from . import table_rows as _table_rows


COL_IMAGE = 0
COL_NAME = 1

# (header, row -> display text). Image column has no extractor -- it's
# painted entirely by WireImageDelegate.
_BASE_COLUMNS = (
    ('Wire', None),
    ('Name', lambda row: row.wire.name),
    ('Circuit #', lambda row: (
        '' if row.wire.circuit is None else str(row.wire.circuit.circuit_num))),
    ('AWG', lambda row: str(row.wire.part.size_awg)),
    ('Cross-Section (mm²)', lambda row: f'{row.wire.part.size_mm2:.2f}'),
    ('Part Number', lambda row: row.wire.part.part_number),
    ('Manufacturer', lambda row: row.wire.part.manufacturer.name),
    # Belt-and-suspenders alongside the group_color background: only
    # populated for multi-conductor cable rows (row.group_color is not
    # None) -- see table_rows._expand_multi_conductor.
    ('Cable Name', lambda row: row.wire.name if row.group_color is not None else ''),
)

# Housing tables only -- appended after _BASE_COLUMNS.
_CAVITY_COLUMNS = (
    ('Cavity Index', lambda row: (
        '' if row.cavity is None else str(row.cavity.part.idx))),
    ('Cavity Name', lambda row: (
        '' if row.cavity is None else (row.cavity.name or row.cavity.part.name))),
)


class PegboardTableModel(QtCore.QAbstractTableModel):
    """Table model for one peg-board data-table overlay.

    :param rows: This table's rows, in display order (already sorted/
        grouped by the caller -- see ``table_rows.build_rows_for_*``).
    :type rows: list[:class:`table_rows.WireTableRow`]
    :param include_cavity_columns: ``True`` for a housing's table (appends
        :data:`_CAVITY_COLUMNS`); ``False`` for splice/transition-branch/
        bare-terminal tables.
    :type include_cavity_columns: bool
    """

    ROW_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self, rows: list, include_cavity_columns: bool, parent=None):
        super().__init__(parent)

        self._rows = rows
        self._columns = list(_BASE_COLUMNS)
        if include_cavity_columns:
            self._columns.extend(_CAVITY_COLUMNS)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                    role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            return self._columns[section][0]

        return str(section + 1)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if role == self.ROW_ROLE:
            return row

        if col == COL_IMAGE:
            # Entirely delegate-painted -- see WireImageDelegate.
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            _, extractor = self._columns[col]
            return extractor(row)

        if role == QtCore.Qt.ItemDataRole.BackgroundRole and col == COL_NAME:
            return row.group_color

        return None


class WireImageDelegate(QtWidgets.QStyledItemDelegate):
    """Paints the 400x100 ``build_wire()`` swatch scaled to fit its cell.

    Mirrors ``ui.editor_ciruit.editor_widget.WireDelegate.paint``: fetches
    the row via :attr:`PegboardTableModel.ROW_ROLE`, then scales at PAINT
    time to whatever rect the view currently gives it -- this is what
    makes the image track the table's own zoom-driven row-height scaling
    without the model needing to know anything about the camera.
    """

    _MARGIN = 2

    def paint(self, painter, option, index: QtCore.QModelIndex) -> None:
        row = index.data(PegboardTableModel.ROW_ROLE)
        if row is None:
            super().paint(painter, option, index)
            return

        painter.save()

        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif row.group_color is not None:
            painter.fillRect(option.rect, row.group_color)

        if row.image_pixmap is None:
            row.image_pixmap = _table_rows.wire_image_pixmap(row.wire)

        cell_w = option.rect.width() - self._MARGIN * 2
        cell_h = option.rect.height() - self._MARGIN * 2

        if cell_w > 0 and cell_h > 0:
            scaled = row.image_pixmap.scaled(
                cell_w, cell_h,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation)
            x = option.rect.left() + (option.rect.width() - scaled.width()) // 2
            y = option.rect.top() + (option.rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        painter.restore()
