# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# circuit_spreadsheet.py  — v3
#
# Enhanced Circuit Spreadsheet with:
#   • Per-circuit totals  (length, resistance, weight, voltage drop)
#   • Bundle routing path (which bundles each circuit passes through)
#   • Design Rules Check  (overcurrent, voltage drop, wire-size warnings)
#   • Concentric-twist split suggestions (large wire → 2 smaller parallel)
#   • Async DB load (QThread) so the UI never freezes on large projects
#   • Rendered wire visuals  (primary + stripe + stripped conductor end)
#   • Housing thumbnail images in the From/To connector columns
#

from dataclasses import dataclass, field
from typing import Any

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import design_rules as _design_rules
from . import bitmaps as _bitmaps


@dataclass
class CircuitRow:
    """Represent a circuit row in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    circuit_db_id: int = 0
    circuit_num: Any = None
    net_name: str = ""
    notes: str = ""
    from_connector: str = ""
    from_connector_image: QtGui.QPixmap | None = None
    from_pin: str = ""
    to_connectors: str = ""
    to_connector_images: list[QtGui.QPixmap] = field(default_factory=list)
    to_pins: str = ""
    wire_color_primary: str | None = None
    wire_color_stripe: str | None = None
    wire_conductor_material: str | None = None
    wire_gauge_awg: Any = None
    wire_gauge_mm2: Any = None
    od_mm: float | None = None
    num_conductors: int = 1
    total_length_mm: float = 0.0
    total_resistance: float = 0.0
    total_weight_g: float = 0.0
    volts: float = 0.0
    total_load_a: float = 0.0
    voltage_drop_v: float = 0.0
    voltage_drop_pct: float = 0.0
    bundle_names: list[str] = field(default_factory=list)
    issues: list[_design_rules.DRTIssue] = field(default_factory=list)
    worst_severity: _design_rules.Severity = _design_rules.Severity.OK
    suggestions: list[_design_rules.SplitSuggestion] = field(default_factory=list)
    wire_db_ids: list[int] = field(default_factory=list)
    start_terminal_db_id: int | None = None
    end_terminal_db_ids: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------
COL_STATUS = 0
COL_CIRCUIT_NUM = 1
COL_NET_NAME = 2
COL_FROM_CONN = 3
COL_FROM_PIN = 4
COL_TO_CONNS = 5
COL_WIRE_COLOR = 6
COL_GAUGE = 7
COL_LENGTH_MM = 8
COL_RESISTANCE = 9
COL_LOAD_A = 10
COL_V_DROP_PCT = 11
COL_WEIGHT_G = 12
COL_BUNDLES = 13
COL_NOTES = 14

COLUMNS = ["▲", "Circuit #", "Net Name", "From", "Pin", "To", "Wire",
           "Gauge", "Length (mm)", "Resistance (Ω)", "Load (A)",
           "V-Drop %", "Weight (g)", "Bundles", "Notes"]

EDITABLE_COLS = {COL_NET_NAME, COL_NOTES}
NUMERIC_COLS = {COL_LENGTH_MM, COL_RESISTANCE, COL_LOAD_A,
                COL_V_DROP_PCT, COL_WEIGHT_G}


# ---------------------------------------------------------------------------
# Async DB builder
# ---------------------------------------------------------------------------
class _BuildWorker(QtCore.QObject):
    """Represent a build worker in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    # list[CircuitRow]
    finished: QtCore.SignalInstance = QtCore.Signal(list)

    # 0-100
    progress: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, db):
        """Initialise the :class:`_BuildWorker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param db: Database accessor or connection.
        :type db: UNKNOWN
        """
        super().__init__()
        self._db = db

    def run(self):
        """Execute the run operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        rows: list[CircuitRow] = []
        circuits = list(self._db.pjt_circuits_table)
        n = max(len(circuits), 1)

        for i, circuit in enumerate(circuits):
            try:
                row = _build_row(circuit, self._db)
                rows.append(row)
            except Exception:  # NOQA
                pass

            self.progress.emit(int((i + 1) / n * 100))

        for row in rows:
            row.issues = _design_rules.run_drt(row)
            row.suggestions = _design_rules.generate_suggestions(row, self._db)
            row.worst_severity = _design_rules.worst_severity(row.issues)

        self.finished.emit(rows)


def _load_housing_pixmap(housing_obj) -> QtGui.QPixmap | None:
    """
    Try to load a QPixmap from a housing database object.
    Looks for common attribute names used by harness tools:
      .image, .thumbnail, .photo, .picture, .icon
    Each may be a QPixmap, QImage, bytes (PNG/JPEG), or str (file path).
    """

    if housing_obj is None:
        return None

    for attr in ("image", "thumbnail", "photo", "picture", "icon", "pixmap"):
        val = _design_rules.safe(housing_obj, attr)
        if val is None:
            continue

        if isinstance(val, QtGui.QPixmap) and not val.isNull():
            return val

        if isinstance(val, QtGui.QImage) and not val.isNull():
            return QtGui.QPixmap.fromImage(val)

        if isinstance(val, (bytes, bytearray)):
            px = QtGui.QPixmap()
            if px.loadFromData(val):
                return px

        if isinstance(val, str) and val:
            px = QtGui.QPixmap(val)
            if not px.isNull():
                return px

    return None


def _build_row(circuit, db) -> CircuitRow:
    """Build the row.

    UNKNOWN details are inferred from the callable name and signature.

    :param circuit: Value for ``circuit``.
    :type circuit: UNKNOWN
    :param db: Database accessor or connection.
    :type db: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`CircuitRow`
    """
    r = CircuitRow()
    r.circuit_db_id = circuit.db_id
    r.circuit_num = _design_rules.safe(circuit, "circuit_num")
    r.net_name = _design_rules.safe(circuit, "name", "") or ""
    r.notes = _design_rules.safe(circuit, "notes", "") or ""
    r.volts = float(_design_rules.safe(circuit, "volts", 0) or 0)

    # Start terminal
    st = _design_rules.safe(circuit, "start_terminal")
    r.start_terminal_db_id = _design_rules.safe(st, "db_id")
    if st:
        cav = _design_rules.safe(st, "cavity")
        if cav:
            r.from_pin = _design_rules.safe(cav, "name", "") or ""

            h = _design_rules.safe(cav, "housing")
            if h:
                r.from_connector = _design_rules.safe(h, "name", "") or ""
                # ── housing image ──────────────────────────────────
                raw_px = _load_housing_pixmap(h)
                if raw_px:
                    r.from_connector_image = _bitmaps.scale_housing_pixmap(
                        raw_px, _bitmaps.ROW_H)

                else:
                    r.from_connector_image = _bitmaps.placeholder_connector_pixmap(
                        r.from_connector, _bitmaps.ROW_H)

    # End terminals
    to_conns, to_pins = [], []
    seen_housing_names: set[str] = set()

    tmp = _design_rules.safe(circuit, "load_terminals", []) or []

    for et in tmp:
        r.end_terminal_db_ids.append(_design_rules.safe(et, "db_id"))

        r.total_load_a += float(_design_rules.safe(et, "load", 0) or 0)

        vd = float(_design_rules.safe(et, "voltage_drop", 0) or 0)
        if vd > r.voltage_drop_v:
            r.voltage_drop_v = vd

        cav = _design_rules.safe(et, "cavity")
        if cav:
            to_pins.append(_design_rules.safe(cav, "name", "") or "")

            h = _design_rules.safe(cav, "housing")
            if h:
                hname = _design_rules.safe(h, "name", "") or ""
                to_conns.append(hname)

                # ── housing image (deduplicate same housing) ───────
                if hname not in seen_housing_names:
                    seen_housing_names.add(hname)

                    raw_px = _load_housing_pixmap(h)
                    if raw_px:
                        r.to_connector_images.append(
                            _bitmaps.scale_housing_pixmap(
                                raw_px, _bitmaps.ROW_H))
                    else:
                        r.to_connector_images.append(
                            _bitmaps.placeholder_connector_pixmap(
                                hname, _bitmaps.ROW_H))

    r.to_connectors = ", ".join(dict.fromkeys(to_conns))
    r.to_pins = ", ".join(to_pins)

    if r.volts > 0 and r.voltage_drop_v > 0:
        r.voltage_drop_pct = round((r.voltage_drop_v / r.volts) * 100, 2)

    # Wires — sum totals
    wires = _design_rules.safe(circuit, "wires", []) or []
    for w in wires:
        r.wire_db_ids.append(_design_rules.safe(w, "db_id"))
        r.total_length_mm += float(
            _design_rules.safe(w, "length_mm",  0) or 0)

        r.total_resistance += float(
            _design_rules.safe(w, "resistance", 0) or 0)

        r.total_weight_g += float(
            _design_rules.safe(w, "weight_g",   0) or 0)

    r.total_length_mm = round(r.total_length_mm,  2)
    r.total_resistance = round(r.total_resistance, 6)
    r.total_weight_g = round(r.total_weight_g,   4)

    # Wire part info from first wire
    if wires:
        part = _design_rules.safe(wires[0], "part")
        if part:
            clr = _design_rules.safe(part, "color")
            if clr:
                r.wire_color_primary = (
                    _design_rules.safe(clr, "hex_code") or
                    _design_rules.safe(clr, "name"))

            sk = _design_rules.safe(part, "stripe_color")
            if sk:
                r.wire_color_stripe = (
                    _design_rules.safe(sk, "hex_code") or
                    _design_rules.safe(sk, "name"))

            # conductor material (e.g. "copper", "tinned_copper", "aluminium")
            r.wire_conductor_material = (_design_rules.safe(part, "conductor_material") or
                                         _design_rules.safe(part, "conductor") or
                                         _design_rules.safe(part, "material"))

            r.wire_gauge_awg = _design_rules.safe(part, "size_awg")
            r.wire_gauge_mm2 = _design_rules.safe(part, "size_mm2")
            r.od_mm = _design_rules.safe(part, "od_mm")
            r.num_conductors = _design_rules.safe(part, "num_conductors", 1) or 1

    # Bundle routing
    r.bundle_names = _bundles_for_circuit(circuit, db)

    return r


def _bundles_for_circuit(circuit, db) -> list[str]:
    """Execute the bundles for circuit operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param circuit: Value for ``circuit``.
    :type circuit: UNKNOWN
    :param db: Database accessor or connection.
    :type db: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: list[str]
    """
    cw_ids = {_design_rules.safe(w, "db_id")
              for w in (_design_rules.safe(circuit, "wires", []) or [])}

    if not cw_ids:
        return []

    names: list[str] = []
    try:
        for bundle in db.pjt_bundles_table:
            for bw in (_design_rules.safe(bundle, "wires", []) or []):
                pw = _design_rules.safe(bw, "wire")

                if pw and _design_rules.safe(pw, "db_id") in cw_ids:

                    nm = (_design_rules.safe(bundle, "name", "") or
                          f"Bundle {_design_rules.safe(bundle,'db_id')}")

                    if nm not in names:
                        names.append(nm)

                    break

    except Exception:  # NOQA
        pass
    return names


# ---------------------------------------------------------------------------
# Qt Model
# ---------------------------------------------------------------------------
class CircuitTableModel(QtCore.QAbstractTableModel):
    """Represent a circuit table model in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    cell_edited: QtCore.SignalInstance = QtCore.Signal(int, int, object)

    def __init__(self, parent=None):
        """Initialise the :class:`CircuitTableModel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self._rows: list[CircuitRow] = []

    def load(self, rows: list[CircuitRow]):
        """Execute the load operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param rows: Value for ``rows``.
        :type rows: list[CircuitRow]
        """
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def row_at(self, index: QtCore.QModelIndex) -> CircuitRow | None:
        """Execute the row at operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: :class:`QtCore.QModelIndex`
        :returns: Return value. UNKNOWN details.
        :rtype: CircuitRow | None
        """
        r = index.row()

        if 0 <= r < len(self._rows):
            return self._rows[r]

    def rowCount(self, p=QtCore.QModelIndex()):
        """Execute the row count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param p: Value for ``p``.
        :type p: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return len(self._rows)

    def columnCount(self, p=QtCore.QModelIndex()):
        """Execute the column count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param p: Value for ``p``.
        :type p: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return len(COLUMNS)

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
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
            role == QtCore.Qt.ItemDataRole.DisplayRole and
            orientation == QtCore.Qt.Orientation.Horizontal
        ):
            return COLUMNS[section]

        if (
            role == QtCore.Qt.ItemDataRole.FontRole and
            orientation == QtCore.Qt.Orientation.Horizontal
        ):
            f = QtGui.QFont()
            f.setBold(True)
            return f

    def data(self, index: QtCore.QModelIndex,
             role=QtCore.Qt.ItemDataRole.DisplayRole):
        """Execute the data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: :class:`QtCore.QModelIndex`
        :param role: Value for ``role``.
        :type role: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if role in (QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.EditRole):

            if col == COL_STATUS:
                return _design_rules.SEV_ICO[row.worst_severity]

            if col == COL_WIRE_COLOR:
                return None   # drawn by delegate

            if col == COL_FROM_CONN:
                return None   # drawn by delegate

            if col == COL_TO_CONNS:
                return None   # drawn by delegate

            return _cell_text(row, col)

        if role == QtCore.Qt.ItemDataRole.UserRole:
            return row.circuit_db_id

        if role == QtCore.Qt.ItemDataRole.UserRole + 1:
            return row

        if role == QtCore.Qt.ItemDataRole.BackgroundRole:
            if col == COL_STATUS:
                return QtGui.QBrush(
                    QtGui.QColor(_design_rules.SEV_BG[row.worst_severity]))

            return QtGui.QBrush(QtCore.Qt.BrushStyle.NoBrush)

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if col == COL_STATUS:
                return QtGui.QBrush(
                    QtGui.QColor(_design_rules.SEV_FG[row.worst_severity]))

            if col == COL_V_DROP_PCT and row.voltage_drop_pct:
                if row.voltage_drop_pct > _design_rules.MAX_VDROP_PCT:
                    return QtGui.QBrush(QtGui.QColor("#ff7070"))

                if row.voltage_drop_pct > _design_rules.MAX_VDROP_PCT * 0.80:
                    return QtGui.QBrush(QtGui.QColor("#ffd060"))

            if col in EDITABLE_COLS:
                return QtGui.QBrush(QtGui.QColor("#a8d8ff"))

            return QtGui.QBrush(QtGui.QColor("#e0e0e0"))

        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if col in NUMERIC_COLS | {COL_CIRCUIT_NUM, COL_STATUS}:
                return QtCore.Qt.AlignmentFlag.AlignCenter

            return (QtCore.Qt.AlignmentFlag.AlignLeft |
                    QtCore.Qt.AlignmentFlag.AlignVCenter)

        if role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return _cell_tooltip(row, col)

        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        """Execute the set data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :param value: Value to store or process.
        :type value: UNKNOWN
        :param role: Value for ``role``.
        :type role: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.EditRole:
            return False

        row = self._rows[index.row()]
        col = index.column()
        if col not in EDITABLE_COLS:
            return False

        if col == COL_NET_NAME:
            row.net_name = value
        elif col == COL_NOTES:
            row.notes = value

        self.dataChanged.emit(
            index, index, [QtCore.Qt.ItemDataRole.DisplayRole])

        self.cell_edited.emit(row.circuit_db_id, col, value)

        return True

    def flags(self, index):
        """Execute the flags operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        f = (QtCore.Qt.ItemFlag.ItemIsEnabled |
             QtCore.Qt.ItemFlag.ItemIsSelectable |
             QtCore.Qt.ItemFlag.ItemIsDragEnabled |
             QtCore.Qt.ItemFlag.ItemIsDropEnabled)

        if index.column() in EDITABLE_COLS:
            f |= QtCore.Qt.ItemFlag.ItemIsEditable

        return f

    MIME = "application/x-harness-circuit-rows"

    def supportedDropActions(self):
        """Execute the supported drop actions operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return QtCore.Qt.DropAction.MoveAction

    def mimeTypes(self):
        """Execute the mime types operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return [self.MIME]

    def mimeData(self, indexes):
        """Execute the mime data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param indexes: Value for ``indexes``.
        :type indexes: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        seen, payload = set(), []
        for idx in indexes:
            r = idx.row()
            if r not in seen:
                seen.add(r)
                payload.append(f"{self._rows[r].circuit_db_id},{r}")

        m = QtCore.QMimeData()
        m.setData(self.MIME, QtCore.QByteArray(",".join(payload).encode()))

        return m

    def dropMimeData(self, data, action, row, col, parent):
        """Execute the drop mime data operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param data: Data payload.
        :type data: UNKNOWN
        :param action: Value for ``action``.
        :type action: UNKNOWN
        :param row: Value for ``row``.
        :type row: UNKNOWN
        :param col: Value for ``col``.
        :type col: UNKNOWN
        :param parent: Parent object.
        :type parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if not data.hasFormat(self.MIME):
            return False

        toks = bytes(data.data(self.MIME)).decode().split(",")
        pairs = list(zip(toks[::2], toks[1::2]))

        if row >= 0:
            target = row
        else:
            target = len(self._rows)

        moved = [self._rows.pop(int(s)) for _, s in pairs]

        ins = min(target, len(self._rows))
        for item in reversed(moved):
            self._rows.insert(ins, item)

        self.beginResetModel()
        self.endResetModel()

        return True


