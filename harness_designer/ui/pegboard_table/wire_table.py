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
from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from ..editor_db import base as _base
from . import column_defs as _column_defs
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import mainframe as _mainframe
    from ...database import project_db as _project_db
    from ...database.project_db.pjt_wire import PJTWiresTable
    from ...database.project_db.pjt_pegboard_table import PJTPegboardTable


class _ColumnPickerPopup(QtWidgets.QFrame):
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
    by whoever routes the mouse (see ``objects_pegboard.table``).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, visible_indices: list[int],
                 available_indices: list[int], on_toggle: Callable[[int, bool], None]):
        """Initialise the popup.

        :param parent: The table this popup lives inside.
        :type parent: QWidget
        :param visible_indices: COLUMN_DEFS indices currently shown.
        :type visible_indices: list[int]
        :param available_indices: COLUMN_DEFS indices this table's anchor
            can show at all (see :meth:`WireTable._available_def_indices`).
        :type available_indices: list[int]
        :param on_toggle: Called with ``(def_index, checked)`` whenever a
            checkbox is toggled.
        :type on_toggle: Callable[[int, bool], None]
        """
        super().__init__(parent)
        self._on_toggle = on_toggle

        # The hosted widget tree is translucent (see mdi_host) -- without
        # its own opaque fill this would render see-through.
        self.setFrameShape(QtWidgets.QFrame.Shape.Box)
        self.setAutoFillBackground(True)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self._scroll = QtWidgets.QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        body = QtWidgets.QWidget(self._scroll)
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(body)

        visible_set = set(visible_indices)
        for def_index, (label, _info) in enumerate(_column_defs.COLUMN_DEFS):
            if def_index not in available_indices:
                continue

            box = QtWidgets.QCheckBox(label, body)
            box.setChecked(def_index in visible_set)
            box.toggled.connect(
                lambda checked, i=def_index: self._on_toggle(i, checked))
            layout.addWidget(box)

        self._body_size_hint = body.sizeHint()

    @_check_types.do
    def scroll_viewport(self) -> QtWidgets.QWidget:
        """The checklist's scroll-area viewport (see
        :meth:`WireTable.picker_scroll_viewport`).
        """
        return self._scroll.viewport()

    @_check_types.do
    def place_within(self, bounds: QtCore.QRect, near: QtCore.QPoint) -> None:
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

    @_check_types.do
    def __init__(self, table: "WireTable"):
        super().__init__(table)
        self._table = table
        self._logical: int | None = None
        self._press_x = 0
        self._grab_offset = 0
        self._dragging = False

    @_check_types.do
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

            if event.button() == QtCore.Qt.MouseButton.LeftButton:
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
            if self._logical is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                x = int(event.position().x())

                if not self._dragging:
                    if abs(x - self._press_x) >= QtWidgets.QApplication.startDragDistance():
                        self._dragging = True

                if self._dragging:
                    self._table.live_drag_step(self._logical, x, self._grab_offset)

        elif event_type == QtCore.QEvent.Type.MouseButtonRelease:
            if self._dragging:
                self._table.live_drag_finished()

            self._logical = None
            self._dragging = False

        return False


# What a row of the table is. A plain wire is a row of its own; a cable's conductor is ONE row however many pieces of wire its lead is
# cut into (a wire service loop cuts a lead in two: two wires, one conductor); a cable is a row of its own that can be expanded into its
# conductors (a bundle's or a transition's table).
_KIND_WIRE = 0
_KIND_CABLE = 1
_KIND_CONDUCTOR = 2

# Where the value of a column comes from for a conductor's row, when it is not the one the plain wire (the catalog wire the row's own
# part is) gives: the conductor's own values (``wc`` is its ``wire_conductors`` row, ``cc`` its ``pjt_cable_conductors`` row; the
# conductor has no part number, manufacturer or family of its own, those stay the cable's).
_CONDUCTOR_SQL = {
    'description': (
        "COALESCE(part.description, '') || CASE WHEN cc.is_shield THEN ' [shield]' "
        "ELSE ' [conductor ' || (cc.idx + 1) || ']' END"),
    'color': 'ccolor.name',
    'stripe_color': 'cstripe.name',
    'material': 'cmaterial.name',
    'core_material': 'ccore.description',
    'num_conductors': '1',
    'shielded': 'cc.is_shield',
    'tpi': 'NULL',
    'wire_size_dia': 'wc.wire_size_dia',
    'wire_size_cross': 'wc.wire_size_cross',
    'wire_size_awg': 'wc.wire_size_awg',
    'od_mm': 'wc.od_mm',
    'strands': 'wc.strands',
    'is_filler_wire': 'cc.is_filler_wire',
    'wire_notes': 'cc.notes',
}

