# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from enum import Enum, auto
from dataclasses import dataclass
import math
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from . import editor_circuit as _editor_circuit


MAX_VDROP_PCT = 5.0   # design-rule voltage-drop limit


# ---------------------------------------------------------------------------
# DRT severity
# ---------------------------------------------------------------------------
class Severity(Enum):
    """Represent a severity in :mod:`harness_designer.ui.editor_circuit.design_rules`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    OK = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


SEV_BG = {Severity.OK: "#2d5a2d", Severity.INFO: "#1a3a5c",
          Severity.WARNING: "#5a4a00", Severity.ERROR: "#5a1a1a"}

SEV_FG = {Severity.OK: "#7dcc7d", Severity.INFO: "#7ab8f5",
          Severity.WARNING: "#ffd060", Severity.ERROR: "#ff7070"}

SEV_ICO = {Severity.OK: "✓", Severity.INFO: "ℹ",
           Severity.WARNING: "⚠", Severity.ERROR: "✕"}


@dataclass
class DRTIssue:
    """Represent a drt issue in :mod:`harness_designer.ui.editor_circuit.design_rules`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    severity: Severity
    code: str
    message: str


@dataclass
class SplitSuggestion:
    """Represent a split suggestion in :mod:`harness_designer.ui.editor_circuit.design_rules`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    original_awg: int
    original_mm2: float
    suggested_awg: int
    suggested_mm2:  float
    num_parallel: int
    combined_mm2: float
    reason:  str


@dataclass
class WireLoad:
    """One wire of a circuit and the current the solver finds in it."""
    name: str
    awg: int | None
    amps: float
    bundled: bool


@dataclass
class HotPart:
    """A part of a circuit that the solver finds hotter than it is rated for."""
    name: str
    temperature_c: float
    rated_c: float


@dataclass
class DropCheck:
    """The voltage drop the solver finds to a load terminal, and the drop the user allows there (0 = none set)."""
    name: str
    drop_v: float
    allowed_v: float


# ---------------------------------------------------------------------------
# Ampacity tables  (NEC + ISO 6722 chassis-wiring bundled-derating)
# {awg: (bundled_A, open_air_A)}
# ---------------------------------------------------------------------------
AWG_AMPACITY: dict[int, tuple[float, float]] = {
    30: (0.5,  0.86),
    28: (0.8,  1.0),
    26: (1.0,  1.3),
    24: (2.0,  2.1),
    22: (3.0,  3.5),
    20: (5.0,  6.0),
    18: (7.5,  10.0),
    16: (13.0, 17.0),
    14: (20.0, 24.0),
    12: (26.0, 32.0),
    10: (35.0, 45.0),
    8:  (46.0, 60.0),
    6:  (62.0, 80.0),
    4:  (84.0, 105.0),
    2:  (113.0, 140.0),
    1:  (130.0, 165.0),
    0:  (150.0, 195.0)
}

# ISO 6722 nominal mm² → nearest AWG
MM2_TO_AWG: dict[float, int] = {
    0.13: 26,
    0.20: 24,
    0.35: 22,
    0.50: 20,
    0.75: 18,
    1.0: 17,
    1.5: 15,
    2.0: 14,
    2.5: 13,
    3.0: 12,
    4.0: 11,
    6.0: 10,
    10.0: 8,
    16.0: 6,
    25.0: 4,
    35.0: 2,
    50.0: 1,
    70.0: 0
}


# ---------------------------------------------------------------------------
# Geometry / wire-size helpers
# ---------------------------------------------------------------------------
@_check_types.do
def awg_to_mm2(awg: int) -> float:
    """Execute the awg to mm 2 operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param awg: Value for ``awg``.
    :type awg: int
    :returns: Return value. UNKNOWN details.
    :rtype: float
    """
    d_in = 0.005 * (92 ** ((36 - awg) / 39))
    d_mm = d_in * 25.4
    return (math.pi / 4) * (d_mm ** 2)


@_check_types.do
def awg_to_od_mm(awg: int) -> float:
    """Execute the awg to od mm operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param awg: Value for ``awg``.
    :type awg: int
    :returns: Return value. UNKNOWN details.
    :rtype: float
    """
    d_in = 0.005 * (92 ** ((36 - awg) / 39))
    return d_in * 25.4 + 2.0


@_check_types.do
def nearest_wire_at_least(target_mm2: float) -> tuple[int | None, float | None]:
    """Execute the nearest wire at least operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param target_mm2: Value for ``target_mm2``.
    :type target_mm2: float
    :returns: Return value. UNKNOWN details.
    :rtype: tuple[int | None, float | None]
    """
    for mm2 in sorted(MM2_TO_AWG):
        if mm2 >= target_mm2 * 0.90:
            return MM2_TO_AWG[mm2], mm2

    return None, None


@_check_types.do
def resolve_awg(awg: float | int | str | None, mm2: float | int | str | None) -> int | None:
    """Execute the resolve awg operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param awg: Value for ``awg``.
    :type awg: UNKNOWN
    :param mm2: Value for ``mm2``.
    :type mm2: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: int | None
    """
    if awg is not None:
        try:
            return int(awg)

        except (TypeError, ValueError):
            pass

    if mm2 is not None:
        try:
            f = float(mm2)
            best = min(MM2_TO_AWG, key=lambda k: abs(k - f))
            return MM2_TO_AWG[best]

        except (TypeError, ValueError):
            pass


@_check_types.do
def worst_severity(issues: list[DRTIssue]) -> Severity:
    """Execute the worst severity operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param issues: Value for ``issues``.
    :type issues: list[DRTIssue]
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`Severity`
    """
    order = [Severity.OK, Severity.INFO, Severity.WARNING, Severity.ERROR]
    sev = Severity.OK
    for i in issues:
        if order.index(i.severity) > order.index(sev):
            sev = i.severity

    return sev


# ---------------------------------------------------------------------------
# DRT engine
# ---------------------------------------------------------------------------
@_check_types.do
def _check_current(issues: list[DRTIssue], awg: int | None, amps: float, bundled: bool, label: str = "") -> None:
    """Add an issue when *amps* is over what the ampacity table allows for *awg*, or close to it.

    :param issues: The list to add to.
    :type issues: list[DRTIssue]
    :param awg: The wire's gauge; nothing is checked when it is unknown or not in the table.
    :type awg: int | None
    :param amps: The current in the wire.
    :type amps: float
    :param bundled: Whether the wire is in a bundle, which has the lower limit.
    :type bundled: bool
    :param label: The wire, named in the message; empty for the circuit as a whole.
    :type label: str
    """
    amp = AWG_AMPACITY.get(awg) if awg is not None else None

    if not amp or amps <= 0:
        return

    limit = amp[0] if bundled else amp[1]
    kind = "bundled" if bundled else "open-air"
    where = f" in {label}" if label else ""

    if amps > limit:
        pct = (amps - limit) / limit * 100
        issues.append(DRTIssue(
            Severity.ERROR, "OVERCURRENT",
            f"Load {amps:.2f} A{where} exceeds {kind} ampacity {limit:.1f} A for {awg} AWG ({pct:.0f} % over)."))

    elif amps > limit * 0.85:
        issues.append(DRTIssue(
            Severity.WARNING, "NEAR_LIMIT",
            f"Load {amps:.2f} A{where} is {amps / limit * 100:.0f} % of {limit:.1f} A {kind} limit "
            f"for {awg} AWG — consider upsizing."))


@_check_types.do
def run_drt(row: "_editor_circuit.CircuitRow") -> list[DRTIssue]:
    """Execute the run drt operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param row: Value for ``row``.
    :type row: :class:`_editor_circuit.CircuitRow`
    :returns: Return value. UNKNOWN details.
    :rtype: list[DRTIssue]
    """
    issues: list[DRTIssue] = []
    awg = resolve_awg(row.wire_gauge_awg, row.wire_gauge_mm2)
    load = row.total_load_a
    in_bun = bool(row.bundle_names)

    if awg is None and row.wire_gauge_mm2 is None:
        issues.append(DRTIssue(
            Severity.WARNING, "NO_WIRE",
            "No wire part assigned to this circuit."))

        return issues

    if load == 0:
        issues.append(DRTIssue(
            Severity.INFO, "NO_LOAD",
            "No load (A) defined — overcurrent checking disabled."))

    if row.volts == 0 and load > 0:
        issues.append(DRTIssue(
            Severity.INFO, "NO_VOLTS",
            "System voltage not set — voltage-drop checking disabled."))

    if row.wire_loads:
        # the current the solver finds in each wire, against that wire's own gauge
        for wire_load in row.wire_loads:
            _check_current(issues, wire_load.awg, wire_load.amps, wire_load.bundled, wire_load.name)

    elif awg is not None and load > 0:
        _check_current(issues, awg, load, in_bun)

    if row.volts > 0 and row.voltage_drop_pct > 0:
        if row.voltage_drop_pct > MAX_VDROP_PCT:
            issues.append(DRTIssue(
                Severity.ERROR, "V_DROP",
                f"Voltage drop {row.voltage_drop_pct:.1f} % exceeds "
                f"{MAX_VDROP_PCT:.0f} % limit "
                f"({row.voltage_drop_v:.3f} V on {row.volts:.1f} V)."))

        elif row.voltage_drop_pct > MAX_VDROP_PCT * 0.80:
            issues.append(DRTIssue(
                Severity.WARNING, "V_DROP_NEAR",
                f"Voltage drop {row.voltage_drop_pct:.1f} % approaching "
                f"{MAX_VDROP_PCT:.0f} % limit."))

    for check in row.drop_checks:
        if check.allowed_v > 0 and check.drop_v > check.allowed_v:
            issues.append(DRTIssue(
                Severity.ERROR, "V_DROP_ALLOWED",
                f"Voltage drop to {check.name} is {check.drop_v:.3f} V, more than the "
                f"{check.allowed_v:.3f} V allowed there."))

    for part in row.hot_parts:
        issues.append(DRTIssue(
            Severity.ERROR, "OVER_TEMP",
            f"{part.name} runs at {part.temperature_c:.0f} °C, above its {part.rated_c:.0f} °C rating."))

    return issues



@_check_types.do
def bundle_wire_ods(bundle: "_pjt_bundle.PJTBundle") -> list[float]:
    """The outside diameter, in millimetres, of every wire in *bundle*; a wire whose part has none is left out.

    :param bundle: The bundle.
    :type bundle: :class:`_pjt_bundle.PJTBundle`
    :returns: The diameters, one per wire.
    :rtype: list[float]
    """
    ods = []

    for wire in bundle.wires:
        od = wire.part.od_mm

        if od:
            ods.append(float(od))

    return ods



@_check_types.do
def generate_suggestions(row: "_editor_circuit.CircuitRow",
                         project_db: "_project_db.PJTTables") -> list[SplitSuggestion]:
    """Execute the generate suggestions operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param row: Value for ``row``.
    :type row: :class:`_editor_circuit.CircuitRow`
    :param project_db: Value for ``project_db``.
    :type project_db: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: list[SplitSuggestion]
    """

    suggestions: list[SplitSuggestion] = []

    awg = resolve_awg(row.wire_gauge_awg, row.wire_gauge_mm2)
    if awg is None:
        return suggestions

    mm2 = awg_to_mm2(awg)
    od = row.od_mm or awg_to_od_mm(awg)

    seen_splits: set[tuple[int, int]] = set()

    for bundle_id, bname in zip(row.bundle_db_ids, row.bundle_names):
        try:
            bundle = project_db.pjt_bundles_table[bundle_id]
        except (KeyError, IndexError):
            continue

        all_ods = bundle_wire_ods(bundle)
        if len(all_ods) < 2:
            continue

        other_ods = [o for o in all_ods if abs(o - od) > 0.1]
        if not other_ods:
            continue

        max_other = max(other_ods)

        if od >= max_other * 1.5 and od > 2.0:
            half_mm2 = mm2 / 2.0
            split_awg, split_mm2 = nearest_wire_at_least(half_mm2)

            if split_awg is None or (split_awg, 2) in seen_splits:
                continue

            seen_splits.add((split_awg, 2))
            combined = split_mm2 * 2
            suggestions.append(SplitSuggestion(
                original_awg=awg,
                original_mm2=round(mm2, 3),
                suggested_awg=split_awg,
                suggested_mm2=round(split_mm2, 3),
                num_parallel=2,
                combined_mm2=round(combined, 3),
                reason=(f"In bundle '{bname}' this {awg} AWG wire (OD {od:.2f} mm) "
                        f"is {od/max_other:.1f}× wider than the next-largest wire "
                        f"({max_other:.2f} mm), disrupting concentric-twist packing. "
                        f"Two parallel {split_awg} AWG wires ({split_mm2} mm² each) "
                        f"give {combined:.3f} mm² combined cross-section vs. the "
                        f"original {mm2:.3f} mm², maintaining current capacity "
                        f"while fitting tightly in the inner concentric layer.")))

    return suggestions
