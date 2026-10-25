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

import functools
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Union as _Union

from PySide6 import QtCore, QtGui, QtWidgets

from . import design_rules as _design_rules
from . import bitmaps as _bitmaps
from ... import check_types as _check_types
from ... import logger as _logger
from ... import image as _image
from ...database import id_generator as _id_generator

if TYPE_CHECKING:
    from .. import mainframe as _mainframe
    from ...database import project_db as _project_db
    from ...database.project_db import pjt_circuit as _pjt_circuit
    from ...database.project_db import pjt_housing as _pjt_housing
    from ...objects import circuit as _circuit
    from ...objects import wire as _wire


# Errors already written to the log, so a failure that repeats (a paint, per cell) is reported once.
_REPORTED: set[tuple[str, str]] = set()


def _guarded(fallback: Any = None):
    """For what Qt calls into the dock (slots, paint, data, sort and filter overrides).

    An exception that escapes one of those reaches ``run.py``'s hook, and PySide6 in this build aborts the process
    right after it (the hook's own comment says so). A table of circuits is not worth the user's unsaved work, so the
    failure is written to the log, with its traceback and once per distinct failure, and *fallback* is returned (called,
    when it is callable) so the dock carries on without that one thing.

    :param fallback: What to return after a failure, or a callable that makes it.
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # NOQA
                key = (func.__qualname__, repr(exc))

                if key not in _REPORTED:
                    _REPORTED.add(key)
                    _logger.error(f"circuit editor: {func.__qualname__} failed: {exc!r}\n{traceback.format_exc()}")

                return fallback() if callable(fallback) else fallback

        return wrapper

    return decorate


# The size of a wire's picture in the table, and in the panel on the right.
WIRE_TABLE_SIZE = (100, 25)
WIRE_PANEL_SIZE = (200, 50)


@dataclass
class WireInfo:
    """One distinct wire part used in a circuit.

    A circuit does not use one wire throughout: where it branches off a splice or another terminal the wire can change gauge, colour or
    construction. Wires and wire service loops made of the same part are one entry, in the order the circuit meets them, with what is
    specific to that part and the totals of the members that use it.
    """
    part_db_id: bytes | None = None
    part_number: str = ""
    wires: int = 0
    loops: int = 0
    length_mm: float = 0.0
    resistance: float = 0.0
    weight_g: float = 0.0
    max_amps: float = 0.0
    bundled: bool = False
    gauge_awg: Any = None
    gauge_mm2: Any = None
    od_mm: float | None = None
    num_conductors: int = 1
    shielded: bool = False
    insulation: str | None = None
    color_primary: str | None = None
    color_stripe: str | None = None
    conductor: str | None = None
    # from images.build_wire, as QImage (drawn on the worker thread, where that is safe); _on_loaded and show_row make QPixmaps
    table_image: QtGui.QImage | QtGui.QPixmap | None = None
    panel_image: QtGui.QImage | QtGui.QPixmap | None = None


@dataclass
class CircuitRow:
    """Represent a circuit row in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    circuit_db_id: bytes | None = None
    circuit_num: Any = None
    net_name: str = ""
    notes: str = ""
    from_connector: str = ""
    # drawn on the worker thread as QImage, which is safe there; _on_loaded makes them QPixmap on the GUI thread
    from_connector_image: QtGui.QImage | QtGui.QPixmap | None = None
    from_pin: str = ""
    to_connectors: str = ""
    to_connector_images: list[QtGui.QImage | QtGui.QPixmap] = field(default_factory=list)
    to_pins: str = ""
    # the FIRST wire's description, which the design rules fall back on; every distinct wire is in ``wires``
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
    bundle_db_ids: list[bytes] = field(default_factory=list)
    issues: list[_design_rules.DRTIssue] = field(default_factory=list)
    worst_severity: _design_rules.Severity = _design_rules.Severity.OK
    suggestions: list[_design_rules.SplitSuggestion] = field(default_factory=list)
    # what the solver finds, for the design rules (see _build_row)
    wire_loads: list[_design_rules.WireLoad] = field(default_factory=list)
    hot_parts: list[_design_rules.HotPart] = field(default_factory=list)
    drop_checks: list[_design_rules.DropCheck] = field(default_factory=list)
    max_wire_amps: float = 0.0
    wire_db_ids: list[bytes] = field(default_factory=list)
    # every distinct wire part of the circuit (wires and wire service loops), see WireInfo
    wires: list[WireInfo] = field(default_factory=list)
    start_terminal_db_id: bytes | None = None
    end_terminal_db_ids: list[bytes] = field(default_factory=list)
    # set when the circuit could not be read: the row stands in for it, saying so
    build_error: str = ""


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------
COL_STATUS = 0
COL_CIRCUIT_NUM = 1
COL_NET_NAME = 2
COL_FROM_CONN = 3
COL_FROM_PIN = 4
COL_TO_CONNS = 5
COL_TO_PIN = 6
COL_WIRE_COLOR = 7
COL_GAUGE = 8
COL_LENGTH_MM = 9
COL_RESISTANCE = 10
COL_LOAD_A = 11
COL_V_DROP_PCT = 12
COL_WEIGHT_G = 13
COL_BUNDLES = 14
COL_NOTES = 15

COLUMNS = ["▲", "Circuit #", "Net Name", "From", "From Pin", "To", "To Pin", "Wire",
           "Gauge", "Length (mm)", "Resistance (Ω)", "Load (A)",
           "V-Drop %", "Weight (g)", "Bundles", "Notes"]

EDITABLE_COLS = {COL_NET_NAME, COL_NOTES}
NUMERIC_COLS = {COL_LENGTH_MM, COL_RESISTANCE, COL_LOAD_A,
                COL_V_DROP_PCT, COL_WEIGHT_G}


