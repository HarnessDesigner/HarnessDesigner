# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from enum import Enum, auto
from dataclasses import dataclass
import math

if TYPE_CHECKING:
    from . import editor_circuit as _editor_circuit


MAX_VDROP_PCT = 5.0   # design-rule voltage-drop limit


# ---------------------------------------------------------------------------
# DRT severity
# ---------------------------------------------------------------------------
class Severity(Enum):
    """Represent a severity in :mod:`harness_designer.ui.editor_ciruit.design_rules`.

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
    """Represent a drt issue in :mod:`harness_designer.ui.editor_ciruit.design_rules`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    severity: Severity
    code: str
    message: str


@dataclass
class SplitSuggestion:
    """Represent a split suggestion in :mod:`harness_designer.ui.editor_ciruit.design_rules`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    original_awg: int
    original_mm2: float
    suggested_awg: int
    suggested_mm2:  float
    num_parallel: int
    combined_mm2: float
    reason:  str


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


def resolve_awg(awg, mm2) -> int | None:
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

    if awg is not None and load > 0:
        amp = AWG_AMPACITY.get(awg)
        if amp:
            limit = amp[0] if in_bun else amp[1]
            if load > limit:
                pct = (load - limit) / limit * 100
                issues.append(DRTIssue(
                    Severity.ERROR, "OVERCURRENT",
                    f"Load {load:.2f} A exceeds {'bundled' if in_bun else 'open-air'} "
                    f"ampacity {limit:.1f} A for {awg} AWG ({pct:.0f} % over)."))

            elif load > limit * 0.85:
                issues.append(DRTIssue(
                    Severity.WARNING, "NEAR_LIMIT",
                    f"Load {load:.2f} A is {load/limit*100:.0f} % of "
                    f"{limit:.1f} A {'bundled' if in_bun else 'open-air'} limit "
                    f"for {awg} AWG — consider upsizing."))

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

    return issues


def safe(obj, attr: str, default=None):
    """Execute the safe operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param obj: Object instance to operate on.
    :type obj: UNKNOWN
    :param attr: Value for ``attr``.
    :type attr: str
    :param default: Value for ``default``.
    :type default: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    try:
        return getattr(obj, attr, default)
    except Exception:   # NOQA
        return default


def find_bundle_by_name(db, name: str):
    """Find the bundle by name.

    UNKNOWN details are inferred from the callable name and signature.

    :param db: Database accessor or connection.
    :type db: UNKNOWN
    :param name: Name value.
    :type name: str
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    try:
        for b in db.pjt_bundles_table:
            if (safe(b, "name", "") or "") == name:
                return b

    except Exception:  # NOQA
        pass


def bundle_wire_ods(bundle) -> list[float]:
    """Execute the bundle wire ods operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param bundle: Value for ``bundle``.
    :type bundle: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: list[float]
    """
    ods = []
    try:
        for bw in (safe(bundle, "wires", []) or []):
            pw = safe(bw, "wire")
            if pw:
                od = safe(safe(pw, "part"), "od_mm")
                if od:
                    ods.append(float(od))

    except Exception:  # NOQA
        pass
    return ods


def generate_suggestions(row: "_editor_circuit.CircuitRow",
                         project_db) -> list[SplitSuggestion]:
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

    for bname in row.bundle_names:
        bundle = find_bundle_by_name(project_db, bname)
        if bundle is None:
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
