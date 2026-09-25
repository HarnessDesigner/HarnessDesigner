# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The peg-board floating wire table -- an :class:`EditorList` subclass so
it inherits the SAME virtual row loading (dynamic buffer sizing via
:class:`ScrollTracker`), multi-column sort stack, and paginated SQL query
machinery every other editor-db list already uses, instead of
reimplementing any of it.

What this subclass adds on top:

- A custom :meth:`WireTable._build_query` -- the base class's own
  auto-generator only supports one-hop FK lookups (column -> a single
  JOINed lookup table), but this table's columns span TWO hops
  (``pjt_wires.part_id -> wires.mfg_id -> manufacturers.name``) plus a
  second, independent join (``pjt_wires.circuit_id -> pjt_circuits``), so
  the JOINs are hand-written instead of generated.
- ``column_mapping`` built PER-INSTANCE (not a class attribute like
  :class:`WiresPage`) from whichever :data:`column_defs.COLUMN_DEFS`
  indices are in ``PJTPegboardTable.visible_columns``, in that order --
  this is what makes the add/remove-column popup and drag-to-reorder
  header actually change what's queried and displayed.
- :meth:`_get_cell_text` overridden for the 7 circuit "math" columns
  (resistance/volts/load/voltage-drop/weight/length) that
  :class:`PJTCircuit` computes in Python by walking terminals/splices/
  wire-service-loops -- no single JOINed SELECT can express them, so the
  query selects a NULL placeholder at their position (to keep every other
  column's row-index position aligned) and this looks up the real
  :class:`PJTCircuit` object on demand instead.
- :meth:`_on_header_context_menu` replaced entirely (column checklist
  popup instead of the inherited per-column search popup -- see the
  module-level design conversation this was built from: the two features
  wanted the same right-click trigger, and the checklist was chosen to win
  for this table).
- Column drag-to-reorder via native ``QHeaderView.setSectionsMovable``,
  persisted back to ``PJTPegboardTable.visible_columns`` on every drop.
- Cross-table wire selection: selecting a row in one table selects (and
  scrolls into view) the row for the same wire in every other live table of
  the same project -- see :meth:`_on_row_selected`/:meth:`_select_wire`.
"""

import weakref
from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QScrollArea,
                               QHeaderView, QAbstractItemView, QApplication, QFrame)

from ..editor_db import base as _base
from . import column_defs as _column_defs
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database.project_db.pjt_wire import PJTWiresTable
    from ...database.project_db.pjt_pegboard_table import PJTPegboardTable


class _ColumnPickerPopup(QFrame):
    """Right-click-header checklist of every optional column, checked
    state mirroring what's currently shown. Toggling one applies
    immediately (no OK/Cancel) -- same instant-apply feel as a normal
    column-visibility menu.

    A plain child widget of the :class:`WireTable` (deliberately NOT a
    ``Qt.Popup`` -- that's a separate top-level window, which the hosted
    table's ``grab()`` never captures), so it renders into the same
    texture as the table itself and stays inside the table's bounds. That
    also means Qt won't auto-close it on an outside click the way it
    would a real popup -- :meth:`WireTable.close_column_picker` is called
    by whoever routes the mouse (see ``objects_pegboard.pegboard_table``).
    """

    @_check_types.do
    def __init__(self, parent: QWidget, visible_indices: list[int], on_toggle):
        """Initialise the popup.

        :param parent: The table this popup lives inside.
        :type parent: QWidget
        :param visible_indices: COLUMN_DEFS indices currently shown.
        :type visible_indices: list[int]
        :param on_toggle: Called with ``(def_index, checked)`` whenever a
            checkbox is toggled.
        :type on_toggle: Callable[[int, bool], None]
        """
        super().__init__(parent)
        self._on_toggle = on_toggle

        # The hosted widget tree is translucent (see mdi_host) -- without
        # its own opaque fill this would render see-through.
        self.setFrameShape(QFrame.Shape.Box)
        self.setAutoFillBackground(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        body = QWidget(self._scroll)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(body)

        visible_set = set(visible_indices)
        for def_index, (label, _info) in enumerate(_column_defs.COLUMN_DEFS):
            box = QCheckBox(label, body)
            box.setChecked(def_index in visible_set)
            box.toggled.connect(
                lambda checked, i=def_index: self._on_toggle(i, checked))
            layout.addWidget(box)

        self._body_size_hint = body.sizeHint()

    @_check_types.do
    def scroll_viewport(self) -> QWidget:
        """The checklist's scroll-area viewport (see
        :meth:`WireTable.picker_scroll_viewport`).
        """
        return self._scroll.viewport()

    @_check_types.do
    def place_within(self, bounds: QRect, near: QPoint) -> None:
        """Size and position this popup to sit fully inside *bounds*
        (the table's own rect), as close to *near* as fits.

        :param bounds: The rect (in the parent's coordinates) to stay in.
        :type bounds: QRect
        :param near: Where the popup would like its top-left corner.
        :type near: QPoint
        """
        margin = 4
        max_w = max(60, bounds.width() - (2 * margin))
        max_h = max(60, bounds.height() - (2 * margin))

        # body's own height + the frame/scroll chrome, capped to what fits
        width = min(max_w, self._body_size_hint.width() + 40)
        height = min(max_h, 400, self._body_size_hint.height() + 20)
        self.resize(width, height)

        x = max(bounds.left() + margin, min(near.x(), bounds.right() - width - margin))
        y = max(bounds.top() + margin, min(near.y(), bounds.bottom() - height - margin))
        self.move(x, y)


class _HeaderLiveMoveFilter(QtCore.QObject):
    """Event filter on the horizontal header's viewport turning a left
    press-and-drag on a column title into a LIVE column move (the column
    follows the cursor as it goes, instead of QHeaderView's native
    ghost-then-drop-on-release).

    Events are only observed, never consumed -- the header still
    processes its own press/release (so a plain click still sorts, and
    the edge-resize handles still work); a press that lands within a few
    pixels of a section edge is treated as a resize and never starts a
    move.
    """

    _EDGE_PX = 4

    def __init__(self, table: "WireTable"):
        super().__init__(table)
        self._table = table
        self._logical: int | None = None
        self._press_x = 0
        self._grab_offset = 0
        self._dragging = False

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        event_type = event.type()

        # The header viewport keeps delivering non-mouse events (child
        # removal, destroy, ...) while the table itself is being torn
        # down, at which point ``self._table`` is already a dead C++
        # object -- so it is only touched inside the mouse branches below.
        if event_type == QtCore.QEvent.Type.MouseButtonPress:
            self._logical = None
            self._dragging = False
            self._table._suppress_header_click = False  # NOQA

            if event.button() == Qt.MouseButton.LeftButton:
                header = self._table.horizontalHeader()
                x = int(event.position().x())
                logical = header.logicalIndexAt(x)
                if logical > 0:
                    start = header.sectionViewportPosition(logical)
                    end = start + header.sectionSize(logical)
                    if x - start > self._EDGE_PX and end - x > self._EDGE_PX:
                        self._logical = logical
                        self._press_x = x
                        self._grab_offset = x - start

        elif event_type == QtCore.QEvent.Type.MouseMove:
            if self._logical is not None and event.buttons() & Qt.MouseButton.LeftButton:
                x = int(event.position().x())

                if not self._dragging:
                    if abs(x - self._press_x) >= QApplication.startDragDistance():
                        self._dragging = True

                if self._dragging:
                    self._table.live_drag_step(self._logical, x, self._grab_offset)

        elif event_type == QtCore.QEvent.Type.MouseButtonRelease:
            if self._dragging:
                self._table.live_drag_finished()

            self._logical = None
            self._dragging = False

        return False


class WireTable(_base.EditorList):
    """Floating peg-board wire table -- one row per :class:`PJTWire`
    (``pjt_wires``), columns drawn from :data:`column_defs.COLUMN_DEFS`
    per the owning anchor's saved :class:`PJTPegboardTable`.
    """

    _has_image = False
    _has_model_3d = False

    __table_name__ = 'pjt_wires'

    _COMPUTED_ALIASES = {
        info['alias'] for _label, info in _column_defs.COLUMN_DEFS
        if info.get('computed')
    }

    table: "PJTWiresTable" = None

    # Every live WireTable, so a selection can be mirrored into the others.
    _live_tables: "weakref.WeakSet[WireTable]" = weakref.WeakSet()

    # Emitted after a selection was changed programmatically by another
    # table (see _select_wire) -- the owning PegboardTable object listens
    # so it can regrab its GL texture; nothing else would repaint it.
    wire_selection_synced = QtCore.Signal()

    # Emitted whenever the table's own look changed with no mouse event
    # to trigger a repaint (column toggled/moved) -- same listener.
    appearance_changed = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent, mainframe, label, table,
                 pegboard_table: "PJTPegboardTable"):
        """Initialise the :class:`WireTable` instance.

        :param parent: Parent widget.
        :type parent: QWidget
        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        :param label: Table label (used by the inherited edit dialog).
        :type label: str
        :param table: The ``pjt_wires`` table accessor.
        :type table: :class:`PJTWiresTable`
        :param pegboard_table: The owning anchor's saved table row --
            source of truth for ``visible_columns``.
        :type pegboard_table: :class:`PJTPegboardTable`
        """
        self.pegboard_table = pegboard_table
        self.column_mapping = self._build_column_mapping(
            pegboard_table.visible_columns or _column_defs.DEFAULT_VISIBLE_COLUMNS)

        super().__init__(parent, mainframe, label, table)

        # column_mapping key 0 ('DB ID') is only there so row[1] is the
        # id for get_obj_id/_get_cell_text/_get_icon (see
        # _build_column_mapping's own docstring) -- WiresPage shows it
        # as a real column, but a floating peg-board table has no use
        # for a raw internal id, so its logical column (1, right after
        # the icon column) is hidden rather than displayed.
        self.setColumnHidden(1, True)

        # Column reorder is driven by _HeaderLiveMoveFilter (live, as the
        # cursor moves) rather than QHeaderView's own drag, which only
        # moves the column on release -- so native movable stays off.
        self._live_dragging = False
        self._suppress_header_click = False
        self._picker: _ColumnPickerPopup | None = None

        header = self.horizontalHeader()
        header.setSectionsMovable(False)
        header.sectionMoved.connect(self._on_section_moved)  # NOQA

        self._live_move_filter = _HeaderLiveMoveFilter(self)
        header.viewport().installEventFilter(self._live_move_filter)

        self._syncing_selection = False
        self.itemSelected.connect(self._on_row_selected)
        WireTable._live_tables.add(self)

    # ------------------------------------------------------------------
    # column_mapping construction
    # ------------------------------------------------------------------

    @staticmethod
    @_check_types.do
    def _build_column_mapping(visible_def_indices: list[int]) -> dict:
        """Build a fresh ``column_mapping`` from a list of
        :data:`column_defs.COLUMN_DEFS` indices, in that order.

        Key 0 is always the row's own id (``t.id``) -- every inherited
        ``EditorList``/``_EditorModel`` helper (``_get_cell_text``,
        ``_get_icon``, ``get_obj_id``, ...) relies on ``row[1]`` being the
        id, matching :class:`WiresPage`'s own convention. The user-visible
        columns start at key 1, in the given order.

        :param visible_def_indices: COLUMN_DEFS indices to show, in
            display order.
        :type visible_def_indices: list[int]
        :returns: A fresh ``column_mapping`` dict.
        :rtype: dict
        """
        mapping = {0: ('DB ID', {'alias': 'id', 'sql': 't.id'}, True)}

        for position, def_index in enumerate(visible_def_indices, start=1):
            label, info = _column_defs.COLUMN_DEFS[def_index]
            mapping[position] = (label, info)

        return mapping

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    @_check_types.do
    def _build_query(self) -> str:
        """Build the paginated SELECT, hand-written (not auto-generated
        from ``column_mapping`` the way the base class's own
        :meth:`EditorList._build_query` does) since this table's columns
        span two JOIN hops (``pjt_wires -> wires -> lookup table``) plus
        an independent second join (``pjt_wires -> pjt_circuits``), which
        the base generator's one-hop-per-column model can't express.

        A computed column (see :data:`column_defs.COLUMN_DEFS`) selects
        a literal ``NULL`` -- its real value isn't in SQL at all (see the
        module docstring) -- purely to keep every column's row-index
        position aligned with ``column_mapping``.

        Scoped to this table's own anchor's own wires (``PJTHousing.
        wires``/``PJTBundle.wires``/etc. -- see :attr:`pegboard_table.
        anchor`) via an ``INNER JOIN`` against a derived table of that
        anchor's CURRENT wire ids, fetched fresh every time this is
        called (not cached), rather than the base class's own
        ``{where_clause}`` slot -- that's reserved for the per-column
        header search filter, which is optional and always renders as
        either ``''`` or a full ``WHERE ...``, so it can't also carry an
        unconditional restriction without colliding with a second
        ``WHERE``. An anchor with no wires yet (or with no anchor
        resolved at all) gets an empty-shaped derived table, so the join
        matches nothing rather than falling through to every wire in
        the project -- confirmed 2026-09-16 as a real bug (a table on a
        housing with exactly one wire showing every wire in the
        project).
        """
        select_cols = []
        for entry in self.column_mapping.values():
            info = entry[1]
            alias = info['alias']
            if info.get('computed'):
                select_cols.append(f'NULL AS {alias}')
            else:
                select_cols.append(f'{info["sql"]} AS {alias}')

        anchor = self.pegboard_table.anchor
        wire_ids = [w.db_id for w in anchor.wires] if anchor is not None else []

        if wire_ids:
            scope_rows = ' UNION ALL '.join(
                f"SELECT x'{wire_id.hex()}' AS id" for wire_id in wire_ids)
        else:
            scope_rows = 'SELECT NULL AS id LIMIT 0'

        query = (
            f'SELECT * FROM (SELECT ROW_NUMBER() OVER '
            f'(ORDER BY {{sort_clause}}) AS RowNum, * '
            f'FROM (SELECT {", ".join(select_cols)} '
            f'FROM pjt_wires AS t '
            f'INNER JOIN ({scope_rows}) AS anchor_scope ON anchor_scope.id = t.id '
            f'LEFT JOIN wires AS part ON part.id = t.part_id '
            f'LEFT JOIN manufacturers AS mfg ON mfg.id = part.mfg_id '
            f'LEFT JOIN families AS family ON family.id = part.family_id '
            f'LEFT JOIN series AS series ON series.id = part.series_id '
            f'LEFT JOIN colors AS color ON color.id = part.color_id '
            f'LEFT JOIN colors AS stripe_color ON stripe_color.id = part.stripe_color_id '
            f'LEFT JOIN temperatures AS min_temp ON min_temp.id = part.min_temp_id '
            f'LEFT JOIN temperatures AS max_temp ON max_temp.id = part.max_temp_id '
            f'LEFT JOIN materials AS material ON material.id = part.material_id '
            f'LEFT JOIN platings AS core_material ON core_material.id = part.core_material_id '
            f'LEFT JOIN pjt_circuits AS circuit ON circuit.id = t.circuit_id '
            f'{{where_clause}}) AS base) AS paged '
            f'WHERE RowNum BETWEEN {{start_row}} AND {{end_row}};'
        )

        return query

    @_check_types.do
    def refresh_wire_scope(self) -> None:
        """Rebuild the query (re-fetching the anchor's current wire ids
        -- see :meth:`_build_query`'s own docstring) and requery, so a
        wire connecting/disconnecting from this table's own anchor is
        reflected. Called from ``objects_pegboard.pegboard_table.
        PegboardTable.refresh_wires`` -- a plain ``Refresh()`` alone
        would only repaint the SAME (now stale) id list ``_build_query``
        baked in at construction/last refresh time.
        """
        self._effective_query = self._build_query()
        self.rows.clear()
        self.bitmap_indexes.clear()
        self._model.reset_all()

    @_check_types.do
    def _get_cell_text(self, row_id, col_id):
        """Return the cell text, overriding the 7 computed circuit
        columns with a real value looked up from :class:`PJTCircuit`
        (walking terminals/splices/wire-service-loops in Python) instead
        of the ``NULL`` placeholder the SQL query selected for them.

        :param row_id: Visible row index.
        :type row_id: int
        :param col_id: Column index (already +1 for the icon column).
        :type col_id: int
        :returns: Display text for the cell.
        :rtype: str
        """
        col_name = self.column_lookup.get(col_id, '')
        if col_name not in self._COMPUTED_ALIASES:
            return super()._get_cell_text(row_id, col_id)

        if row_id < 0:
            return ''

        # get_obj_id's query matches against SQL's 1-indexed RowNum (see
        # dialogs.part_search's own use of the same +1 convention) --
        # row_id here is the 0-indexed Qt row.
        db_id = self.get_obj_id(row_id + 1)
        if db_id is None:
            return ''

        if col_name == 'cavity_name':
            return self._cavity_names_for_wire(db_id)

        # See _get_icon's own comment -- get_obj_id can transiently
        # return an id not yet resolvable via a plain select() here.
        circuit_rows = self.table.select('circuit_id', id=db_id)
        if not circuit_rows:
            return ''

        circuit_id = circuit_rows[0][0]
        if circuit_id is None:
            return ''

        circuit = self.table.db.pjt_circuits_table[circuit_id]

        if col_name == 'circuit_resistance':
            return str(circuit.resistance)
        if col_name == 'circuit_volts':
            return str(circuit.volts)
        if col_name == 'circuit_load':
            return str(circuit.total_circuit_load)
        if col_name == 'circuit_voltage_drop':
            return str(circuit.voltage_drop)
        if col_name == 'circuit_voltage_drop_pct':
            volts = circuit.volts
            if not volts:
                return '0'
            return str(circuit.voltage_drop / volts * 100.0)
        if col_name == 'circuit_weight':
            return str(circuit.total_circuit_weight_g)
        if col_name == 'circuit_length':
            return str(circuit.wire_length_mm)

        return ''

    @_check_types.do
    def _cavity_names_for_wire(self, wire_id: bytes) -> str:
        """Name(s) of the cavity/cavities this wire's ends are seated in.

        A wire's start/stop point IS the seated terminal's
        ``attach_point3d_id`` (see ``PJTHousing.wires``), so each end is
        matched to a terminal, then to that terminal's cavity. When the
        owning anchor is a housing, only that housing's own cavity is
        shown (the wire's other end sits in a different housing); for any
        other anchor (bundle/transition) every end's cavity is listed,
        joined with `` / ``.

        :param wire_id: The ``pjt_wires`` row id.
        :type wire_id: bytes
        :returns: Cavity name text, ``''`` if the wire is seated nowhere
            (or its cavities are unnamed).
        :rtype: str
        """
        wire_rows = self.table.select('start_point3d_id', 'stop_point3d_id', id=wire_id)
        if not wire_rows:
            return ''

        db = self.table.db
        anchor = self.pegboard_table.anchor
        anchor_id = None
        if anchor is not None:
            anchor_id = anchor.db_id

        cavities = []
        for point_id in wire_rows[0]:
            if point_id is None:
                continue

            for terminal_row in db.pjt_terminals_table.select('cavity_id', attach_point3d_id=point_id):
                cavity_id = terminal_row[0]
                if cavity_id is None:
                    continue

                for name, housing_id in db.pjt_cavities_table.select('name', 'housing_id', id=cavity_id):
                    cavities.append((name, housing_id))

        own = [name for name, housing_id in cavities if housing_id == anchor_id]
        if own:
            names = own
        else:
            names = [name for name, _housing_id in cavities]

        return ' / '.join(name for name in names if name)

    @_check_types.do
    def _get_icon(self, row_id):
        """Return the wire-insulation swatch icon for *row_id*, same
        technique as :meth:`WiresPage._get_icon` but starting from this
        row's joined ``part_id`` (a ``pjt_wires`` row has no color/
        material columns of its own -- they live on the JOINed ``wires``
        part record) instead of treating the row's own id as the part id.

        :param row_id: Visible row index.
        :type row_id: int
        :returns: The swatch icon, or the shared "no image" placeholder.
        :rtype: :class:`PySide6.QtGui.QIcon`
        """
        from ... import image as _image
        from ...database import id_generator as _id_generator
        from PySide6.QtGui import QIcon

        if row_id < 0:
            return None

        # get_obj_id's query matches against SQL's 1-indexed RowNum (see
        # dialogs.part_search's own use of the same +1 convention) --
        # row_id here is the 0-indexed Qt row. Passing row_id directly
        # (unshifted) is what put every icon one row below where it
        # belonged -- confirmed 2026-09-16.
        db_id = self.get_obj_id(row_id + 1)
        if db_id is None:
            return None

        if db_id in self.bitmap_indexes:
            return self.bitmap_indexes[db_id]

        # get_obj_id runs a fresh windowed query against this table's own
        # _effective_query for row_id's CURRENT screen position -- a real
        # race exists between that and a row actually landing in this
        # editor's own scroll buffer (confirmed 2026-09-16: crashed on a
        # brand new peg-board table's very first synchronous paint, where
        # get_obj_id transiently returned an id not yet resolvable here).
        # Defensive empty-result guards below, same "no image" fallback
        # already used for every other "can't determine a real color"
        # case in this method, rather than assuming either lookup always
        # finds a row.
        part_rows = self.table.select('part_id', id=db_id)
        if not part_rows:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        part_id = part_rows[0][0]

        wires_table = self.table.db.global_db.wires_table
        wire_rows = wires_table.select(
            'num_conductors', 'shielded', 'color_id', 'stripe_color_id',
            'core_material_id', id=part_id)
        if not wire_rows:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        num_conductors, shielded, color_id, stripe_color_id, core_material_id = wire_rows[0]

        if num_conductors != 1 or shielded:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        nil_uuid = _id_generator.NIL_UUID.bytes
        colors_table = self.table.db.global_db.colors_table

        primary_color = None if color_id is None or color_id == nil_uuid else colors_table[color_id]
        stripe_color = None if stripe_color_id is None or stripe_color_id == nil_uuid else colors_table[stripe_color_id]

        if core_material_id is None or core_material_id == nil_uuid:
            conductor_color = None
        else:
            conductor_color = self.table.db.global_db.platings_table[core_material_id].color

        if primary_color is None or conductor_color is None:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        image = _image.images.build_wire(primary_color, stripe_color, conductor_color)
        image = image.resize_keep_aspect(64, 64)

        icon = QIcon(image.pixmap)
        self.bitmap_indexes[db_id] = icon

        return icon

    # ------------------------------------------------------------------
    # Column visibility (right-click header popup)
    # ------------------------------------------------------------------

    @_check_types.do
    def _visible_def_indices(self) -> list[int]:
        """COLUMN_DEFS indices of the columns currently shown, in the
        header's current left-to-right (visual) order -- NOT
        ``column_mapping``'s key order, which a live drag-reorder doesn't
        touch.

        :returns: COLUMN_DEFS indices in display order.
        :rtype: list[int]
        """
        header = self.horizontalHeader()

        visible = []
        for visual_pos in range(1, header.count()):
            column_name = self.column_lookup.get(header.logicalIndex(visual_pos))
            if column_name not in _column_defs.ALIAS_TO_DEF_INDEX:
                # the hidden row-id column ('id') isn't a COLUMN_DEFS entry
                continue

            visible.append(_column_defs.ALIAS_TO_DEF_INDEX[column_name])

        return visible

    @_check_types.do
    def show_column_picker(self, pos: QPoint) -> None:
        """Show the add/remove-column checklist inside this table, as
        close to *pos* as fits (see :class:`_ColumnPickerPopup` for why
        it's a plain child widget rather than a ``Qt.Popup`` window).
        Replaces one already open.

        :param pos: Where to place it, in this table's own coordinates.
        :type pos: QPoint
        """
        self.close_column_picker()

        self._picker = _ColumnPickerPopup(self, self._visible_def_indices(), self._on_column_toggled)
        self._picker.place_within(self.rect(), pos)
        self._picker.show()
        self._picker.raise_()
        self.appearance_changed.emit()

    @property
    def has_column_picker(self) -> bool:
        """Whether the column checklist is currently open."""
        return self._picker is not None

    @_check_types.do
    def close_column_picker(self) -> None:
        """Close the column checklist if it's open."""
        if self._picker is None:
            return

        picker = self._picker
        self._picker = None
        picker.hide()
        picker.deleteLater()
        self.appearance_changed.emit()

    @_check_types.do
    def picker_scroll_viewport(self) -> QWidget | None:
        """The open column checklist's scroll-area viewport, or ``None``
        if it isn't open.

        The right target for a forwarded wheel event: a synthetic wheel
        sent to the deepest child under the cursor (a checkbox, a
        scrollbar, the frame margin) does NOT propagate up to the scroll
        area the way a real one would, so nothing scrolls -- only one
        delivered to this viewport does.
        """
        if self._picker is None:
            return None

        return self._picker.scroll_viewport()

    @_check_types.do
    def picker_contains(self, widget: QWidget | None) -> bool:
        """Whether *widget* is the open column checklist or inside it.

        :param widget: A widget, or ``None``.
        :type widget: QWidget | None
        :returns: ``True`` if the checklist is open and owns *widget*.
        :rtype: bool
        """
        if self._picker is None or widget is None:
            return False

        return widget is self._picker or self._picker.isAncestorOf(widget)

    @_check_types.do
    def _on_header_context_menu(self, pos: QPoint) -> None:
        """Show the add/remove-column checklist. Replaces (does not
        extend) the inherited per-column search popup for this table --
        see the module docstring for why the two features couldn't share
        the right-click trigger.

        :param pos: Click position, in the header's own coordinates.
        :type pos: QPoint
        """
        self.show_column_picker(self.mapFromGlobal(self.horizontalHeader().mapToGlobal(pos)))

    @_check_types.do
    def _on_column_toggled(self, def_index: int, checked: bool) -> None:
        """Add or remove one column, re-querying and persisting the new
        visible-column list.

        :param def_index: The toggled column's COLUMN_DEFS index.
        :type def_index: int
        :param checked: ``True`` to show the column, ``False`` to hide it.
        :type checked: bool
        """
        visible = self._visible_def_indices()

        if checked:
            if def_index not in visible:
                visible.append(def_index)
        else:
            if def_index in visible:
                visible.remove(def_index)

        self._apply_visible_columns(visible)

    @_check_types.do
    def _apply_visible_columns(self, visible_def_indices: list[int]) -> None:
        """Rebuild ``column_mapping``/the SQL query for a new column
        selection or order, persist it, and refresh the view.

        :param visible_def_indices: COLUMN_DEFS indices, in display order.
        :type visible_def_indices: list[int]
        """
        self.column_mapping = self._build_column_mapping(visible_def_indices)
        self._effective_query = self._build_query()
        self.max_column_count = len(self.column_mapping)

        self.rows.clear()
        self.bitmap_indexes.clear()
        self._clear_selection_state()
        self.column_lookup.clear()

        # logical index = mapping key + 1 (logical 0 is the icon column),
        # exactly as EditorList.__init__ builds it -- key 0 ('id') lands
        # on the hidden logical column 1.
        for key in sorted(self.column_mapping.keys()):
            self.column_lookup[key + 1] = self.column_mapping[key][1]['alias']

        self._model.reset_all()

        # A reset may keep the header's old visual permutation; the new
        # mapping is laid out in display order, so put visual == logical.
        header = self.horizontalHeader()
        self._live_dragging = True
        try:
            for logical in range(header.count()):
                header.moveSection(header.visualIndex(logical), logical)
        finally:
            self._live_dragging = False

        self._rebuild_header_columns()
        self.setColumnHidden(1, True)

        self.pegboard_table.visible_columns = visible_def_indices
        self.appearance_changed.emit()

    @_check_types.do
    def _rebuild_header_columns(self) -> None:
        """Re-apply column widths/resize-modes after a column set change.
        Mirrors the sizing loop in :meth:`EditorList.__init__`.
        """
        header = self.horizontalHeader()
        fm = self.fontMetrics()

        for key in sorted(self.column_mapping.keys()):
            if key == 0:
                continue

            logical = key + 1
            label_text = self.column_mapping[key][0]
            header.setSectionResizeMode(logical, QHeaderView.ResizeMode.Interactive)
            offset = 100 if label_text == 'Description' else 25
            self.setColumnWidth(logical, fm.horizontalAdvance(label_text) + offset)

    # ------------------------------------------------------------------
    # Column drag-to-reorder (live)
    # ------------------------------------------------------------------

    @_check_types.do
    def _on_header_clicked(self, logical_index: int) -> None:
        """Ignore the click Qt reports at the end of a column drag -- it
        would otherwise re-sort by the column that was just moved.

        :param logical_index: The clicked header section.
        :type logical_index: int
        """
        if self._suppress_header_click:
            return

        super()._on_header_clicked(logical_index)

    @_check_types.do
    def _on_section_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Persist the header's new left-to-right column order (once per
        drag -- see :meth:`live_drag_finished` -- not on every step of a
        live move).

        The icon column (logical index 0) is kept pinned at visual
        position 0 -- QHeaderView has no direct "lock this section" flag,
        so a move that would displace it is simply undone immediately.

        :param logical_index: The section that was moved.
        :type logical_index: int
        :param old_visual: Its previous visual position.
        :type old_visual: int
        :param new_visual: Its new visual position.
        :type new_visual: int
        """
        header = self.horizontalHeader()

        if header.logicalIndex(0) != 0:
            header.moveSection(header.visualIndex(0), 0)
            return

        if self._live_dragging:
            return

        self.pegboard_table.visible_columns = self._visible_def_indices()

    @_check_types.do
    def live_drag_step(self, logical: int, cursor_x: int, grab_offset: int) -> None:
        """Move section *logical* under the cursor, live.

        The dragged section's would-be left edge (``cursor_x -
        grab_offset``) is compared against each neighbour's midpoint, so
        it swaps only once it has actually crossed half of that
        neighbour -- after a swap the same test can't immediately swap it
        back, so wide/narrow neighbours don't make it oscillate.

        :param logical: The section being dragged.
        :type logical: int
        :param cursor_x: Cursor X in the header's viewport coordinates.
        :type cursor_x: int
        :param grab_offset: Where within the section the drag started.
        :type grab_offset: int
        """
        header = self.horizontalHeader()
        self._live_dragging = True
        self._suppress_header_click = True

        try:
            for _ in range(header.count()):
                left = cursor_x - grab_offset
                right = left + header.sectionSize(logical)
                visual = header.visualIndex(logical)

                # nearest visible neighbour on each side; visual 0 is the
                # pinned icon column, never a swap target
                target = None

                v = visual - 1
                while v >= 1 and header.isSectionHidden(header.logicalIndex(v)):
                    v -= 1
                if v >= 1:
                    neighbour = header.logicalIndex(v)
                    mid = header.sectionViewportPosition(neighbour) + header.sectionSize(neighbour) / 2
                    if left < mid:
                        target = v

                if target is None:
                    v = visual + 1
                    while v < header.count() and header.isSectionHidden(header.logicalIndex(v)):
                        v += 1
                    if v < header.count():
                        neighbour = header.logicalIndex(v)
                        mid = header.sectionViewportPosition(neighbour) + header.sectionSize(neighbour) / 2
                        if right > mid:
                            target = v

                if target is None:
                    break

                header.moveSection(visual, target)
        finally:
            self._live_dragging = False

    @_check_types.do
    def live_drag_finished(self) -> None:
        """Persist the column order once the drag is released."""
        self.pegboard_table.visible_columns = self._visible_def_indices()

    # ------------------------------------------------------------------
    # Cross-table wire selection
    # ------------------------------------------------------------------

    @_check_types.do
    def _on_row_selected(self, row: int) -> None:
        """Mirror this table's new selection into every other live table
        of the same project that also contains the selected wire.

        :param row: The newly selected visible row index.
        :type row: int
        """
        if self._syncing_selection:
            return

        wire_id = self.GetSelection()
        if wire_id is None:
            return

        for other in list(WireTable._live_tables):
            if other is self or other.table.db is not self.table.db:
                continue

            try:
                other._select_wire(wire_id)
            except RuntimeError:
                # underlying C++ widget already destroyed
                WireTable._live_tables.discard(other)

    @_check_types.do
    def _row_for_wire(self, wire_id: bytes) -> int | None:
        """Find the visible (0-indexed) row holding *wire_id* under this
        table's current query, sort and filters.

        :param wire_id: The ``pjt_wires`` row id.
        :type wire_id: bytes
        :returns: The row index, or ``None`` if this table doesn't list
            that wire.
        :rtype: int | None
        """
        where_body, params = self._combined_where()
        if where_body:
            where_sql = f'WHERE {where_body}'
        else:
            where_sql = ''

        sql = self._effective_query.format(
            sort_clause=self.sort_clause, row=1, start_row=1,
            end_row=2 ** 31 - 1, where_clause=where_sql)

        if params:
            self.table.execute(sql, params)
        else:
            self.table.execute(sql)

        # result rows are (RowNum, id, ...), RowNum being 1-indexed
        for result in self.table.fetchall():
            if result[1] == wire_id:
                return result[0] - 1

        return None

    @_check_types.do
    def _select_wire(self, wire_id: bytes) -> None:
        """Select *wire_id*'s row and scroll it into view, if this table
        lists that wire. Doesn't propagate back out (guarded), and asks
        the owning PegboardTable to repaint via
        :attr:`wire_selection_synced`.

        :param wire_id: The ``pjt_wires`` row id.
        :type wire_id: bytes
        """
        row = self._row_for_wire(wire_id)
        if row is None:
            return

        self._syncing_selection = True
        try:
            self.selectRow(row)
            self.scrollTo(self.model().index(row, 0),
                          QAbstractItemView.ScrollHint.EnsureVisible)
        finally:
            self._syncing_selection = False

        self.wire_selection_synced.emit()
