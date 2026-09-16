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
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QScrollArea,
                               QHeaderView)

from ..editor_db import base as _base
from . import column_defs as _column_defs
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database.project_db.pjt_wire import PJTWiresTable
    from ...database.project_db.pjt_pegboard_table import PJTPegboardTable


class _ColumnPickerPopup(QWidget):
    """Right-click-header popup listing every optional column as a
    checkbox, checked state mirroring what's currently shown. Toggling
    one applies immediately (no OK/Cancel) -- same instant-apply feel as
    a normal column-visibility menu.

    ``Qt.Popup`` (same as :class:`_HeaderSearchPopup` in editor_db.base)
    means Qt closes it automatically on any click outside it or loss of
    focus.
    """

    @_check_types.do
    def __init__(self, parent, visible_indices: list[int], on_toggle):
        """Initialise the popup.

        :param parent: Widget the popup is anchored near.
        :type parent: QWidget
        :param visible_indices: COLUMN_DEFS indices currently shown.
        :type visible_indices: list[int]
        :param on_toggle: Called with ``(def_index, checked)`` whenever a
            checkbox is toggled.
        :type on_toggle: Callable[[int, bool], None]
        """
        super().__init__(parent, Qt.WindowType.Popup)
        self._on_toggle = on_toggle

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(400)
        outer.addWidget(scroll)

        body = QWidget(scroll)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(body)

        visible_set = set(visible_indices)
        for def_index, (label, _info) in enumerate(_column_defs.COLUMN_DEFS):
            box = QCheckBox(label, body)
            box.setChecked(def_index in visible_set)
            box.toggled.connect(
                lambda checked, i=def_index: self._on_toggle(i, checked))
            layout.addWidget(box)


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

        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.sectionMoved.connect(self._on_section_moved)  # NOQA

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
    def _on_header_context_menu(self, pos: QPoint) -> None:
        """Show the add/remove-column checklist. Replaces (does not
        extend) the inherited per-column search popup for this table --
        see the module docstring for why the two features couldn't share
        the right-click trigger.

        :param pos: Click position, in the header's own coordinates.
        :type pos: QPoint
        """
        visible = [_column_defs.ALIAS_TO_DEF_INDEX[entry[1]['alias']]
                   for key, entry in sorted(self.column_mapping.items())
                   if key != 0]

        popup = _ColumnPickerPopup(self, visible, self._on_column_toggled)
        popup.move(self.horizontalHeader().mapToGlobal(pos))
        popup.show()

    @_check_types.do
    def _on_column_toggled(self, def_index: int, checked: bool) -> None:
        """Add or remove one column, re-querying and persisting the new
        visible-column list.

        :param def_index: The toggled column's COLUMN_DEFS index.
        :type def_index: int
        :param checked: ``True`` to show the column, ``False`` to hide it.
        :type checked: bool
        """
        visible = [_column_defs.ALIAS_TO_DEF_INDEX[entry[1]['alias']]
                   for key, entry in sorted(self.column_mapping.items())
                   if key != 0]

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

        header = self.horizontalHeader()
        for i in sorted(self.column_mapping.keys()):
            if i == 0:
                continue

            column_name = self.column_mapping[i][1]['alias']
            self.column_lookup[i] = column_name

        self._model.reset_all()
        self._rebuild_header_columns()

        self.pegboard_table.visible_columns = visible_def_indices

    @_check_types.do
    def _rebuild_header_columns(self) -> None:
        """Re-apply column widths/resize-modes after a column set change.
        Mirrors the sizing loop in :meth:`EditorList.__init__`.
        """
        header = self.horizontalHeader()
        fm = self.fontMetrics()

        for i in sorted(self.column_mapping.keys()):
            if i == 0:
                continue

            label_text = self.column_mapping[i][0]
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            offset = 100 if label_text == 'Description' else 25
            self.setColumnWidth(i, fm.horizontalAdvance(label_text) + offset)

    # ------------------------------------------------------------------
    # Column drag-to-reorder
    # ------------------------------------------------------------------

    @_check_types.do
    def _on_section_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Persist the header's new left-to-right column order.

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
            # The icon column got displaced from visual position 0 --
            # move it back; this itself re-enters _on_section_moved, so
            # guard against infinite recursion isn't needed (the second
            # call will find logicalIndex(0) == 0 and fall through).
            header.moveSection(header.visualIndex(0), 0)
            return

        visible = []
        for visual_pos in range(1, header.count()):
            logical = header.logicalIndex(visual_pos)
            column_name = self.column_lookup.get(logical)
            if column_name is None:
                continue

            visible.append(_column_defs.ALIAS_TO_DEF_INDEX[column_name])

        self.pegboard_table.visible_columns = visible