# ---------------------------------------------------------------------------
# Filter proxy
# ---------------------------------------------------------------------------
class CircuitFilterProxy(QtCore.QSortFilterProxyModel):
    """Represent a circuit filter proxy in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, parent=None):
        """Initialise the :class:`CircuitFilterProxy` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self._text = ""
        self._sev = None
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    def set_filter(self, text: str):
        """Set the filter.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self._text = text.lower()
        self.invalidateFilter()

    def set_severity(self, sev):
        """Set the severity.

        UNKNOWN details are inferred from the callable name and signature.

        :param sev: Value for ``sev``.
        :type sev: UNKNOWN
        """
        self._sev = sev
        self.invalidateFilter()

    def filterAcceptsRow(self, src_row, src_parent):
        """Execute the filter accepts row operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param src_row: Value for ``src_row``.
        :type src_row: UNKNOWN
        :param src_parent: Value for ``src_parent``.
        :type src_parent: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        model = self.sourceModel()
        row: CircuitRow = model.data(
            model.index(src_row, 0, src_parent),
            QtCore.Qt.ItemDataRole.UserRole + 1)

        if row is None:
            return True

        if self._sev and row.worst_severity != self._sev:
            return False

        if not self._text:
            return True

        for col in range(model.columnCount()):
            v = model.data(
                model.index(src_row, col, src_parent),
                QtCore.Qt.ItemDataRole.DisplayRole)

            if v and self._text in str(v).lower():
                return True

        # also search connector names (not in display data)
        for s in (row.from_connector, row.to_connectors):
            if self._text in s.lower():
                return True

        return False