@_check_types.do
def _number(value: Any) -> float:
    """A cell's value as a number to sort by; 0.0 for anything that is not one."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


_SEVERITY_ORDER = {severity: place for place, severity in enumerate(_design_rules.Severity)}

# What each sortable column is ordered by. The cells hold text, and as text "10" comes before "9".
_SORT_KEYS = {
    COL_STATUS: lambda row: _SEVERITY_ORDER[row.worst_severity],
    COL_CIRCUIT_NUM: lambda row: _number(row.circuit_num),
    COL_LENGTH_MM: lambda row: row.total_length_mm,
    COL_RESISTANCE: lambda row: row.total_resistance,
    COL_LOAD_A: lambda row: row.total_load_a,
    COL_V_DROP_PCT: lambda row: row.voltage_drop_pct,
    COL_WEIGHT_G: lambda row: row.total_weight_g
}


# ---------------------------------------------------------------------------
# Async DB builder
# ---------------------------------------------------------------------------
class _BuildWorker(QtCore.QObject):
    """Represent a build worker in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    # list[CircuitRow]
    finished: QtCore.SignalInstance = QtCore.Signal(list)

    # 0-100
    progress: QtCore.SignalInstance = QtCore.Signal(int)

    @_check_types.do
    def __init__(self, db: "_project_db.PJTTables"):
        """Initialise the :class:`_BuildWorker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param db: Database accessor or connection.
        :type db: UNKNOWN
        """
        super().__init__()
        self._db = db

    @_check_types.do
    def run(self) -> None:
        """Execute the run operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        rows: list[CircuitRow] = []

        try:
            circuits = list(self._db.pjt_circuits_table)
            n = max(len(circuits), 1)

            for i, circuit in enumerate(circuits):
                try:
                    rows.append(_build_row(circuit, self._db))
                except Exception as exc:  # NOQA
                    # a circuit that cannot be read gets a row that says so, not a silent gap in the table
                    _logger.error(f"circuit editor: could not read circuit {circuit.db_id!r}: {exc!r}")
                    rows.append(_failed_row(circuit, exc))

                self.progress.emit(int((i + 1) / n * 100))

            for row in rows:
                if row.build_error:
                    continue

                try:
                    row.issues = _design_rules.run_drt(row)
                    row.suggestions = _design_rules.generate_suggestions(row, self._db)
                except Exception as exc:  # NOQA
                    _logger.error(f"circuit editor: design rules failed for circuit {row.circuit_db_id!r}: {exc!r}")
                    row.issues = [_design_rules.DRTIssue(
                        _design_rules.Severity.WARNING, "RULES_FAILED",
                        f"The design rules could not be checked: {type(exc).__name__}: {exc}")]

                row.worst_severity = _design_rules.worst_severity(row.issues)

        except Exception as exc:  # NOQA
            _logger.error(f"circuit editor: building the table failed: {exc!r}")

        finally:
            # always tell the dock: it will not start another build while it believes this one is still running
            self.finished.emit(rows)


@_check_types.do
def _load_housing_image(housing_obj: "_pjt_housing.PJTHousing") -> QtGui.QImage | None:
    """
    Try to load a QImage from a housing database object (it runs on the worker thread, where a QPixmap is not safe).
    Looks for common attribute names used by harness tools:
      .image, .thumbnail, .photo, .picture, .icon
    Each may be a QPixmap, QImage, bytes (PNG/JPEG), or str (file path).
    """
    # PJTHousing has no image, icon or pixmap attribute, so no pixmap source
    # was ever found and this always returned None (see performance_notes).
    return None



@_check_types.do
def _unset(part: Any, id_attribute: str) -> bool:
    """Whether a catalog reference of *part* is not set: no id, or the nil id the database uses for "none"."""
    value = getattr(part, id_attribute, None)

    return value is None or value == _id_generator.NIL_UUID.bytes


def _log_once(key: tuple[str, str], message: str) -> None:
    """Write *message* to the log the first time *key* is seen, so a failure that repeats for every circuit is reported once."""
    if key not in _REPORTED:
        _REPORTED.add(key)
        _logger.error(message)


# A wire part's pictures by (primary, stripe, conductor) colour name, as (table image, panel image). The generator keeps the full-size
# image itself; this keeps the two sizes made from it. Reset by EditorCircuitPanel.refresh().
_WIRE_IMAGES: dict[Any, tuple[QtGui.QImage, QtGui.QImage]] = {}


@_check_types.do
def _qimage(image: Any, size: tuple[int, int]) -> QtGui.QImage:
    """A generated :class:`~harness_designer.image.Image` as a ``QImage`` that fits *size*, aspect kept. A ``QImage`` (not a ``QPixmap``)
    because this runs on the worker thread."""
    return QtGui.QImage.fromData(image.resize_keep_aspect(*size).png_data)


@_check_types.do
def _wire_part_images(part: Any) -> tuple[QtGui.QImage, QtGui.QImage]:
    """A wire part's picture from the image module's generator, at the table size and at the panel size.

    The generator draws only a single-conductor, unshielded wire whose insulation and conductor colours are set; the parts editor, the
    peg-board table and the BOM make the same call under the same rule. Any other part, or one the generator fails on (logged once),
    gets ``images.no_image``.

    :param part: The catalog wire, or ``None`` for a member with no part.
    :type part: Any
    :returns: ``(table image, panel image)``.
    :rtype: tuple[QtGui.QImage, QtGui.QImage]
    """
    images = _image.images
    key = None
    source = None

    try:
        if (part is not None and (part.num_conductors or 1) == 1 and not part.shielded
                and not _unset(part, "color_id") and not _unset(part, "core_material_id")):
            primary = part.color
            stripe = None if _unset(part, "stripe_color_id") else part.stripe_color
            conductor = part.core_material.color
            key = (primary.name, None if stripe is None else stripe.name, conductor.name)

            if key not in _WIRE_IMAGES:
                source = images.build_wire(primary, stripe, conductor)

    except Exception as exc:  # NOQA
        _log_once(("wire image", repr(exc)), f"circuit editor: could not build a wire image: {exc!r}")
        key = None
        source = None

    if key is None:
        key = "no image"

        if key not in _WIRE_IMAGES:
            source = images.no_image

    if key not in _WIRE_IMAGES:
        _WIRE_IMAGES[key] = (_qimage(source, WIRE_TABLE_SIZE), _qimage(source, WIRE_PANEL_SIZE))

    return _WIRE_IMAGES[key]


@_check_types.do
def _table_pixmap(info: WireInfo) -> QtGui.QPixmap | None:
    """The table picture of *info* as a ``QPixmap`` (GUI thread only), converted once and kept."""
    if isinstance(info.table_image, QtGui.QImage):
        info.table_image = QtGui.QPixmap.fromImage(info.table_image)

    return info.table_image


@_check_types.do
def _panel_pixmap(info: WireInfo) -> QtGui.QPixmap | None:
    """The panel picture of *info* as a ``QPixmap`` (GUI thread only), converted once and kept."""
    if isinstance(info.panel_image, QtGui.QImage):
        info.panel_image = QtGui.QPixmap.fromImage(info.panel_image)

    return info.panel_image


@_check_types.do
def _new_wire_info(part: Any) -> WireInfo:
    """What is specific to a wire *part*: its description and its pictures. The members using it are added by :func:`_wire_infos`."""
    info = WireInfo()
    info.table_image, info.panel_image = _wire_part_images(part)

    if part is None:
        return info

    info.part_db_id = part.db_id
    info.part_number = part.part_number or ""
    info.gauge_awg = part.size_awg
    info.gauge_mm2 = part.size_mm2
    info.od_mm = part.od_mm
    info.num_conductors = part.num_conductors or 1
    info.shielded = bool(part.shielded)

    if not _unset(part, "color_id"):
        info.color_primary = part.color.name or None

    if not _unset(part, "stripe_color_id"):
        info.color_stripe = part.stripe_color.name or None

    # The insulation is the wire's MATERIAL (a Material row); the conductor is its CORE material (a Plating).
    if not _unset(part, "material_id"):
        info.insulation = part.material.name or None

    if not _unset(part, "core_material_id"):
        core = part.core_material
        info.conductor = core.description or core.symbol or None

    return info


@_check_types.do
def _wire_infos(circuit: "_pjt_circuit.PJTCircuit", solution: Any) -> list[WireInfo]:
    """Every distinct wire part *circuit* uses, in the order it meets them, with the members that use each.

    Wire service loops count as wires. Members of one part are one entry: its count, its total length, resistance and weight, the
    most current any of them carries, and whether any is in a bundle.

    :param circuit: The circuit to read.
    :type circuit: :class:`_pjt_circuit.PJTCircuit`
    :param solution: What ``circuit.solve()`` found, or ``None`` when nothing could be solved.
    :type solution: Any
    :returns: One :class:`WireInfo` per distinct part.
    :rtype: list[WireInfo]
    """
    infos: dict[bytes | None, WireInfo] = {}

    for is_loop, members in ((False, circuit.wires or []), (True, circuit.wire_service_loops or [])):
        for member in members:
            part = member.part
            key = part.db_id if part is not None else None
            info = infos.get(key)

            if info is None:
                info = infos[key] = _new_wire_info(part)

            if is_loop:
                info.loops += 1

                # a loop knows nothing of bundles: it is taken to be in one when any wire of the circuit is (wires come first)
                if any(other.bundled for other in infos.values()):
                    info.bundled = True
            else:
                info.wires += 1

                if member.bundles:
                    info.bundled = True

            info.length_mm += float(member.length_mm or 0)
            info.resistance += float(member.resistance or 0)
            info.weight_g += float(member.weight_g or 0)

            if solution is not None:
                info.max_amps = max(info.max_amps, abs(solution.amps.get(member.db_id, 0.0)))

    for info in infos.values():
        info.length_mm = round(info.length_mm, 2)
        info.resistance = round(info.resistance, 6)
        info.weight_g = round(info.weight_g, 4)
        info.max_amps = round(info.max_amps, 3)

    return list(infos.values())


@_check_types.do
def _wire_text(info: WireInfo) -> str:
    """What is specific to one wire part of a circuit, as the text of its card in the detail panel."""
    used = []

    if info.wires:
        used.append(f"{info.wires} wire{'' if info.wires == 1 else 's'}")

    if info.loops:
        used.append(f"{info.loops} wire service loop{'' if info.loops == 1 else 's'}")

    colour = info.color_primary or "unknown"
    if info.color_stripe:
        colour += f", stripe {info.color_stripe}"

    meters = info.length_mm / 1000
    lines = [
        ("Part:", info.part_number or "unknown"),
        ("Used by:", ", ".join(used) or "nothing"),
        ("Gauge:", _gauge_text(info.gauge_awg, info.gauge_mm2) or "unknown"),
        ("Insulation:", info.insulation or "unknown"),
        ("Color:", colour),
        ("Conductor:", info.conductor or "unknown"),
        ("OD:", f"{info.od_mm:.2f} mm" if info.od_mm is not None else "unknown"),
        ("Conductors:", f"{info.num_conductors}" + (" (shielded)" if info.shielded else "")),
        ("Length:", f"{info.length_mm:.1f} mm  /  {meters:.4f} m  /  {meters * 3.28084:.4f} ft"),
        ("Resistance:", f"{info.resistance:.6f} \u03a9"),
        ("Weight:", f"{info.weight_g:.4f} g"),
        ("Max current:", f"{info.max_amps:.3f} A"),
    ]

    awg = _design_rules.resolve_awg(info.gauge_awg, info.gauge_mm2)
    amp = None if awg is None else _design_rules.AWG_AMPACITY.get(awg)

    if amp:
        limit = amp[0] if info.bundled else amp[1]
        lines.append((f"Ampacity ({'bundled' if info.bundled else 'open-air'}):",
                      f"{limit:.1f} A   margin {limit - info.max_amps:+.2f} A"))

    return "\n".join(f"{label:<21}{value}" for label, value in lines)


@_check_types.do
def _add_wire_totals(r: CircuitRow, member: Any, kind: str, solution: Any, bundled: bool) -> None:
    """Count a wire, or a wire service loop, in the row: its length, resistance and weight go into the circuit's totals, and the current it
    carries (what ``solution`` finds) into the inputs of the per-wire overcurrent rule.

    :param r: The row being built.
    :type r: CircuitRow
    :param member: The wire or wire service loop.
    :type member: Any
    :param kind: ``Wire`` or ``Wire service loop``, for the rule's message.
    :type kind: str
    :param solution: What ``circuit.solve()`` found, or ``None``.
    :type solution: Any
    :param bundled: Whether it is in a bundle, which sets the ampacity it is checked against.
    :type bundled: bool
    """
    r.total_length_mm += float(member.length_mm or 0)
    r.total_resistance += float(member.resistance or 0)
    r.total_weight_g += float(member.weight_g or 0)

    if solution is not None:
        part = member.part
        amps = abs(solution.amps.get(member.db_id, 0.0))
        r.max_wire_amps = max(r.max_wire_amps, amps)
        r.wire_loads.append(_design_rules.WireLoad(
            _member_name(member, kind),
            _design_rules.resolve_awg(part.size_awg, part.size_mm2) if part else None,
            amps, bundled))


@_check_types.do
def _member_name(member: Any, kind: str) -> str:
    """How a part of a circuit is named in a message: its name, or its kind and the start of its id."""
    try:
        name = member.name
    except Exception:  # NOQA
        name = None

    return name or f"{kind} {member.db_id.hex()[:8]}"


@_check_types.do
def _failed_row(circuit: "_pjt_circuit.PJTCircuit", error: Exception) -> CircuitRow:
    """The row for a circuit that could not be read: it says so, instead of the circuit going missing."""
    r = CircuitRow()

    try:
        r.circuit_db_id = circuit.db_id
        r.circuit_num = circuit.circuit_num
        r.net_name = circuit.name or ""
    except Exception:  # NOQA
        pass

    r.build_error = f"{type(error).__name__}: {error}"
    r.issues = [_design_rules.DRTIssue(
        _design_rules.Severity.ERROR, "ROW_FAILED", f"This circuit could not be read: {r.build_error}")]
    r.worst_severity = _design_rules.Severity.ERROR

    return r


@_check_types.do
def _build_row(circuit: "_pjt_circuit.PJTCircuit", db: "_project_db.PJTTables") -> CircuitRow:
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
    r.circuit_num = circuit.circuit_num
    r.net_name = circuit.name or ""
    r.notes = circuit.notes or ""
    r.volts = float(circuit.volts or 0)

    # What the circuit really does (the current in every wire, the voltage reaching every load, how hot every part
    # runs), worked out once for this row. None when there is no voltage terminal, so nothing can be solved.
    try:
        solution = circuit.solve()
    except Exception as exc:  # NOQA
        _logger.error(f"circuit editor: could not solve circuit {circuit.db_id!r}: {exc!r}")
        solution = None

    # Start terminal
    st = circuit.start_terminal
    r.start_terminal_db_id = st.db_id if st else None
    if st:
        cav = st.cavity
        if cav:
            r.from_pin = cav.name or ""

            h = cav.housing
            if h:
                r.from_connector = h.name or ""
                # ── housing image ──────────────────────────────────
                raw_px = _load_housing_image(h)
                if raw_px:
                    r.from_connector_image = _bitmaps.scale_housing_image(
                        raw_px, _bitmaps.ROW_H)

                else:
                    r.from_connector_image = _bitmaps.placeholder_connector_image(
                        r.from_connector, _bitmaps.ROW_H)

    # End terminals
    to_conns, to_pins = [], []
    seen_housing_names: set[str] = set()

    for et in circuit.load_terminals or []:
        r.end_terminal_db_ids.append(et.db_id)

        # a terminal's voltage_drop is the drop the user ALLOWS at that load; what it really drops comes from the solver
        allowed = float(et.voltage_drop or 0)

        if solution is not None:
            drop = max(0.0, r.volts - solution.volts.get(et.db_id, r.volts))
            r.voltage_drop_v = max(r.voltage_drop_v, drop)
            r.drop_checks.append(_design_rules.DropCheck(_member_name(et, "Terminal"), drop, allowed))
        else:
            # nothing is solved, so all there is to show is what the loads are rated for
            r.total_load_a += float(et.load or 0)

        cav = et.cavity
        if cav:
            to_pins.append(cav.name or "")

            h = cav.housing
            if h:
                hname = h.name or ""
                to_conns.append(hname)

                # ── housing image (deduplicate same housing) ───────
                if hname not in seen_housing_names:
                    seen_housing_names.add(hname)

                    raw_px = _load_housing_image(h)
                    if raw_px:
                        r.to_connector_images.append(
                            _bitmaps.scale_housing_image(
                                raw_px, _bitmaps.ROW_H))
                    else:
                        r.to_connector_images.append(
                            _bitmaps.placeholder_connector_image(
                                hname, _bitmaps.ROW_H))

    r.to_connectors = ", ".join(dict.fromkeys(to_conns))
    r.to_pins = ", ".join(to_pins)

    if solution is not None:
        r.total_load_a = round(solution.total_amps, 3)

    if r.volts > 0 and r.voltage_drop_v > 0:
        r.voltage_drop_pct = round((r.voltage_drop_v / r.volts) * 100, 2)

    # Wires and wire service loops. A loop is wire too (user, 2026-10-25): its length, resistance and weight count towards the
    # totals, and the current it carries is checked like any wire's. A loop knows nothing of bundles, so it is taken to be in one
    # when any of the circuit's wires is (the stricter bundled ampacity then applies).
    wires_bundled = False

    for member in circuit.wires or []:
        r.wire_db_ids.append(member.db_id)
        bundled = bool(member.bundles)
        wires_bundled = wires_bundled or bundled
        _add_wire_totals(r, member, "Wire", solution, bundled)

    for member in circuit.wire_service_loops or []:
        _add_wire_totals(r, member, "Wire service loop", solution, wires_bundled)

    r.total_length_mm = round(r.total_length_mm,  2)
    r.total_resistance = round(r.total_resistance, 6)
    r.total_weight_g = round(r.total_weight_g,   4)

    # Every distinct wire the circuit uses, wires and wire service loops together. The wire changes where the circuit branches
    # off a splice or another terminal, so one wire's description is not the circuit's.
    r.wires = _wire_infos(circuit, solution)

    # The first one's description, which the design rules fall back on.
    if r.wires:
        first = r.wires[0]
        r.wire_color_primary = first.color_primary
        r.wire_color_stripe = first.color_stripe
        r.wire_conductor_material = first.conductor
        r.wire_gauge_awg = first.gauge_awg
        r.wire_gauge_mm2 = first.gauge_mm2
        r.od_mm = first.od_mm
        r.num_conductors = first.num_conductors

    # Bundle routing
    bundles = _bundles_for_circuit(circuit)
    r.bundle_db_ids = [bundle_id for bundle_id, _ in bundles]
    r.bundle_names = [name for _, name in bundles]

    # the parts the solver finds hotter than they are rated for, hottest first
    if solution is not None and solution.over_temp:
        members = {member.db_id: (kind, member)
                   for kind, group in (("Wire", circuit.wires), ("Wire service loop", circuit.wire_service_loops),
                                       ("Splice", circuit.splices), ("Terminal", circuit.terminals))
                   for member in group}

        for member_id in solution.over_temp:
            kind, member = members.get(member_id, (None, None))

            if member is not None and member.max_temp_c is not None:
                r.hot_parts.append(_design_rules.HotPart(
                    _member_name(member, kind), solution.temperature[member_id], member.max_temp_c))

        r.hot_parts.sort(key=lambda part: part.temperature_c, reverse=True)

    return r



@_check_types.do
def _bundles_for_circuit(circuit: "_pjt_circuit.PJTCircuit") -> list[tuple[bytes, str]]:
    """Return every bundle one of the circuit's wires runs through, as ``(id, name)``.

    A wire is in a bundle as ``PJTWire.bundles`` judges it: by the ``bundle_id`` tag on its route rows, or, for a
    bundle none of whose wires carry the tag, by its concentric layers.

    :param circuit: The circuit to look at.
    :type circuit: :class:`_pjt_circuit.PJTCircuit`
    :returns: Each bundle once, in the order the circuit's wires meet them. A bundle with no name is called
        ``Unnamed bundle``.
    :rtype: list[tuple[bytes, str]]
    """
    found = {}

    for wire in circuit.wires:
        for bundle in wire.bundles:
            if bundle.db_id not in found:
                found[bundle.db_id] = bundle.name or "Unnamed bundle"

    return list(found.items())


# ---------------------------------------------------------------------------
# Qt Model
# ---------------------------------------------------------------------------
class CircuitTableModel(QtCore.QAbstractTableModel):
    """Represent a circuit table model in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    # (circuit id, column, new value). The id is bytes, so the first argument is `object`: declared as `int` the
    # emit could not convert it, and the edit never reached _on_cell_edited.
    cell_edited: QtCore.SignalInstance = QtCore.Signal(object, int, object)

    @_check_types.do
    def __init__(self, parent: QtCore.QObject | None = None):
        """Initialise the :class:`CircuitTableModel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self._rows: list[CircuitRow] = []

    @_check_types.do
    def load(self, rows: list[CircuitRow]) -> None:
        """Execute the load operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param rows: Value for ``rows``.
        :type rows: list[CircuitRow]
        """
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    @_check_types.do
    def clear(self) -> None:
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    @_check_types.do
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

    @_check_types.do
    def rowCount(self, p: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Execute the row count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param p: Value for ``p``.
        :type p: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return len(self._rows)

    @_check_types.do
    def columnCount(self, p: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Execute the column count operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param p: Value for ``p``.
        :type p: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return len(COLUMNS)

    @_check_types.do
    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: int = QtCore.Qt.ItemDataRole.DisplayRole
                   ) -> str | QtGui.QFont | None:
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

    @_check_types.do
    @_guarded(None)
    def data(self, index: QtCore.QModelIndex,
             role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole
             ) -> str | bytes | CircuitRow | QtGui.QBrush | QtCore.Qt.AlignmentFlag | None:
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

    @_check_types.do
    @_guarded(False)
    def setData(self, index: QtCore.QModelIndex, value: Any,
                role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.EditRole) -> bool:
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

    @_check_types.do
    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
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

    @_check_types.do
    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        """Execute the supported drop actions operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return QtCore.Qt.DropAction.MoveAction

    @_check_types.do
    def mimeTypes(self) -> list[str]:
        """Execute the mime types operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return [self.MIME]

    @_check_types.do
    @_guarded(QtCore.QMimeData)
    def mimeData(self, indexes: list[QtCore.QModelIndex]) -> QtCore.QMimeData:
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
                payload.append(f"{(self._rows[r].circuit_db_id or b'').hex()},{r}")

        m = QtCore.QMimeData()
        m.setData(self.MIME, QtCore.QByteArray(",".join(payload).encode()))

        return m

    @_check_types.do
    @_guarded(False)
    def dropMimeData(self, data: QtCore.QMimeData, action: QtCore.Qt.DropAction,
                     row: int, col: int, parent: QtCore.QModelIndex) -> bool:
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

        # "id,row,id,row,...": the ids are hex, so the rows are the odd tokens
        toks = bytes(data.data(self.MIME)).decode().split(",")
        indexes = sorted({int(token) for token in toks[1::2] if token.isdigit()})
        indexes = [i for i in indexes if 0 <= i < len(self._rows)]

        if not indexes:
            return False

        target = row if row >= 0 else len(self._rows)

        # the rows leaving from above the drop point move it up by that many places
        target -= sum(1 for i in indexes if i < target)

        self.beginResetModel()
        moved = [self._rows[i] for i in indexes]

        for i in reversed(indexes):
            del self._rows[i]

        self._rows[target:target] = moved
        self.endResetModel()

        return True


# ---------------------------------------------------------------------------
# Filter proxy
# ---------------------------------------------------------------------------
class CircuitFilterProxy(QtCore.QSortFilterProxyModel):
    """Represent a circuit filter proxy in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    @_check_types.do
    def __init__(self, parent: QtCore.QObject | None = None):
        """Initialise the :class:`CircuitFilterProxy` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)
        self._text = ""
        self._sev = None
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    @_check_types.do
    def set_filter(self, text: str) -> None:
        """Set the filter.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self._text = text.lower()
        self.invalidateFilter()

    @_check_types.do
    def set_severity(self, sev: _design_rules.Severity | None) -> None:
        """Set the severity.

        UNKNOWN details are inferred from the callable name and signature.

        :param sev: Value for ``sev``.
        :type sev: UNKNOWN
        """
        self._sev = sev
        self.invalidateFilter()

    @_check_types.do
    @_guarded(False)
    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        """Order the numeric columns by their numbers (as text, 10 would come before 9) and the status column
        by how bad it is.

        :param left: One cell.
        :type left: :class:`QtCore.QModelIndex`
        :param right: The cell to compare it with.
        :type right: :class:`QtCore.QModelIndex`
        :rtype: bool
        """
        key = _SORT_KEYS.get(left.column())

        if key is not None:
            model = self.sourceModel()
            first = model.data(left, QtCore.Qt.ItemDataRole.UserRole + 1)
            second = model.data(right, QtCore.Qt.ItemDataRole.UserRole + 1)

            if first is not None and second is not None:
                return key(first) < key(second)

        return super().lessThan(left, right)

    @_check_types.do
    @_guarded(True)
    def filterAcceptsRow(self, src_row: int, src_parent: QtCore.QModelIndex) -> bool:
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
    """Draws the Wire column: one picture for each distinct wire of the circuit (wires and wire service loops), stacked.

    The pictures are the image module's generated wire (``images.build_wire``) at ``WIRE_TABLE_SIZE``. A circuit whose wires are all
    the same part shows one; where it uses several (the wire changes when it branches off a splice or another terminal) the cell is
    made taller and they are stacked in it: the table sizes the row to what :meth:`sizeHint` asks for.
    """
    _MARGIN = 4   # px above, below and beside the pictures
    _GAP = 4      # px between two stacked pictures

    @staticmethod
    @_check_types.do
    def _pixmaps(row: CircuitRow) -> list[QtGui.QPixmap]:
        """The row's wire pictures that can be drawn."""
        pixmaps = [_table_pixmap(info) for info in row.wires]

        return [px for px in pixmaps if px is not None and not px.isNull()]

    @_check_types.do
    @_guarded(None)
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem,
              index: QtCore.QModelIndex) -> None:
        """Draw the wire pictures, centred in the cell, or a dash when the circuit has no wires.

        :param painter: The painter.
        :type painter: :class:`QtGui.QPainter`
        :param option: The item's style options.
        :type option: QtWidgets.QStyleOptionViewItem
        :param index: The item.
        :type index: :class:`QtCore.QModelIndex`
        """
        self.initStyleOption(option, index)
        row: CircuitRow = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)

        if row is None:
            super().paint(painter, option, index)
            return

        painter.save()

        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            bg = option.palette.highlight()
        else:
            bg = QtGui.QBrush(QtGui.QColor("#1e1e1e"))

        painter.fillRect(option.rect, bg)

        pixmaps = self._pixmaps(row)

        if pixmaps:
            total = sum(px.height() for px in pixmaps) + self._GAP * (len(pixmaps) - 1)
            y = option.rect.top() + max(self._MARGIN, (option.rect.height() - total) // 2)

            for px in pixmaps:
                x = option.rect.left() + max(0, (option.rect.width() - px.width()) // 2)
                painter.drawPixmap(x, y, px)
                y += px.height() + self._GAP
        else:
            painter.setPen(QtGui.QColor("#888"))
            painter.drawText(option.rect, QtCore.Qt.AlignmentFlag.AlignCenter, "\u2014")

        painter.restore()

    @_check_types.do
    @_guarded(lambda: QtCore.QSize(WIRE_TABLE_SIZE[0] + 12, _bitmaps.ROW_H))
    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        """The cell is as tall as its stacked pictures, and never shorter than a normal row.

        :param option: The item's style options.
        :type option: QtWidgets.QStyleOptionViewItem
        :param index: The item.
        :type index: :class:`QtCore.QModelIndex`
        :returns: The size the cell wants.
        :rtype: QtCore.QSize
        """
        row: CircuitRow = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)
        pixmaps = [] if row is None else self._pixmaps(row)
        width = max([px.width() for px in pixmaps] + [WIRE_TABLE_SIZE[0]]) + self._MARGIN * 2
        height = sum(px.height() for px in pixmaps) + self._GAP * max(0, len(pixmaps) - 1) + self._MARGIN * 2

        return QtCore.QSize(width, max(_bitmaps.ROW_H, height))


class ConnectorImageDelegate(QtWidgets.QStyledItemDelegate):
    """
    Shows a housing thumbnail (photo or schematic placeholder) plus the
    connector name as a small text label below the image.
    Works for both COL_FROM_CONN and COL_TO_CONNS.
    """
    _PADDING = 3

    @staticmethod
    @_check_types.do
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

    @_check_types.do
    @_guarded(None)
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem,
              index: QtCore.QModelIndex) -> None:
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

    @_check_types.do
    @_guarded(lambda: QtCore.QSize(80, _bitmaps.ROW_H))
    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
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
    """Represent a numeric delegate in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    @_check_types.do
    @_guarded("")
    def displayText(self, value: str, locale: QtCore.QLocale) -> str:
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

        except (TypeError, ValueError, OverflowError):
            if value is not None:
                return str(value)

            return "—"


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------
class CircuitDetailPanel(QtWidgets.QWidget):
    """Represent a circuit detail panel in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
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

        tabs = self._tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #3a3a3a; background:#1e1e1e; }
            QTabBar::tab { background:#2d2d2d; color:#aaa; padding:4px 12px; }
            QTabBar::tab:selected { background:#1e1e1e; color:#fff;
                                    border-bottom:2px solid #4a8fff; }
        """)

        layout.addWidget(tabs)

        @_check_types.do
        def _te() -> QtWidgets.QTextEdit:
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

        # one card per distinct wire of the circuit: its picture centred above what is specific to it
        self._wires_scroll = QtWidgets.QScrollArea()
        self._wires_scroll.setWidgetResizable(True)
        self._wires_scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e1e; }")
        body = QtWidgets.QWidget()
        body.setStyleSheet("background:#1e1e1e;")
        self._wires_layout = QtWidgets.QVBoxLayout(body)
        self._wires_layout.setContentsMargins(6, 6, 6, 6)
        self._wires_layout.setSpacing(10)
        self._wires_scroll.setWidget(body)
        tabs.addTab(self._wires_scroll, "Wires")
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
    @_check_types.do
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
        x = 0
        with _bitmaps.painting(comp) as ptr:
            for p in all_px:
                ptr.drawPixmap(x, (total_h - p.height()) // 2, p)
                x += p.width() + gap

        return comp

    @_check_types.do
    def _show_wires(self, row: CircuitRow | None) -> None:
        """Fill the Wires tab: one card for each distinct wire of the circuit, its picture centred above its data.

        :param row: The circuit's row, or ``None`` to empty the tab.
        :type row: CircuitRow | None
        """
        layout = self._wires_layout

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                # out of the panel now: deleteLater alone leaves it a child, and drawn, until the event loop gets to it
                widget.setParent(None)
                widget.deleteLater()

        wires = [] if row is None else row.wires
        self._tabs.setTabText(1, f"Wires ({len(wires)})" if len(wires) > 1 else "Wires")

        if not wires:
            note = QtWidgets.QLabel("No circuit selected" if row is None else "This circuit has no wires.")
            note.setStyleSheet("color:#888; padding:8px;")
            layout.addWidget(note)
            layout.addStretch(1)
            return

        for info in wires:
            card = QtWidgets.QFrame()
            card.setObjectName("wireCard")
            card.setStyleSheet("#wireCard { border:1px solid #3a3a3a; border-radius:4px; background:#222; }")

            box = QtWidgets.QVBoxLayout(card)
            box.setContentsMargins(8, 8, 8, 8)
            box.setSpacing(6)

            picture = QtWidgets.QLabel()
            pixmap = _panel_pixmap(info)

            if pixmap is not None:
                picture.setPixmap(pixmap)

            box.addWidget(picture, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)

            text = QtWidgets.QLabel(_wire_text(info))
            text.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            text.setStyleSheet("font-family:monospace; font-size:11px; color:#e0e0e0;")
            box.addWidget(text)

            layout.addWidget(card)

        layout.addStretch(1)

    @_check_types.do
    def show_row(self, row: CircuitRow | None) -> None:
        """Show the row.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: CircuitRow | None
        """
        if row is None:
            self._title.setText("No circuit selected")
            self._show_wires(None)
            self._totals.clear()
            self._drt.clear()
            self._sugg.clear()

            return

        name = row.net_name or f"Circuit {row.circuit_num}"
        self._title.setText(f"  {name}")

        # ── Wire preview ──────────────────────────────────────────────
        self._show_wires(row)

        # ── Totals ────────────────────────────────────────────────────
        lm = row.total_length_mm / 1000
        txt = (
            f"  {'Wire parts:':<28} {len(row.wires)}  (see the Wires tab)\n\n"
            f"  {'Total length:':<28} {row.total_length_mm:.1f} mm\n"
            f"  {'':28} {lm:.4f} m   /   {lm*3.28084:.4f} ft\n\n"
            f"  {'Total resistance:':<28} {row.total_resistance:.6f} Ω\n"
            f"  {'Total weight:':<28} {row.total_weight_g:.4f} g\n\n"
            f"  {'System voltage:':<28} {row.volts:.1f} V\n"
            f"  {'Total load:':<28} {row.total_load_a:.3f} A\n"
            f"  {'Voltage drop:':<28} {row.voltage_drop_v:.4f} V  "
            f"({row.voltage_drop_pct:.2f} %)\n\n"
            f"  {'From:':<28} {row.from_connector}  pin {row.from_pin}\n"
            f"  {'To:':<28} {row.to_connectors}  pin {row.to_pins}\n\n"
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
            self._tabs.setTabText(2, "DRT Issues")
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
                2, f"DRT Issues  ({ec}✕  {wc}⚠)" if (ec or wc) else "DRT Issues")

        # ── Suggestions ───────────────────────────────────────────────
        if not row.suggestions:
            self._sugg.setPlainText("No concentric-twist split suggestions.")
            self._tabs.setTabText(3, "Suggestions")
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
            self._tabs.setTabText(3, f"Suggestions ({len(row.suggestions)})")


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
    """Represent a circuit table view in :mod:`harness_designer.ui.editor_circuit.editor_widget`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    row_selected: QtCore.SignalInstance = QtCore.Signal(object)
    # the circuit id of the row whose Delete Circuit was chosen
    delete_requested: QtCore.SignalInstance = QtCore.Signal(object)

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame",
                 parent: QtWidgets.QWidget | None = None):
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
        # a row is as tall as its tallest cell: the Wire column stacks a picture per distinct wire
        vh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        vh.setVisible(False)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(
            COL_STATUS, QtWidgets.QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(COL_STATUS, 28)

        for col in (COL_NET_NAME, COL_BUNDLES, COL_NOTES):
            hh.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.Stretch)

        for col in (COL_CIRCUIT_NUM, COL_FROM_PIN, COL_TO_PIN,
                    COL_GAUGE, COL_LOAD_A, COL_V_DROP_PCT):

            hh.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        # Give connector and wire columns a reasonable fixed width
        self.setColumnWidth(COL_FROM_CONN, 120)
        self.setColumnWidth(COL_TO_CONNS, 160)
        self.setColumnWidth(COL_WIRE_COLOR, WIRE_TABLE_SIZE[0] + 12)

    @_check_types.do
    @_guarded(None)
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """Right-click a circuit for its menu: Delete Circuit.

        :param event: The context menu event.
        :type event: :class:`QtGui.QContextMenuEvent`
        """
        index = self.indexAt(event.pos())

        if not index.isValid():
            return

        row: CircuitRow | None = index.data(QtCore.Qt.ItemDataRole.UserRole + 1)

        if row is None or row.circuit_db_id is None:
            return

        self.selectRow(index.row())

        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Delete Circuit\u2026")

        if self._choose_action(menu, event.globalPos()) is delete_action:
            self.delete_requested.emit(row.circuit_db_id)

    @_check_types.do
    def _choose_action(self, menu: QtWidgets.QMenu, global_pos: QtCore.QPoint) -> QtGui.QAction | None:
        """Show *menu* at *global_pos* and return the action the user chose, or ``None``."""
        return menu.exec(global_pos)

    @_check_types.do
    @_guarded(None)
    def selectionChanged(self, selected: QtCore.QItemSelection,
                         deselected: QtCore.QItemSelection) -> None:
        """Execute the selection changed operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        :param deselected: Value for ``deselected``.
        :type deselected: UNKNOWN
        """
        super().selectionChanged(selected, deselected)
        self.row_selected.emit(self.selected_row())

    @_check_types.do
    def selected_row(self) -> CircuitRow | None:
        """Return the row that is selected in the table, or ``None`` when no row is.

        :returns: The selected row.
        :rtype: CircuitRow | None
        """
        idxs = self.selectionModel().selectedRows()
        if not idxs:
            return None

        proxy = self.model()

        if isinstance(proxy, QtCore.QSortFilterProxyModel):
            si = proxy.mapToSource(idxs[0])
            sm = proxy.sourceModel()
        else:
            si = idxs[0]
            sm = proxy

        return sm.data(si, QtCore.Qt.ItemDataRole.UserRole + 1)


# ---------------------------------------------------------------------------
# Dock
# ---------------------------------------------------------------------------
class EditorCircuitPanel(QtWidgets.QWidget):
    """
    The circuit table and its detail panel. :class:`EditorCircuit` (``editor_circuit.py``) puts it in the
    dock; ``MainFrame`` builds that, and ``load_project(project_db)`` points the panel at a project (or
    at none, when it closes).
    """

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorCircuitPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        super().__init__(mainframe)
        self._mainframe = mainframe
        self._project_db = None
        self._thread = None
        self._worker = None
        self._refresh_pending = False
        # the circuit that selecting a row selected (see _on_row_selected), so unselecting the row can deselect it
        self._selected_circuit_db_id: bytes | None = None

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
        self._view.delete_requested.connect(self._on_delete_requested)
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
        # A plain panel, like every other editor's: the dock around it is the one DockBase makes. This used to be a
        # QDockWidget itself, which put a dock (its own title bar, float and close buttons) inside the dock.
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        self._model.modelReset.connect(self._update_count)
        self._proxy.rowsInserted.connect(self._update_count)
        self._proxy.rowsRemoved.connect(self._update_count)

    # ── Public ────────────────────────────────────────────────────────
    @_check_types.do
    @_guarded(None)
    def load_project(self, project_db: _Union["_project_db.PJTTables", None]) -> None:
        """Point the dock at a project (or at none, when it closes).

        Rows are built when the dock is on screen: right away if it already
        is, otherwise in :meth:`showEvent`. A dock nobody opens costs nothing.

        :param project_db: The project's tables, or ``None`` to clear the dock.
        :type project_db: :class:`_project_db.PJTTables` | None
        """
        self._project_db = project_db

        if project_db is None or self.isVisible():
            self.refresh()

    @_check_types.do
    @_guarded(None)
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Rebuild the rows whenever the dock is shown, so what it lists is
        current with the circuits made, merged or deleted since.

        :param event: The show event.
        :type event: :class:`QtGui.QShowEvent`
        """
        super().showEvent(event)

        if self._project_db is not None:
            self.refresh()

    @_check_types.do
    @_guarded(None)
    def refresh(self) -> None:
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._project_db is None:
            self._model.clear()
            return

        if self._thread is not None and self._thread.isRunning():
            # a build is under way, perhaps for a project that has since closed: run again when it ends
            self._refresh_pending = True
            return

        # flush stale pixmaps on reload
        _WIRE_IMAGES.clear()

        self._progress.setValue(0)
        self._progress.show()
        self._thread = QtCore.QThread(self)
        self._worker = _BuildWorker(self._project_db)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)  # NOQA
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    @_check_types.do
    @_guarded(None)
    def deselect_circuit(self, circuit_db_id: bytes) -> None:
        """Clear the table's selection when the selected row is this circuit's, and do nothing otherwise.

        A circuit's views call this when the circuit is deselected (``Circuit.set_selected(False)``: the user clicked another object, or empty
        space, in an editor), so the table stops showing the circuit's row as selected. When it is the table that changed the selection, the
        row is no longer the selected one by the time the circuit asks, so this exits without doing anything and the two cannot loop.

        :param circuit_db_id: The circuit's row id.
        :type circuit_db_id: bytes
        """
        row = self._view.selected_row()

        if row is None or row.circuit_db_id != circuit_db_id:
            return

        self._view.clearSelection()

    @_check_types.do
    @_guarded(None)
    def highlight_circuit(self, circuit_db_id: bytes) -> None:
        """Execute the highlight circuit operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param circuit_db_id: Identifier for the circuit database.
        :type circuit_db_id: bytes
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
    @_check_types.do
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

    @_check_types.do
    @_guarded(None)
    def _on_sev_changed(self, idx: int) -> None:
        """Handle the sev changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param idx: Value for ``idx``.
        :type idx: int
        """
        self._proxy.set_severity(
            {0: None, 1: _design_rules.Severity.ERROR,
             2: _design_rules.Severity.WARNING,
             3: _design_rules.Severity.INFO}.get(idx))

    @_check_types.do
    @_guarded(None)
    def _on_thread_finished(self) -> None:
        """Let go of the finished build, and start another if one was asked for while it ran."""
        thread, worker = self._thread, self._worker
        self._thread = self._worker = None

        if worker is not None:
            worker.deleteLater()

        if thread is not None:
            thread.deleteLater()

        if self._refresh_pending:
            self._refresh_pending = False
            self.refresh()

    @_check_types.do
    @_guarded(None)
    def _on_loaded(self, rows: list[CircuitRow]) -> None:
        """Handle the loaded event.

        UNKNOWN details are inferred from the callable name and signature.

        :param rows: Value for ``rows``.
        :type rows: list[CircuitRow]
        """
        # A build that was still running when the project closed or changed: its rows are for the wrong project.
        if self._project_db is None or self._worker is None or self._worker._db is not self._project_db:
            self._progress.hide()
            return

        # the connector pictures were drawn as QImage on the worker thread; a QPixmap may only be made on this one
        for row in rows:
            if isinstance(row.from_connector_image, QtGui.QImage):
                row.from_connector_image = QtGui.QPixmap.fromImage(row.from_connector_image)

            row.to_connector_images = [
                QtGui.QPixmap.fromImage(image) if isinstance(image, QtGui.QImage) else image
                for image in row.to_connector_images]

            for info in row.wires:
                _table_pixmap(info)

        self._model.load(rows)
        self._view.resizeColumnsToContents()
        # Re-enforce minimum widths for visual columns after resize
        self._view.setColumnWidth(
            COL_WIRE_COLOR, max(self._view.columnWidth(COL_WIRE_COLOR), WIRE_TABLE_SIZE[0] + 12))

        self._view.setColumnWidth(
            COL_FROM_CONN, max(self._view.columnWidth(COL_FROM_CONN), 100))

        self._view.setColumnWidth(
            COL_TO_CONNS, max(self._view.columnWidth(COL_TO_CONNS), 130))

        self._progress.hide()
        self._update_count()

    @_check_types.do
    def _confirm_delete(self, label: str, members: int) -> bool:
        """Ask whether to delete a circuit, saying that it cannot be undone.

        :param label: What to call the circuit, e.g. ``#3 Fuel pump``.
        :type label: str
        :param members: How many wires, wire service loops, splices and terminals are in it.
        :type members: int
        :returns: ``True`` to delete it.
        :rtype: bool
        """
        if members:
            what = (f"{members} object{'' if members == 1 else 's'} in it (wires, wire service loops, splices and terminals) "
                    f"will be taken out of the circuit. The objects themselves are kept.\n\n")
        else:
            what = "It has no wires, wire service loops, splices or terminals.\n\n"

        button = QtWidgets.QMessageBox.question(
            self, "Delete Circuit",
            f"Are you sure you want to delete circuit {label}?\n\n{what}This cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No)

        return button == QtWidgets.QMessageBox.StandardButton.Yes

    @_check_types.do
    @_guarded(None)
    def _on_delete_requested(self, circuit_db_id: bytes) -> None:
        """Delete the circuit whose Delete Circuit was chosen, after asking.

        Deleting a circuit clears the circuit of every wire, wire service loop, splice and terminal in it (``PJTCircuit.detach_members``:
        the column holds NULL); it never deletes them.

        :param circuit_db_id: The circuit's row id.
        :type circuit_db_id: bytes
        """
        project = self._mainframe.project

        if project is None:
            return

        circuit = _find_obj(project.circuits, circuit_db_id)

        if circuit is None:
            _logger.error(f"circuit editor: no circuit {circuit_db_id!r} to delete")
            return

        db_obj = circuit.db_obj
        members = (len(db_obj.wires) + len(db_obj.wire_service_loops) + len(db_obj.splices) + len(db_obj.terminals))

        if not self._confirm_delete(db_obj.label, members):
            return

        circuit.delete()

        self._detail.show_row(None)
        self.refresh()

    @_check_types.do
    @_guarded(None)
    def _on_row_selected(self, row: CircuitRow | None) -> None:
        """Handle the row selected event.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: CircuitRow | None
        """
        self._detail.show_row(row)

        project = self._mainframe.project
        previous_id, self._selected_circuit_db_id = self._selected_circuit_db_id, None

        if row is None:
            # The row was unselected (empty space in the table, the row toggled off, a filter hiding it): deselect the circuit it had
            # selected, everywhere. When a click in an editor ended the selection this does nothing, because the circuit is already
            # deselected (it says so before its views call deselect_circuit, which is what cleared this row).
            if project is not None and previous_id is not None:
                previous = _find_obj(project.circuits, previous_id)

                if previous is not None and previous.is_selected:
                    previous.set_selected(False)

            return

        if project is None:
            return

        obj = _find_obj(project.circuits, row.circuit_db_id)
        if obj:
            self._selected_circuit_db_id = row.circuit_db_id
            # Selecting a circuit highlights all of its members (see
            # Circuit.set_selected); MainFrame.set_selected does not deselect
            # the previous selection, so do that first or two circuits stay lit.
            current = self._mainframe.get_selected()
            if current is not None and current is not obj:
                current.set_selected(False)

            self._mainframe.set_selected(obj)

    @_check_types.do
    @_guarded(None)
    def _on_cell_edited(self, circuit_db_id: bytes, col: int, value: Any) -> None:
        """Handle the cell edited event.

        UNKNOWN details are inferred from the callable name and signature.

        :param circuit_db_id: Identifier for the circuit database.
        :type circuit_db_id: bytes
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

    @_check_types.do
    @_guarded(None)
    def _update_count(self) -> None:
        """Update the count.

        UNKNOWN details are inferred from the callable name and signature.
        """
        n = self._proxy.rowCount()
        errs = 0
        for r in range(self._proxy.rowCount()):
            shown = self._proxy.data(self._proxy.index(r, 0), QtCore.Qt.ItemDataRole.UserRole + 1)

            if shown is not None and shown.worst_severity == _design_rules.Severity.ERROR:
                errs += 1

        label = f"  {n} circuit{'s' if n!=1 else ''}"
        if errs:
            label += f"  ·  {errs} ✕ error{'s' if errs!=1 else ''}  "

        self._count_label.setText(label)
        self._count_label.setStyleSheet(
            "color:#ff7070; padding-right:6px;" if errs else "color:#888; padding-right:6px;")


# ---------------------------------------------------------------------------
# Cell text / tooltip helpers
# ---------------------------------------------------------------------------
@_check_types.do
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
        COL_TO_PIN: row.to_pins,
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


@_check_types.do
def _gauge(row: CircuitRow) -> str:
    """The gauge of every distinct wire of the circuit, each once, in the order the circuit meets them."""
    texts = []

    for info in row.wires:
        text = _gauge_text(info.gauge_awg, info.gauge_mm2)

        if text and text not in texts:
            texts.append(text)

    return ", ".join(texts)


@_check_types.do
def _gauge_text(awg: Any, mm2: Any) -> str:
    """One gauge as text: ``18 AWG / 0.75 mm²``, whichever of the two the part has."""
    p = []
    if awg is not None:
        p.append(f"{awg} AWG")

    if mm2 is not None:
        p.append(f"{mm2} mm²")

    return " / ".join(p)


@_check_types.do
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
        lines = []

        for info in row.wires:
            awg = _design_rules.resolve_awg(info.gauge_awg, info.gauge_mm2)
            amp = None if awg is None else _design_rules.AWG_AMPACITY.get(awg)

            if amp:
                lines.append(f"{info.part_number or 'wire'}:  {_gauge_text(info.gauge_awg, info.gauge_mm2)}\n"
                             f"    Bundled ampacity:   {amp[0]:.1f} A\n"
                             f"    Open-air ampacity:  {amp[1]:.1f} A\n"
                             f"    Currently:  {'bundled' if info.bundled else 'open air'}")

        return "\n".join(lines)

    if col == COL_WIRE_COLOR:
        lines = []

        for info in row.wires:
            colour = info.color_primary or "unknown"
            if info.color_stripe:
                colour += f" / {info.color_stripe}"

            lines.append(f"{info.part_number or 'wire'}:  {colour},  conductor {info.conductor or 'unknown'}")

        return "\n".join(lines)

    if col == COL_FROM_CONN:
        return row.from_connector or ""

    if col == COL_TO_CONNS:
        return row.to_connectors or ""

    return ""


@_check_types.do
def _find_obj(objs: _Union[list["_circuit.Circuit"], list["_wire.Wire"]], db_id: bytes) -> _Union["_circuit.Circuit", "_wire.Wire", None]:
    """Return the first object in ``objs`` whose DB id is ``db_id``, else None.

    :param objs: Project circuits or wires, as ObjectBase facades.
    :type objs: list
    :param db_id: Identifier for the database.
    :type db_id: bytes
    :returns: The matching object, or None.
    """
    try:
        for obj in objs:
            if obj.db_obj.db_id == db_id:
                return obj

    except Exception:  # NOQA
        pass