# ... and for a cable's row (the cable's part is the row's part; what belongs to the placed cable is its own).
_CABLE_SQL = {
    'is_filler_wire': '0',
    'wire_notes': 'cb.notes',
}


class _CableBackgroundDelegate(QtWidgets.QStyledItemDelegate):
    """Paints the rows of one cable (the cable's own row and every conductor of it) in one colour, a colour of its own for each cable,
    so what is in a cable and what is not can be told at a glance."""

    _TEXT = QtGui.QColor(236, 236, 236)

    def __init__(self, table: "WireTable"):
        super().__init__(table)
        self._table = table

    def initStyleOption(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        super().initStyleOption(option, index)

        brush = self._table.row_brush(index.row())
        if brush is not None:
            option.backgroundBrush = brush
            # the colours are dark: the text on them is light
            option.palette.setColor(QtGui.QPalette.ColorRole.Text, self._TEXT)
            option.palette.setColor(QtGui.QPalette.ColorRole.WindowText, self._TEXT)


class WireTable(_base.EditorList):
    """Floating peg-board wire table -- one row per plain wire (``pjt_wires``) or per cable conductor, columns drawn from
    :data:`column_defs.COLUMN_DEFS` per the owning anchor's saved :class:`PJTPegboardTable`.

    **Rows (2026-11-11):** a housing's table has a row for each plain wire and for each CONDUCTOR of a cable that plugs into it (the
    values are the conductor's, with the picture of the one conductor); a bundle's or a transition's table has a row for each plain wire
    and for each CABLE (the cable's values and picture) that a double click expands into the cable's conductors. Every row of a cable
    has the cable's colour. A conductor is selected as a conductor in every table that has it (a collapsed cable is expanded there).
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
    # table (see _select_wire) -- the owning Table object listens
    # so it can regrab its GL texture; nothing else would repaint it.
    wire_selection_synced = QtCore.Signal()

    # Emitted whenever the table's own look changed with no mouse event
    # to trigger a repaint (column toggled/moved) -- same listener.
    appearance_changed = QtCore.Signal()

    # The user picked a wire row in THIS table (not a programmatic sync
    # from another table -- see _select_wire), carrying the wire's row id;
    # and the user then cleared that selection. The owning Table
    # forwards both to the editor's WireHighlight.
    wire_selected = QtCore.Signal(object)
    wire_deselected = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_mainframe.MainFrame", label: str, table: "PJTWiresTable",
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

        # the rows (see _refresh_specs): the base class builds the query and counts the rows while it is initialised
        self._wire_db = table.db
        self._expanded: set[bytes] = set()
        self._specs: list[tuple] = []
        self._spec_by_key: dict[bytes, tuple] = {}
        self._cable_members: dict[bytes, list[bytes]] = {}
        self._cable_brushes: dict[bytes, QtGui.QBrush] = {}
        self._refresh_specs()

        visible_columns = pegboard_table.visible_columns
        if not visible_columns:
            if self._anchor_is_transition():
                visible_columns = _column_defs.DEFAULT_VISIBLE_COLUMNS_TRANSITION
            else:
                visible_columns = _column_defs.DEFAULT_VISIBLE_COLUMNS

        self.column_mapping = self._build_column_mapping(visible_columns)

        super().__init__(parent, mainframe, label, table)

        # column_mapping key 0 ('DB ID') is only there so row[1] is the
        # id for get_obj_id/_get_cell_text/_get_icon (see
        # _build_column_mapping's own docstring) -- WiresPage shows it
        # as a real column, but a floating peg-board table has no use
        # for a raw internal id, so its logical column (1, right after
        # the icon column) is hidden rather than displayed.
        self.setColumnHidden(1, True)
        self.setItemDelegate(_CableBackgroundDelegate(self))

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
        self.itemUnselected.connect(self._on_row_unselected)
        WireTable._live_tables.add(self)

    # ------------------------------------------------------------------
    # Anchor-dependent columns
    # ------------------------------------------------------------------

    @_check_types.do
    def _anchor_is_transition(self) -> bool:
        """Whether this table belongs to a transition (the only anchor
        type with the branch column).
        """
        from ...database.project_db import pjt_transition as _pjt_transition  # NOQA -- avoid a cycle at import time

        return isinstance(self.pegboard_table.anchor, _pjt_transition.PJTTransition)

    @_check_types.do
    def _available_def_indices(self) -> list[int]:
        """COLUMN_DEFS indices this table's anchor can show -- every
        column, except the ``transition_only`` ones unless the anchor is
        a transition.
        """
        is_transition = self._anchor_is_transition()

        available = []
        for def_index, (_label, info) in enumerate(_column_defs.COLUMN_DEFS):
            if info.get('transition_only') and not is_transition:
                continue

            available.append(def_index)

        return available

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
        mapping = {0: ('DB ID', {'alias': 'id', 'sql': 's.row_key'}, True)}

        for position, def_index in enumerate(visible_def_indices, start=1):
            label, info = _column_defs.COLUMN_DEFS[def_index]
            mapping[position] = (label, info)

        return mapping

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    @property
    @_check_types.do
    def record_count(self) -> int:
        """The number of rows (the rows are listed in :attr:`_specs`, not counted in ``pjt_wires``)."""
        return len(self._specs)

    @_check_types.do
    def _anchor_kind(self) -> str:
        """``'housing'``, ``'bundle'`` or ``'transition'``: which anchor this table belongs to (``''`` when it has none)."""
        from ...database.project_db import pjt_housing as _pjt_housing  # NOQA -- avoid a cycle at import time
        from ...database.project_db import pjt_bundle as _pjt_bundle  # NOQA
        from ...database.project_db import pjt_transition as _pjt_transition  # NOQA

        anchor = self.pegboard_table.anchor

        if isinstance(anchor, _pjt_housing.PJTHousing):
            return 'housing'

        if isinstance(anchor, _pjt_bundle.PJTBundle):
            return 'bundle'

        if isinstance(anchor, _pjt_transition.PJTTransition):
            return 'transition'

        return ''

    @_check_types.do
    def _build_row_specs(self) -> list[tuple]:
        """The rows of the table, in the order they are listed before any sorting: ``(key, kind, wire_id, cable_id, conductor_id, group,
        depth)`` for each.

        *key* identifies the row (the wire's id, the cable's, the conductor's), *wire_id* is a wire of a conductor's lead (to find the
        housings it is seated in), *group* ties a cable's rows together (a cable's own row is depth 0, its expanded conductors depth 1).
        The pieces of one conductor's lead (a wire service loop cuts a lead in two wires) are ONE conductor row.
        """
        anchor = self.pegboard_table.anchor
        db = self._wire_db
        self._cable_members = {}

        if anchor is None:
            return []

        kind = self._anchor_kind()
        pieces: dict[bytes, bytes] = {}
        order: list[tuple] = []
        seen: set[bytes] = set()

        for wire in anchor.wires:
            if wire.db_id in seen:
                continue

            seen.add(wire.db_id)
            conductor_id = wire.cable_conductor_id

            if conductor_id is None:
                order.append(('wire', wire.db_id))
            elif conductor_id not in pieces:
                pieces[conductor_id] = wire.db_id
                order.append(('conductor', conductor_id))

        cable_of: dict[bytes, bytes | None] = {}
        for conductor_id in pieces:
            rows = db.pjt_cable_conductors_table.select('cable_id', id=conductor_id)
            cable_of[conductor_id] = rows[0][0] if rows else None

        # cables placed on the bundle / transition themselves (no wire of theirs is routed through it)
        extra_cables: list[bytes] = []
        if kind == 'bundle':
            extra_cables = [row[0] for row in db.pjt_cables_table.select('id', bundle_id=anchor.db_id)]
        elif kind == 'transition':
            extra_cables = [row[0] for row in db.pjt_cables_table.select('id', transition_id=anchor.db_id)]

        specs: list[tuple] = []
        done_cables: set[bytes] = set()

        def add_cable(cable_id: bytes) -> None:
            if cable_id in done_cables:
                return

            done_cables.add(cable_id)
            members = [c.db_id for c in db.pjt_cables_table[cable_id].conductors]
            self._cable_members[cable_id] = members
            specs.append((cable_id, _KIND_CABLE, None, cable_id, None, cable_id, 0))

            if cable_id in self._expanded:
                for member in members:
                    specs.append((member, _KIND_CONDUCTOR, pieces.get(member), cable_id, member, cable_id, 1))

        for what, ident in order:
            if what == 'wire':
                specs.append((ident, _KIND_WIRE, ident, None, None, ident, 0))
                continue

            cable_id = cable_of.get(ident)

            if kind == 'housing' or cable_id is None:
                # a housing lists the conductors that plug into it, each with its own values and picture
                specs.append((ident, _KIND_CONDUCTOR, pieces[ident], cable_id, ident, ident, 0))
                if cable_id is not None:
                    self._cable_members.setdefault(cable_id, [])
            else:
                add_cable(cable_id)

        for cable_id in extra_cables:
            add_cable(cable_id)

        return specs

    @_check_types.do
    def _refresh_specs(self) -> None:
        """Work the rows out again (see :meth:`_build_row_specs`) -- the query follows (:meth:`_build_query`)."""
        self._specs = self._build_row_specs()
        self._spec_by_key = {spec[0]: spec for spec in self._specs}

    @_check_types.do
    def _scope_sql(self) -> str:
        """The rows as a derived table: ``row_key, kind, wire_id, cable_id, conductor_id, grp, depth``."""
        def blob(value: bytes | None) -> str:
            return 'NULL' if value is None else f"x'{value.hex()}'"

        if not self._specs:
            return ('SELECT NULL AS row_key, 0 AS kind, NULL AS wire_id, NULL AS cable_id, NULL AS conductor_id, '
                    'NULL AS grp, 0 AS depth LIMIT 0')

        values = ', '.join(
            f'({blob(key)}, {kind}, {blob(wire_id)}, {blob(cable_id)}, {blob(conductor_id)}, {blob(group)}, {depth})'
            for key, kind, wire_id, cable_id, conductor_id, group, depth in self._specs)

        return ('SELECT column1 AS row_key, column2 AS kind, column3 AS wire_id, column4 AS cable_id, column5 AS conductor_id, '
                f'column6 AS grp, column7 AS depth FROM (VALUES {values})')

    @_check_types.do
    def _build_query(self) -> str:
        """Build the paginated SELECT, hand-written (the base class's generator only knows one JOIN hop per column; this table's
        columns span two (``pjt_wires -> wires -> lookup table``) plus independent joins).

        The rows are the ones :meth:`_build_row_specs` found (their keys are written into the query, so it is built again whenever
        they change, see :meth:`refresh_wire_scope`). A WIRE row's values are the wire's part's; a CONDUCTOR row's are the
        conductor's (``_CONDUCTOR_SQL``) over the cable's part for what a conductor has none of (part number, manufacturer); a CABLE
        row's are the cable part's. A computed column selects a literal ``NULL`` (see the module docstring).

        Sorting keeps a cable's conductors under the cable: the groups are put in order by the sort of their first row (the cable's, or
        the plain wire's or conductor's own), then the rows of a group, the cable's own row first, by the same sort.
        """
        select_cols = []
        for entry in self.column_mapping.values():
            info = entry[1]
            alias = info['alias']
            if info.get('computed'):
                select_cols.append(f'NULL AS {alias}')
                continue

            conductor_sql = _CONDUCTOR_SQL.get(alias)
            cable_sql = _CABLE_SQL.get(alias)

            if conductor_sql is None and cable_sql is None:
                select_cols.append(f'{info["sql"]} AS {alias}')
            else:
                select_cols.append(
                    f'CASE s.kind WHEN {_KIND_CONDUCTOR} THEN {conductor_sql or info["sql"]} '
                    f'WHEN {_KIND_CABLE} THEN {cable_sql or info["sql"]} ELSE {info["sql"]} END AS {alias}')

        query = (
            f'WITH wt_rows AS (SELECT {", ".join(select_cols)}, s.grp AS grp, s.depth AS depth, s.kind AS kind, '
            f'COALESCE(s.cable_id, cc.cable_id) AS cable_key '
            f'FROM ({self._scope_sql()}) AS s '
            f'LEFT JOIN pjt_wires AS t ON t.id = s.wire_id '
            f'LEFT JOIN pjt_cable_conductors AS cc ON cc.id = s.conductor_id '
            f'LEFT JOIN pjt_cables AS cb ON cb.id = COALESCE(s.cable_id, cc.cable_id) '
            f'LEFT JOIN wire_conductors AS wc ON wc.id = cc.conductor_id '
            f'LEFT JOIN wires AS part ON part.id = CASE WHEN s.kind = {_KIND_WIRE} THEN t.part_id ELSE cb.part_id END '
            f'LEFT JOIN manufacturers AS mfg ON mfg.id = part.mfg_id '
            f'LEFT JOIN families AS family ON family.id = part.family_id '
            f'LEFT JOIN series AS series ON series.id = part.series_id '
            f'LEFT JOIN colors AS color ON color.id = part.color_id '
            f'LEFT JOIN colors AS stripe_color ON stripe_color.id = part.stripe_color_id '
            f'LEFT JOIN temperatures AS min_temp ON min_temp.id = part.min_temp_id '
            f'LEFT JOIN temperatures AS max_temp ON max_temp.id = part.max_temp_id '
            f'LEFT JOIN materials AS material ON material.id = part.material_id '
            f'LEFT JOIN platings AS core_material ON core_material.id = part.core_material_id '
            f'LEFT JOIN colors AS ccolor ON ccolor.id = wc.color_id '
            f'LEFT JOIN colors AS cstripe ON cstripe.id = wc.stripe_color_id '
            f'LEFT JOIN materials AS cmaterial ON cmaterial.id = wc.material_id '
            f'LEFT JOIN platings AS ccore ON ccore.id = wc.core_material_id '
            f'LEFT JOIN pjt_circuits AS circuit ON circuit.id = '
            f'CASE s.kind WHEN {_KIND_WIRE} THEN t.circuit_id WHEN {_KIND_CONDUCTOR} THEN cc.circuit_id END '
            f'{{where_clause}}), '
            f'wt_heads AS (SELECT grp, ROW_NUMBER() OVER (ORDER BY {{sort_clause}}) AS hrank FROM wt_rows WHERE depth = 0) '
            f'SELECT * FROM (SELECT ROW_NUMBER() OVER (ORDER BY COALESCE(wt_heads.hrank, 1000000000), wt_rows.depth, '
            f'{{sort_clause}}) AS RowNum, wt_rows.* FROM wt_rows LEFT JOIN wt_heads ON wt_heads.grp = wt_rows.grp) AS paged '
            f'WHERE RowNum BETWEEN {{start_row}} AND {{end_row}};'
        )

        return query

    @_check_types.do
    def refresh_wire_scope(self) -> None:
        """Work the rows out again from the anchor's CURRENT wires, rebuild the query (its row keys are written into it) and requery,
        so a wire connecting/disconnecting from this table's own anchor is reflected. Called from ``objects_pegboard.table.
        Table.refresh_wires`` -- a plain ``Refresh()`` alone would only repaint the SAME (now stale) rows."""
        self._rebuild()

    @_check_types.do
    def _rebuild(self) -> None:
        """Rows, query and what was cached of them, again."""
        self._refresh_specs()
        self._cable_brushes.clear()
        self._effective_query = self._build_query()
        self.rows.clear()
        self.bitmap_indexes.clear()
        self._row_count = len(self._specs)
        self._model.reset_all()

    # -- the colour of a cable's rows, and the rows of a cable

    @_check_types.do
    def _cable_brush(self, cable_id: bytes, head: bool) -> QtGui.QBrush:
        """The brush of *cable_id*'s rows: the cable's own dark colour (``pjt_cables.bg_color``, stored, so it is the same in every
        table and after a restart), a little lighter for the cable's own row."""
        key = (cable_id, head)
        brush = self._cable_brushes.get(key)

        if brush is None:
            value = self._wire_db.pjt_cables_table[cable_id].bg_color
            color = QtGui.QColor((value >> 16) & 255, (value >> 8) & 255, value & 255)

            if head:
                color = color.lighter(145)

            brush = QtGui.QBrush(color)
            self._cable_brushes[key] = brush

        return brush

    @_check_types.do
    def row_brush(self, row_id: int) -> QtGui.QBrush | None:
        """The background of the row *row_id* (a cable's, or one of its conductors'), ``None`` for a plain wire."""
        row = self.rows.get(row_id)
        if row is None:
            return None

        extra = 1 + len(self.column_mapping)
        kind, cable_key = row[extra + 2], row[extra + 3]

        if kind == _KIND_WIRE or cable_key is None:
            return None

        return self._cable_brush(cable_key, kind == _KIND_CABLE)

    @_check_types.do
    def wire_ids_for_key(self, key: bytes) -> list[bytes]:
        """The wires a row stands for: the wire itself; every piece of wire of a conductor's leads; those of every conductor of a cable.
        What a selection of the row lights up on the board (``WireHighlight``)."""
        spec = self._spec_by_key.get(key)
        kind = spec[1] if spec is not None else _KIND_WIRE

        if kind == _KIND_WIRE:
            return [key]

        conductor_ids = [key] if kind == _KIND_CONDUCTOR else self._cable_members.get(key, [])
        found: list[bytes] = []

        for conductor_id in conductor_ids:
            found.extend(row[0] for row in self.table.select('id', cable_conductor_id=conductor_id))

        return found

    @_check_types.do
    def selected_wire_id(self) -> bytes | None:
        """The selected row's wire, only when the row IS a plain wire (a cable's or a conductor's row is not dragged as a wire)."""
        key = self.GetSelection()
        spec = self._spec_by_key.get(key)

        if key is None or (spec is not None and spec[1] != _KIND_WIRE):
            return None

        return key

    @_check_types.do
    def _resolve_key(self, any_id: bytes) -> bytes | None:
        """The key of the row of this table that *any_id* (a wire, a cable's conductor, a cable) is, or is a part of: a piece of wire is
        its conductor's row; a conductor inside a cable that is not expanded here EXPANDS the cable, so the conductor has a row.
        ``None`` when this table does not have it."""
        if any_id in self._spec_by_key:
            return any_id

        conductor_id = any_id
        rows = self.table.select('cable_conductor_id', id=any_id)
        if rows and rows[0][0] is not None:
            conductor_id = rows[0][0]

        if conductor_id in self._spec_by_key:
            return conductor_id

        for cable_id, members in self._cable_members.items():
            if conductor_id in members and cable_id in self._spec_by_key:
                if cable_id not in self._expanded:
                    self._expanded.add(cable_id)
                    self._rebuild()

                return conductor_id if conductor_id in self._spec_by_key else None

        return None

    @_check_types.do
    def _on_activated(self, index: QtCore.QModelIndex) -> None:
        """A double click: a cable's row expands into its conductors (or folds them away again); a wire's row does what a double click
        always did; a conductor's row does nothing."""
        row = self.get_row(index.row())
        if row is None:
            return

        key = row[1]
        spec = self._spec_by_key.get(key)
        kind = spec[1] if spec is not None else _KIND_WIRE

        if kind == _KIND_CONDUCTOR:
            return

        if kind == _KIND_WIRE:
            super()._on_activated(index)
            return

        if key in self._expanded:
            self._expanded.discard(key)
        else:
            self._expanded.add(key)

        self._rebuild()

        wanted = self._row_for_wire(key)
        self._syncing_selection = True
        try:
            if wanted is not None:
                self.selectRow(wanted)
        finally:
            self._syncing_selection = False

        self.wire_selection_synced.emit()

    @_check_types.do
    def _first_text_column(self) -> int | None:
        """The logical column of the first column shown (left to right), after the icon and the hidden id."""
        header = self.horizontalHeader()

        for visual in range(1, header.count()):
            logical = header.logicalIndex(visual)

            if not self.isColumnHidden(logical):
                return logical

        return None

    @_check_types.do
    def _get_cell_text(self, row_id: int, col_id: int) -> str:
        """The cell text. A cable's row says whether it is folded (a triangle before its first column), its conductors are indented."""
        text = self._cell_text(row_id, col_id)

        if row_id < 0 or col_id != self._first_text_column():
            return text

        row = self.rows.get(row_id)
        if row is None:
            return text

        extra = 1 + len(self.column_mapping)
        kind, depth = row[extra + 2], row[extra + 1]

        if kind == _KIND_CABLE:
            return ('\u25bc ' if row[1] in self._expanded else '\u25b6 ') + text

        if depth == 1:
            return '      ' + text

        return text

    @_check_types.do
    def _cell_text(self, row_id: int, col_id: int) -> str:
        """Return the cell text, overriding the 7 computed circuit
        columns with a real value looked up from :class:`PJTCircuit`
        (walking terminals/splices/wire-service-loops in Python) instead
        of the ``NULL`` placeholder the SQL query selected for them. A cable's row has none of them; a conductor's circuit is the
        one of its own row, its cavity and branch those of a wire of its lead.

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

        row = self.get_row(row_id)
        if row is None:
            return ''

        db_id = row[1]
        kind = row[1 + len(self.column_mapping) + 2]

        if kind == _KIND_CABLE:
            return ''

        spec = self._spec_by_key.get(db_id)
        wire_id = spec[2] if spec is not None else db_id

        if col_name == 'cavity_name':
            return self._cavity_names_for_wire(wire_id) if wire_id is not None else ''

        if col_name == 'branch_index':
            return self._branch_indexes_for_wire(wire_id) if wire_id is not None else ''

        # See _get_icon's own comment -- get_row can transiently return a row not yet resolvable via a plain select() here.
        if kind == _KIND_CONDUCTOR:
            circuit_rows = self._wire_db.pjt_cable_conductors_table.select('circuit_id', id=db_id)
        else:
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
    def _branch_indexes_for_wire(self, wire_id: bytes) -> str:
        """The ``branch_id`` of each of this table's transition's
        branches *wire_id* passes through, ascending and joined with
        `` / `` (a wire can enter through one branch and leave through
        another).

        Read from ``pjt_wire_paths`` -- the same source
        ``PJTTransitionBranch.wires`` uses, so this column and the rows
        the table lists can never disagree. Branches of OTHER transitions
        the wire also passes through are ignored.

        :param wire_id: The ``pjt_wires`` row id.
        :type wire_id: bytes
        :returns: e.g. ``'1 / 3'``, or ``''`` if no branch is recorded.
        :rtype: str
        """
        routed_ids = self.table.db.pjt_wire_paths_table.transition_branch_ids_for_wire(wire_id)

        indexes = []
        for branch in self.pegboard_table.anchor.branches:
            if branch.db_id in routed_ids:
                indexes.append(branch.branch_id)

        indexes.sort()

        return ' / '.join(str(index) for index in indexes)

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
    def _get_icon(self, row_id: int) -> QtGui.QIcon | None:
        """Return the picture icon for *row_id*: a plain wire's (single wire, twisted pair / triple, cable or coax) from its
        part; a cable's row the picture of the cable; a conductor's row the picture of that one conductor (its colour, stripe and
        core), same technique as :meth:`WiresPage._get_icon`.

        :param row_id: Visible row index.
        :type row_id: int
        :returns: The swatch icon, or the shared "no image" placeholder.
        :rtype: :class:`PySide6.QtGui.QIcon`
        """
        from ... import logger as _logger
        from ...database.global_db import wire_image as _wire_image

        if row_id < 0:
            return None

        # get_row can race with a row landing in this editor's own scroll buffer (confirmed 2026-09-16: crashed on a brand new
        # peg-board table's very first synchronous paint) -- "no image" instead of assuming a row is always there.
        row = self.get_row(row_id)
        if row is None:
            return None

        db_id = row[1]
        kind = row[1 + len(self.column_mapping) + 2]

        if db_id in self.bitmap_indexes:
            return self.bitmap_indexes[db_id]

        db = self.table.db

        try:
            if kind == _KIND_CONDUCTOR:
                # the conductor's own row is a wire-like row (see PJTCableConductor): its part is the catalog conductor
                icon = _wire_image.build_wire_icon(db.pjt_cable_conductors_table[db_id], 64)
            elif kind == _KIND_CABLE:
                icon = _wire_image.build_wire_icon(db.pjt_cables_table[db_id].part, 64)
            else:
                part_rows = self.table.select('part_id', id=db_id)
                icon = None

                if part_rows:
                    # which picture a wire gets (single wire, twisted pair / triple, jacketed cable, coax) is decided in one place
                    # (wires that look the same share ONE icon object, so this row costs a reference, not a pixmap)
                    icon = _wire_image.build_wire_icon(db.global_db.wires_table[part_rows[0][0]], 64)
        except Exception as exc:  # NOQA
            _logger.error(f'peg-board wire table: could not build the image of a wire: {exc!r}')
            icon = None

        if icon is None:
            icon = _base.EditorList._no_image

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
    def show_column_picker(self, pos: QtCore.QPoint) -> None:
        """Show the add/remove-column checklist inside this table, as
        close to *pos* as fits (see :class:`_ColumnPickerPopup` for why
        it's a plain child widget rather than a ``Qt.Popup`` window).
        Replaces one already open.

        :param pos: Where to place it, in this table's own coordinates.
        :type pos: QPoint
        """
        self.close_column_picker()

        self._picker = _ColumnPickerPopup(
            self, self._visible_def_indices(), self._available_def_indices(),
            self._on_column_toggled)
        self._picker.place_within(self.rect(), pos)
        self._picker.show()
        self._picker.raise_()
        self.appearance_changed.emit()

    @property
    @_check_types.do
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
    def picker_scroll_viewport(self) -> QtWidgets.QWidget | None:
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
    def picker_contains(self, widget: QtWidgets.QWidget | None) -> bool:
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
    def _on_header_context_menu(self, pos: QtCore.QPoint) -> None:
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
            header.setSectionResizeMode(logical, QtWidgets.QHeaderView.ResizeMode.Interactive)
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

        self.wire_selected.emit(wire_id)

        for other in list(WireTable._live_tables):
            if other is self or other.table.db is not self.table.db:
                continue

            try:
                # a table that does not list it must not keep the row it had selected from before
                if other._row_for_wire(wire_id) is None:
                    other._clear_wire()
                else:
                    other._select_wire(wire_id)
            except RuntimeError:
                # underlying C++ widget already destroyed
                WireTable._live_tables.discard(other)

    @_check_types.do
    def _on_row_unselected(self) -> None:
        """The user cleared this table's selection: clear it in every other live table of the project too (they were given the
        selection by :meth:`_on_row_selected`; left selected, a cable's rows there kept the selection colour instead of
        returning to the cable's)."""
        if self._syncing_selection:
            return

        self.wire_deselected.emit()

        for other in list(WireTable._live_tables):
            if other is self or other.table.db is not self.table.db:
                continue

            try:
                other._clear_wire()
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

        # the key of the row *wire_id* is, or is a part of (a piece of wire is its conductor's row; a conductor in a cable that is not
        # expanded here expands it): see _resolve_key
        wire_id = self._resolve_key(wire_id)
        if wire_id is None:
            return None

        where_body, params = self._combined_where()
        where_sql = f'WHERE {where_body}' if where_body else ''

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
        the owning Table to repaint via
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
                          QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible)
        finally:
            self._syncing_selection = False

        self.wire_selection_synced.emit()

    @_check_types.do
    def _clear_wire(self) -> None:
        """Clear this table's selection without telling anyone (guarded like
        :meth:`_select_wire`) and ask the owning Table to repaint."""
        if self.selected is None:
            return

        self._syncing_selection = True
        try:
            self.clearSelection()
        finally:
            self._syncing_selection = False

        self.wire_selection_synced.emit()

    @classmethod
    @_check_types.do
    def mirror_selection(cls, db: "_project_db.PJTTables", wire_id: bytes | None) -> None:
        """Select *wire_id* in every live table of the project *db* that lists
        it -- and clear the selection of every one that does not -- or clear
        them all for ``None``. Used when the wire was picked somewhere that is
        not a wire table (a cable in a concentric section widget), so no table
        has made the selection itself. Nothing is emitted by the tables
        themselves, so this cannot loop back into the wire highlight.

        :param db: The project database the tables belong to.
        :type db: :class:`_project_db.PJTTables`
        :param wire_id: The ``pjt_wires`` row id, or ``None`` for no wire.
        :type wire_id: bytes | None
        """
        for other in list(cls._live_tables):
            if other.table.db is not db:
                continue

            try:
                if wire_id is None or other._row_for_wire(wire_id) is None:
                    other._clear_wire()
                else:
                    other._select_wire(wire_id)
            except RuntimeError:
                # underlying C++ widget already destroyed
                cls._live_tables.discard(other)