# ---------------------------------------------------------------------------
# ── Delegates ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class WireDelegate(QtWidgets.QStyledItemDelegate):
    """
    Renders a full wire visualisation in the Wire column:
      • Coloured insulation with diagonal stripe bands
      • Stripped end showing conductor metal colour
      • Cylindrical 3-D shading
    Falls back to a "—" label if no colour data is present.
    """
    _MARGIN = 4   # px padding top/bottom around the wire

    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex):
        """Execute the paint operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param painter: Value for ``painter``.
        :type painter: :class:`QtGui.QPainter`
        :param option: Value for ``option``.
        :type option: UNKNOWN
        :param index: Index value.
        :type index: :class:`QtCore.QModelIndex`
        """
        self.initStyleOption(option, index)
        row: CircuitRow = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)

        if row is None:
            super().paint(painter, option, index)
            return

        painter.save()

        # Cell background

        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            bg = option.palette.highlight()
        else:
            bg = QtGui.QBrush(QtGui.QColor("#1e1e1e"))

        painter.fillRect(option.rect, bg)

        if row.wire_color_primary:
            cell_w = option.rect.width()
            cell_h = option.rect.height()
            wire_w = min(cell_w - self._MARGIN * 2, 180)
            wire_h = cell_h - self._MARGIN * 2

            px = _bitmaps.cached_wire_pixmap(row.wire_color_primary,
                                             row.wire_color_stripe,
                                             row.wire_conductor_material,
                                             wire_w, wire_h)

            # Centre pixmap vertically, left-aligned with margin
            draw_x = option.rect.left() + self._MARGIN
            draw_y = option.rect.top() + self._MARGIN
            painter.drawPixmap(draw_x, draw_y, px)
        else:
            painter.setPen(QtGui.QColor("#888"))
            painter.drawText(
                option.rect, QtCore.Qt.AlignmentFlag.AlignCenter, "—")

        painter.restore()

    def sizeHint(self, option, index):
        """Execute the size hint operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param option: Value for ``option``.
        :type option: UNKNOWN
        :param index: Index value.
        :type index: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return QtCore.QSize(190, _bitmaps.ROW_H)


class ConnectorImageDelegate(QtWidgets.QStyledItemDelegate):
    """
    Shows a housing thumbnail (photo or schematic placeholder) plus the
    connector name as a small text label below the image.
    Works for both COL_FROM_CONN and COL_TO_CONNS.
    """
    _PADDING = 3

    @staticmethod
    def _pixmaps_and_name(
        index: QtCore.QModelIndex
    ) -> tuple[list[QtGui.QPixmap], str]:
        """Execute the pixmaps and name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: :class:`QtCore.QModelIndex`
        :returns: Return value. UNKNOWN details.
        :rtype: tuple[list[QtGui.QPixmap], str]
        """

        row: CircuitRow = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)
        if row is None:
            return [], ""

        col = index.column()
        if col == COL_FROM_CONN:
            if row.from_connector_image:
                imgs = [row.from_connector_image]
            else:
                imgs = []

            name = row.from_connector
        else:  # COL_TO_CONNS
            imgs = row.to_connector_images
            name = row.to_connectors

        return imgs, name

    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex):
        """Execute the paint operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param painter: Value for ``painter``.
        :type painter: :class:`QtGui.QPainter`
        :param option: Value for ``option``.
        :type option: UNKNOWN
        :param index: Index value.
        :type index: :class:`QtCore.QModelIndex`
        """
        self.initStyleOption(option, index)
        row: CircuitRow = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)
        if row is None:
            super().paint(painter, option, index)
            return

        imgs, name = self._pixmaps_and_name(index)

        painter.save()

        # Background
        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            bg = option.palette.highlight()
        else:
            bg = QtGui.QBrush(QtGui.QColor("#1e1e1e"))

        painter.fillRect(option.rect, bg)

        p = self._PADDING
        r = option.rect.adjusted(p, p, -p, -p)
        x = r.left()

        if imgs:
            for px in imgs:
                if px and not px.isNull():
                    draw_y = r.top() + max(0, (r.height() - px.height()) // 2)
                    painter.drawPixmap(x, draw_y, px)
                    x += px.width() + 3
        else:
            # No image at all — draw connector name as text
            painter.setPen(QtGui.QColor("#c8c8c8"))
            f = QtGui.QFont("monospace", 9)
            painter.setFont(f)
            painter.drawText(
                r, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                name or "—")

        painter.restore()

    def sizeHint(self, option, index):
        """Execute the size hint operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param option: Value for ``option``.
        :type option: UNKNOWN
        :param index: Index value.
        :type index: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        imgs, _ = self._pixmaps_and_name(index)
        total_w = sum((px.width() if px else 0) for px in imgs)
        total_w += max(0, len(imgs) - 1) * 3 + self._PADDING * 2

        return QtCore.QSize(max(total_w, 80), _bitmaps.ROW_H)


class NumericDelegate(QtWidgets.QStyledItemDelegate):
    """Represent a numeric delegate in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def displayText(self, value, locale):
        """Execute the display text operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        :param locale: Value for ``locale``.
        :type locale: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        try:
            f = float(value)
            if f != int(f):
                return f"{f:.3f}"

            return str(int(f))

        except (TypeError, ValueError):
            if value is not None:
                return str(value)

            return "—"


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------
class CircuitDetailPanel(QtWidgets.QWidget):
    """Represent a circuit detail panel in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, parent=None):
        """Initialise the :class:`CircuitDetailPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self.setStyleSheet("background:#1e1e1e; color:#e0e0e0;")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._title = QtWidgets.QLabel("No circuit selected")
        self._title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#ccc;")

        layout.addWidget(self._title)

        # Wire preview in detail panel
        self._wire_preview = QtWidgets.QLabel()
        self._wire_preview.setFixedHeight(_bitmaps.ROW_H + 8)

        self._wire_preview.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft |
            QtCore.Qt.AlignmentFlag.AlignVCenter)

        self._wire_preview.setStyleSheet(
            "background:#121212; border-radius:4px; padding:4px;")

        layout.addWidget(self._wire_preview)

        tabs = self._tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #3a3a3a; background:#1e1e1e; }
            QTabBar::tab { background:#2d2d2d; color:#aaa; padding:4px 12px; }
            QTabBar::tab:selected { background:#1e1e1e; color:#fff;
                                    border-bottom:2px solid #4a8fff; }
        """)

        layout.addWidget(tabs)

        def _te():
            """Execute the te operation.

            UNKNOWN details are inferred from the callable name and signature.

            :returns: Return value. UNKNOWN details.
            :rtype: UNKNOWN
            """
            w = QtWidgets.QTextEdit()
            w.setReadOnly(True)
            w.setStyleSheet(
                "background:#1e1e1e; color:#e0e0e0; border:none; "
                "font-family:monospace; font-size:11px;")

            return w

        self._totals = _te()
        tabs.addTab(self._totals,  "Totals & Routing")
        self._drt = QtWidgets.QTreeWidget()
        self._drt.setHeaderHidden(True)
        self._drt.setColumnCount(1)
        self._drt.setStyleSheet("QTreeWidget { background:#1e1e1e; color:#e0e0e0;"
                                " border:none; } "
                                "QTreeWidget::item:selected { background:#2a4a7f; }")

        tabs.addTab(self._drt, "DRT Issues")
        self._sugg = _te()
        tabs.addTab(self._sugg,    "Suggestions")

    # ── Housing image panel ───────────────────────────────────────────
    @staticmethod
    def _make_connector_strip(row: CircuitRow) -> QtGui.QPixmap | None:
        """Compose From + To housing thumbnails side by side."""

        all_px: list[QtGui.QPixmap] = []
        if row.from_connector_image and not row.from_connector_image.isNull():
            all_px.append(row.from_connector_image)

        for px in row.to_connector_images:
            if px and not px.isNull():
                all_px.append(px)

        if not all_px:
            return None

        gap = 8
        total_w = sum(p.width() for p in all_px) + gap * (len(all_px) - 1)
        total_h = max(p.height() for p in all_px)
        comp = QtGui.QPixmap(total_w, total_h)
        comp.fill(QtCore.Qt.GlobalColor.transparent)
        ptr = QtGui.QPainter(comp)
        x = 0
        for p in all_px:
            ptr.drawPixmap(x, (total_h - p.height()) // 2, p)
            x += p.width() + gap

        ptr.end()

        return comp

    def show_row(self, row: CircuitRow | None):
        """Show the row.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: CircuitRow | None
        """
        if row is None:
            self._title.setText("No circuit selected")
            self._wire_preview.clear()
            self._totals.clear()
            self._drt.clear()
            self._sugg.clear()

            return

        name = row.net_name or f"Circuit {row.circuit_num}"
        self._title.setText(f"  {name}")

        # ── Wire preview ──────────────────────────────────────────────
        if row.wire_color_primary:
            px = _bitmaps.cached_wire_pixmap(row.wire_color_primary,
                                             row.wire_color_stripe,
                                             row.wire_conductor_material,
                                             width=320, height=_bitmaps.ROW_H)

            self._wire_preview.setPixmap(px)
            mat = row.wire_conductor_material or "copper"
            self._wire_preview.setToolTip(f"Primary: {row.wire_color_primary}\n"
                                          f"Stripe:  {row.wire_color_stripe or 'none'}\n"
                                          f"Conductor: {mat}")
        else:
            self._wire_preview.clear()

        # ── Totals ────────────────────────────────────────────────────
        awg = _design_rules.resolve_awg(row.wire_gauge_awg, row.wire_gauge_mm2)

        in_bun = bool(row.bundle_names)
        amp_line = ""
        if awg is not None:
            amp = _design_rules.AWG_AMPACITY.get(awg)
            if amp:
                lim = amp[0] if in_bun else amp[1]
                margin = lim - row.total_load_a
                amp_line = (f"  {'Ampacity (' + ('bundled' if in_bun else 'open-air')+')':<26}"
                            f" {lim:.1f} A   margin {margin:+.2f} A\n")

        lm = row.total_length_mm / 1000
        txt = (
            f"  {'Wire gauge:':<28} {row.wire_gauge_awg} AWG  /  {row.wire_gauge_mm2} mm²\n"
            f"  {'Conductor:':<28} {row.wire_conductor_material or 'unknown'}\n"
            f"  {'OD:':<28} {row.od_mm:.2f} mm\n"
            f"  {'Conductors:':<28} {row.num_conductors}\n\n"
            f"  {'Total length:':<28} {row.total_length_mm:.1f} mm\n"
            f"  {'':28} {lm:.4f} m   /   {lm*3.28084:.4f} ft\n\n"
            f"  {'Total resistance:':<28} {row.total_resistance:.6f} Ω\n"
            f"  {'Total weight:':<28} {row.total_weight_g:.4f} g\n\n"
            f"  {'System voltage:':<28} {row.volts:.1f} V\n"
            f"  {'Total load:':<28} {row.total_load_a:.3f} A\n"
            f"  {'Voltage drop:':<28} {row.voltage_drop_v:.4f} V  "
            f"({row.voltage_drop_pct:.2f} %)\n"
            f"{amp_line}\n"
            f"  {'From:':<28} {row.from_connector}  pin {row.from_pin}\n"
            f"  {'To:':<28} {row.to_connectors}\n"
            f"  {'Pins:':<28} {row.to_pins}\n\n"
            f"  {'Bundles traversed:':<28} "
            f"{', '.join(row.bundle_names) or 'None (free wire)'}\n"
        )
        self._totals.setPlainText(txt)

        # ── DRT ───────────────────────────────────────────────────────
        self._drt.clear()
        if not row.issues:
            item = QtWidgets.QTreeWidgetItem(["✓  No design rule violations"])
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(
                _design_rules.SEV_FG[_design_rules.Severity.OK])))

            self._drt.addTopLevelItem(item)
            self._tabs.setTabText(1, "DRT Issues")
        else:
            for iss in row.issues:
                item = QtWidgets.QTreeWidgetItem(
                    [f"{_design_rules.SEV_ICO[iss.severity]}  [{iss.code}]  {iss.message}"])

                item.setForeground(0, QtGui.QBrush(
                    QtGui.QColor(_design_rules.SEV_FG[iss.severity])))

                self._drt.addTopLevelItem(item)

            ec = sum(1 for i in row.issues
                     if i.severity == _design_rules.Severity.ERROR)

            wc = sum(1 for i in row.issues
                     if i.severity == _design_rules.Severity.WARNING)

            self._tabs.setTabText(
                1, f"DRT Issues  ({ec}✕  {wc}⚠)" if (ec or wc) else "DRT Issues")

        # ── Suggestions ───────────────────────────────────────────────
        if not row.suggestions:
            self._sugg.setPlainText("No concentric-twist split suggestions.")
            self._tabs.setTabText(2, "Suggestions")
        else:
            lines = []
            for i, s in enumerate(row.suggestions, 1):
                lines += [
                    f"Suggestion {i}:",
                    f"  {s.reason}",
                    f"",
                    f"  Split:  1 × {s.original_awg} AWG ({s.original_mm2} mm²)",
                    f"      →   {s.num_parallel} × {s.suggested_awg} AWG "
                    f"({s.suggested_mm2} mm² each)",
                    f"  Combined area: {s.combined_mm2} mm²  "
                    f"(original: {s.original_mm2} mm²)",
                    "",
                ]
            self._sugg.setPlainText("\n".join(lines))
            self._tabs.setTabText(2, f"Suggestions ({len(row.suggestions)})")


# ---------------------------------------------------------------------------
# Table view
# ---------------------------------------------------------------------------
_TABLE_STYLE = """
    QTableView {
        background:#1e1e1e; alternate-background-color:#252525;
        color:#e0e0e0; gridline-color:#3a3a3a;
        selection-background-color:#2a4a7f; selection-color:#fff;
        font-size:12px;
    }
    QTableView::item:hover { background:#2e3e50; }
    QHeaderView::section {
        background:#2d2d2d; color:#ccc; border:1px solid #3a3a3a;
        padding:4px; font-weight:bold;
    }
    QScrollBar:vertical   { background:#1a1a1a; width:12px; }
    QScrollBar::handle:vertical { background:#444; border-radius:4px; }
    QScrollBar:horizontal { background:#1a1a1a; height:12px; }
    QScrollBar::handle:horizontal { background:#444; border-radius:4px; }
"""


class CircuitTableView(QtWidgets.QTableView):
    """Represent a circuit table view in :mod:`harness_designer.ui.editor_ciruit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    row_selected: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, mainframe, parent=None):
        """Initialise the :class:`CircuitTableView` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self._mainframe = mainframe
        self.setStyleSheet(_TABLE_STYLE)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setSortingEnabled(True)
        self.setWordWrap(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        vh = self.verticalHeader()
        vh.setDefaultSectionSize(_bitmaps.ROW_H)
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)
        vh.setVisible(False)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(
            COL_STATUS, QtWidgets.QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(COL_STATUS, 28)

        for col in (COL_NET_NAME, COL_BUNDLES, COL_NOTES):
            hh.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.Stretch)

        for col in (COL_CIRCUIT_NUM, COL_FROM_PIN,
                    COL_GAUGE, COL_LOAD_A, COL_V_DROP_PCT):

            hh.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        # Give connector and wire columns a reasonable fixed width
        self.setColumnWidth(COL_FROM_CONN, 120)
        self.setColumnWidth(COL_TO_CONNS, 160)
        self.setColumnWidth(COL_WIRE_COLOR, 190)

    def selectionChanged(self, selected, deselected):
        """Execute the selection changed operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        :param deselected: Value for ``deselected``.
        :type deselected: UNKNOWN
        """
        super().selectionChanged(selected, deselected)
        idxs = self.selectionModel().selectedRows()
        if not idxs:
            self.row_selected.emit(None)
            return

        proxy = self.model()

        if isinstance(proxy, QtCore.QSortFilterProxyModel):
            si = proxy.mapToSource(idxs[0])
            sm = proxy.sourceModel()
        else:
            si = idxs[0]
            sm = proxy

        self.row_selected.emit(sm.data(si, QtCore.Qt.ItemDataRole.UserRole + 1))


# ---------------------------------------------------------------------------
# Dock
# ---------------------------------------------------------------------------
class EditorCircuitPanel(QtWidgets.QDockWidget):
    """
    Usage in mainframe.py:
        from .circuit_spreadsheet.circuit_spreadsheet import CircuitSpreadsheetDock
        self._circuit_dock = CircuitSpreadsheetDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._circuit_dock)
        # after project opens:
        self._circuit_dock.load_project(self.project_db)
    """

    def __init__(self, mainframe):
        """Initialise the :class:`EditorCircuitPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        super().__init__("Circuit Editor", mainframe)
        self._mainframe = mainframe
        self._project_db = None
        self._thread = None
        self._worker = None
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)

        self._model = CircuitTableModel(self)
        self._model.cell_edited.connect(self._on_cell_edited)

        self._proxy = CircuitFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        self._wire_delegate = WireDelegate(self)
        self._conn_from_delegate = ConnectorImageDelegate(self)
        self._conn_to_delegate = ConnectorImageDelegate(self)

        self._view = CircuitTableView(mainframe, self)
        self._view.setModel(self._proxy)
        self._view.row_selected.connect(self._on_row_selected)
        self._view.setItemDelegateForColumn(
            COL_WIRE_COLOR, self._wire_delegate)

        self._view.setItemDelegateForColumn(
            COL_FROM_CONN, self._conn_from_delegate)

        self._view.setItemDelegateForColumn(
            COL_TO_CONNS, self._conn_to_delegate)

        for col in NUMERIC_COLS:
            self._view.setItemDelegateForColumn(col, NumericDelegate(self))

        self._detail = CircuitDetailPanel()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._view)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([700, 300])
        splitter.setStyleSheet(
            "QSplitter::handle { background:#3a3a3a; width:2px; }")

        self._progress = QtWidgets.QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background:#1a1a1a; border:none; }"
            "QProgressBar::chunk { background:#4a8fff; }")

        self._progress.hide()

        self._count_label = QtWidgets.QLabel("0 circuits  ")
        self._count_label.setStyleSheet("color:#888; padding-right:6px;")

        container = QtWidgets.QWidget()
        container.setStyleSheet("background:#1e1e1e;")
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        lay.addWidget(splitter, 1)
        lay.addWidget(self._progress)
        self.setWidget(container)

        self._model.modelReset.connect(self._update_count)
        self._proxy.rowsInserted.connect(self._update_count)
        self._proxy.rowsRemoved.connect(self._update_count)

    # ── Public ────────────────────────────────────────────────────────
    def load_project(self, project_db):
        """Load the project.

        UNKNOWN details are inferred from the callable name and signature.

        :param project_db: Value for ``project_db``.
        :type project_db: UNKNOWN
        """
        self._project_db = project_db
        self.refresh()

    def refresh(self):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._project_db is None:
            self._model.clear()
            return

        if self._thread and self._thread.isRunning():
            return

        # flush stale pixmaps on reload
        _bitmaps.WIRE_PIXMAP_CACHE.clear()

        self._progress.setValue(0)
        self._progress.show()
        self._thread = QtCore.QThread(self)
        self._worker = _BuildWorker(self._project_db)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)  # NOQA
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def highlight_circuit(self, circuit_db_id: int):
        """Execute the highlight circuit operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param circuit_db_id: Identifier for the circuit database.
        :type circuit_db_id: int
        """
        self._view.clearSelection()
        for r in range(self._model.rowCount()):
            if self._model.data(self._model.index(r, 0),
                                QtCore.Qt.ItemDataRole.UserRole) == circuit_db_id:

                pi = self._proxy.mapFromSource(self._model.index(r, 0))

                if pi.isValid():
                    self._view.selectRow(pi.row())
                    self._view.scrollTo(pi)

                break

    # ── Private ───────────────────────────────────────────────────────
    def _build_toolbar(self) -> QtWidgets.QToolBar:
        """Build the toolbar.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QtWidgets.QToolBar`
        """
        tb = QtWidgets.QToolBar()
        tb.setMovable(False)
        tb.setStyleSheet(
            "QToolBar { background:#2a2a2a; border:none; spacing:4px; padding:2px; }"
            "QToolButton { color:#ccc; padding:3px 8px; border-radius:3px; border:none; }"
            "QToolButton:hover { background:#3a3a3a; }"
        )

        tb.addWidget(QtWidgets.QLabel("  Filter: "))
        fe = self._filter_edit = QtWidgets.QLineEdit()
        fe.setPlaceholderText("Search circuits…")
        fe.setMaximumWidth(200)
        fe.setStyleSheet("QLineEdit { background:#1e1e1e; color:#ddd;"
                         " border:1px solid #555; border-radius:3px; padding:2px 6px; }")

        fe.textChanged.connect(self._proxy.set_filter)
        tb.addWidget(fe)

        tb.addSeparator()
        tb.addWidget(QtWidgets.QLabel("  Show: "))
        sc = self._sev_combo = QtWidgets.QComboBox()
        sc.setStyleSheet("QComboBox { background:#2d2d2d; color:#ccc;"
                         " border:1px solid #555; border-radius:3px; padding:2px 6px; }"
                         "QComboBox QAbstractItemView { background:#2d2d2d; color:#ccc; }")

        sc.addItems(["All", "✕ Errors only", "⚠ Warnings+", "ℹ Info+"])
        sc.currentIndexChanged.connect(self._on_sev_changed)
        tb.addWidget(sc)

        tb.addSeparator()
        act = QtGui.QAction("⟳ Refresh", self)
        act.triggered.connect(self.refresh)
        tb.addAction(act)
        act2 = QtGui.QAction("✕ Clear", self)
        act2.triggered.connect(self._view.clearSelection)
        tb.addAction(act2)

        sp = QtWidgets.QWidget()
        sp.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred)

        tb.addWidget(sp)
        tb.addWidget(self._count_label)
        return tb

    def _on_sev_changed(self, idx: int):
        """Handle the sev changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param idx: Value for ``idx``.
        :type idx: int
        """
        self._proxy.set_severity(
            {0: None, 1: _design_rules.Severity.ERROR,
             2: _design_rules.Severity.WARNING,
             3: _design_rules.Severity.INFO}.get(idx))

    def _on_loaded(self, rows: list[CircuitRow]):
        """Handle the loaded event.

        UNKNOWN details are inferred from the callable name and signature.

        :param rows: Value for ``rows``.
        :type rows: list[CircuitRow]
        """
        self._model.load(rows)
        self._view.resizeColumnsToContents()
        # Re-enforce minimum widths for visual columns after resize
        self._view.setColumnWidth(
            COL_WIRE_COLOR, max(self._view.columnWidth(COL_WIRE_COLOR), 190))

        self._view.setColumnWidth(
            COL_FROM_CONN, max(self._view.columnWidth(COL_FROM_CONN), 100))

        self._view.setColumnWidth(
            COL_TO_CONNS, max(self._view.columnWidth(COL_TO_CONNS), 130))

        self._progress.hide()
        self._update_count()

    def _on_row_selected(self, row: CircuitRow | None):
        """Handle the row selected event.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: CircuitRow | None
        """
        self._detail.show_row(row)
        if row is None:
            return

        project = self._mainframe.project
        if project is None:
            return

        obj = _find_obj(project, "circuits", row.circuit_db_id)
        if obj:
            self._mainframe.set_selected(obj)

        for wid in row.wire_db_ids:
            wo = _find_obj(project, "wires", wid)
            if wo:
                wo.identify([0.2, 0.6, 1.0, 1.0])

    def _on_cell_edited(self, circuit_db_id: int, col: int, value: Any):
        """Handle the cell edited event.

        UNKNOWN details are inferred from the callable name and signature.

        :param circuit_db_id: Identifier for the circuit database.
        :type circuit_db_id: int
        :param col: Value for ``col``.
        :type col: int
        :param value: Value to store or process.
        :type value: :class:`Any`
        """
        if self._project_db is None:
            return
        try:
            c = self._project_db.pjt_circuits_table[circuit_db_id]
        except (KeyError, IndexError):
            return

        if col == COL_NET_NAME:
            c.name = str(value)

        elif col == COL_NOTES:
            c.notes = str(value)

    def _update_count(self):
        """Update the count.

        UNKNOWN details are inferred from the callable name and signature.
        """
        n = self._proxy.rowCount()
        errs = sum(
            1 for r in range(self._model.rowCount())
            if (
                self._model.data(self._model.index(r, 0), QtCore.Qt.ItemDataRole.UserRole + 1) or
                CircuitRow().worst_severity == _design_rules.Severity.ERROR))

        label = f"  {n} circuit{'s' if n!=1 else ''}"
        if errs:
            label += f"  ·  {errs} ✕ error{'s' if errs!=1 else ''}  "

        self._count_label.setText(label)
        self._count_label.setStyleSheet(
            "color:#ff7070; padding-right:6px;" if errs else "color:#888; padding-right:6px;")


# ---------------------------------------------------------------------------
# Cell text / tooltip helpers
# ---------------------------------------------------------------------------
def _cell_text(row: CircuitRow, col: int) -> str:
    """Execute the cell text operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param row: Value for ``row``.
    :type row: :class:`CircuitRow`
    :param col: Value for ``col``.
    :type col: int
    :returns: Return value. UNKNOWN details.
    :rtype: str
    """
    m = {
        COL_CIRCUIT_NUM: row.circuit_num,
        COL_NET_NAME: row.net_name,
        COL_FROM_CONN: None,   # handled by delegate
        COL_FROM_PIN: row.from_pin,
        COL_TO_CONNS: None,   # handled by delegate
        COL_WIRE_COLOR: None,   # handled by delegate
        COL_GAUGE: _gauge(row),
        COL_LENGTH_MM: row.total_length_mm,
        COL_RESISTANCE: row.total_resistance,
        COL_LOAD_A: row.total_load_a or None,
        COL_V_DROP_PCT: f"{row.voltage_drop_pct:.1f}%" if row.voltage_drop_pct else None,
        COL_WEIGHT_G: row.total_weight_g,
        COL_BUNDLES: ", ".join(row.bundle_names) if row.bundle_names else "—",
        COL_NOTES: row.notes,
    }
    v = m.get(col)

    return "" if v is None else str(v)


def _gauge(row: CircuitRow) -> str:
    """Execute the gauge operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param row: Value for ``row``.
    :type row: :class:`CircuitRow`
    :returns: Return value. UNKNOWN details.
    :rtype: str
    """
    p = []
    if row.wire_gauge_awg is not None:
        p.append(f"{row.wire_gauge_awg} AWG")

    if row.wire_gauge_mm2 is not None:
        p.append(f"{row.wire_gauge_mm2} mm²")

    return " / ".join(p)


def _cell_tooltip(row: CircuitRow, col: int) -> str:
    """Execute the cell tooltip operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param row: Value for ``row``.
    :type row: :class:`CircuitRow`
    :param col: Value for ``col``.
    :type col: int
    :returns: Return value. UNKNOWN details.
    :rtype: str
    """
    if col in EDITABLE_COLS:
        return "Double-click to edit"

    if col == COL_LENGTH_MM and row.total_length_mm:
        mm = row.total_length_mm

        return (f"{mm:.1f} mm  ·  {mm/25.4:.3f} in  "
                f"·  {mm/304.8:.4f} ft  ·  {mm/1000:.4f} m")

    if col == COL_V_DROP_PCT:
        return (f"Drop: {row.voltage_drop_v:.4f} V  ({row.voltage_drop_pct:.2f} %)\n"
                f"Limit: {_design_rules.MAX_VDROP_PCT:.0f} %  on {row.volts:.1f} V")

    if col == COL_STATUS and row.issues:
        return "\n".join(f"{_design_rules.SEV_ICO[i.severity]} {i.message}" for i in row.issues)

    if col == COL_BUNDLES and row.bundle_names:
        return "Bundles traversed:\n" + "\n".join(f"  • {b}" for b in row.bundle_names)

    if col == COL_GAUGE:
        awg = _design_rules.resolve_awg(row.wire_gauge_awg, row.wire_gauge_mm2)
        if awg is not None:
            amp = _design_rules.AWG_AMPACITY.get(awg)
            if amp:
                in_bun = bool(row.bundle_names)
                return (f"Bundled ampacity:   {amp[0]:.1f} A\n"
                        f"Open-air ampacity:  {amp[1]:.1f} A\n"
                        f"Currently:  {'bundled' if in_bun else 'open air'}")

    if col == COL_WIRE_COLOR:
        parts = []
        if row.wire_color_primary:
            parts.append(f"Primary:   {row.wire_color_primary}")

        if row.wire_color_stripe:
            parts.append(f"Stripe:    {row.wire_color_stripe}")

        mat = row.wire_conductor_material
        if mat:
            parts.append(f"Conductor: {mat}")

        return "\n".join(parts) if parts else ""

    if col == COL_FROM_CONN:
        return row.from_connector or ""

    if col == COL_TO_CONNS:
        return row.to_connectors or ""

    return ""


def _find_obj(project, collection: str, db_id: int):
    """Find the obj.

    UNKNOWN details are inferred from the callable name and signature.

    :param project: Value for ``project``.
    :type project: UNKNOWN
    :param collection: Value for ``collection``.
    :type collection: str
    :param db_id: Identifier for the database.
    :type db_id: int
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    try:
        for obj in getattr(project, collection, []):
            if hasattr(obj, "db_obj") and obj.db_obj.db_id == db_id:
                return obj

    except Exception:  # NOQA
        pass
