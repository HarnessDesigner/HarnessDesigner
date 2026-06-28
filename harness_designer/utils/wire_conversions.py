# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import math

from ..geometry.decimal import Decimal as _d


# ---------------------------------------------------------------------------
# Unit conversion constant
# ---------------------------------------------------------------------------
MM2_PER_IN2 = 645.16


# ---------------------------------------------------------------------------
# Stranding tables
# ---------------------------------------------------------------------------

# Generic strand counts by AWG used when strands=0 (stranded but count unknown)
_AWG_STRAND_COUNT = {
    -4: 2109,
    -3: 1665,
    -2: 1330,
    0: 1045,
    1: 817,
    2: 665,
    4: 133,
    6: 133,
    8: 133,
    10: 37,
    12: 19,
    14: 19,
    16: 19,
    18: 19,
    20: 19,
    22: 19,
    24: 19,
    26: 19,
    28: 7,
    30: 7,
}

# Packing factors by strand count
_PACKING_FACTOR = {
    1: 1.000,
    7: 0.750,
    19: 0.780,
    37: 0.800,
    133: 0.830,
    665: 0.850,
    817: 0.850,
    1045: 0.850,
    1330: 0.850,
    1665: 0.850,
    2109: 0.850,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# The functions below have a "strand" parameter. This parameter is
# defaulted to 1 which means a single strcand or a solid wire.
# If this parameter is set to zero that means the wire is a stranded wire
# but the strand count is not known. When that occurs a default value for the
# number of strands is used based on the size of the wire. This is not going
# to produce an exact size for the wire but it will produce a closer estimate
# than calculating it as a solid wire. The calculations are doing using a
# concentric twist for the strands and once again depending on the twist there
# could be a deviation from what the actual diameter of the wire is.
# These functions are a calculated best and not perfect.


def _get_strand_count(awg: int | _d, strands: int | _d) -> int:
    """
    Resolve the strand count used for diameter calculations.

    :param awg: Wire gauge used when ``strands`` is ``0``.
    :type awg: int | _d
    :param strands: Requested strand count.
    :type strands: int | _d
    :returns: Effective strand count.
    :rtype: int
    """

    strands = int(strands)
    if strands == 1:
        return 1

    if strands == 0:
        return _AWG_STRAND_COUNT.get(int(awg), 19)

    return strands


def _get_packing_factor(strand_count: int | _d) -> float:
    """
    Return or interpolate the bundle packing factor for a strand count.

    :param strand_count: Number of strands in the conductor bundle.
    :type strand_count: int | _d
    :returns: Packing factor used to approximate bundle diameter.
    :rtype: float
    """

    if strand_count in _PACKING_FACTOR:
        return _PACKING_FACTOR[strand_count]

    known = sorted(_PACKING_FACTOR.keys())
    for i, k in enumerate(known):
        if strand_count < k:
            if i == 0:
                return _PACKING_FACTOR[k]

            lo, hi = known[i - 1], k
            t = (strand_count - lo) / (hi - lo)
            return _PACKING_FACTOR[lo] + t * (
                _PACKING_FACTOR[hi] - _PACKING_FACTOR[lo])

    return _PACKING_FACTOR[known[-1]]


def _solid_to_bundle(solid_d_mm: float | _d, strand_count: int | _d) -> float:
    """
    Convert a solid-conductor diameter to an approximate bundle diameter.

    :param solid_d_mm: Equivalent solid diameter in millimetres.
    :type solid_d_mm: float | _d
    :param strand_count: Number of strands in the bundle.
    :type strand_count: int | _d
    :returns: Approximate stranded bundle diameter in millimetres.
    :rtype: float
    """

    if strand_count == 1:
        return solid_d_mm

    return solid_d_mm / math.sqrt(_get_packing_factor(strand_count))


def _bundle_to_solid(bundle_d_mm: float | _d, strand_count: int | _d) -> float:
    """
    Convert a bundle diameter back to an equivalent solid diameter.

    :param bundle_d_mm: Stranded bundle diameter in millimetres.
    :type bundle_d_mm: float | _d
    :param strand_count: Number of strands in the bundle.
    :type strand_count: int | _d
    :returns: Equivalent solid diameter in millimetres.
    :rtype: float
    """

    if strand_count == 1:
        return bundle_d_mm

    return bundle_d_mm * math.sqrt(_get_packing_factor(strand_count))


# ---------------------------------------------------------------------------
# Public conversion functions
# ---------------------------------------------------------------------------

def mm2_to_awg(mm2: float | _d, strands: int | _d = 1) -> int:  # NOQA
    """
    Convert cross-sectional area in mm² to AWG.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Unused; AWG is the electrical cross-section and is
        independent of stranding. Retained for API compatibility.
    :type strands: int | _d
    :returns: Rounded AWG value.
    :rtype: int
    """

    # Derive solid-conductor diameter directly to avoid the circular path
    # mm2_to_awg → mm2_to_d_in → mm2_to_d_mm → mm2_to_awg.
    solid_d_mm = 2 * math.sqrt(float(mm2) / math.pi)
    d_in = solid_d_mm / 25.4
    awg = 36 - 39 * math.log(d_in / 0.005, 92)

    return int(round(awg))



def awg_to_mm2(awg: int | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert AWG to electrical cross-sectional area in mm².

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Unused for area conversion; retained for API compatibility.
    :type strands: int | _d
    :returns: Conductor area in square millimetres.
    :rtype: float
    """

    # mm² is always the electrical equivalent cross-section — stranding doesn't change it
    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    d_mm = d_in * 25.4

    return float(round(math.pi / 4 * d_mm ** 2, 4))


def awg_to_d_in(awg: int | _d, strands: int | _d = 1) -> float:
    """
    Convert AWG to approximate conductor diameter in inches.

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Diameter in inches.
    :rtype: float
    """

    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    strand_count = _get_strand_count(awg, strands)
    d_mm = _solid_to_bundle(d_in * 25.4, strand_count)

    return float(round(d_mm / 25.4, 4))


def awg_to_d_mm(awg: int | _d, strands: int | _d = 1) -> float:
    """
    Convert AWG to approximate conductor diameter in millimetres.

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Diameter in millimetres.
    :rtype: float
    """

    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    strand_count = _get_strand_count(awg, strands)

    return float(round(_solid_to_bundle(d_in * 25.4, strand_count), 4))


def d_in_to_d_mm(d_in: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert diameter in inches to millimetres.

    :param d_in: Diameter in inches.
    :type d_in: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Diameter in millimetres.
    :rtype: float
    """

    return float(round(float(d_in) * 25.4, 4))


def d_mm_to_mm2(d_mm: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert diameter in millimetres to area in mm².

    :param d_mm: Diameter in millimetres.
    :type d_mm: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Cross-sectional area in mm².
    :rtype: float
    """

    return float(round(math.pi / 4 * float(d_mm) ** 2, 4))


def mm2_to_d_mm(mm2: float | _d, strands: int | _d = 1) -> float:
    """
    Convert area in mm² to approximate conductor diameter in millimetres.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Approximate diameter in millimetres.
    :rtype: float
    """

    solid_d_mm = 2 * math.sqrt(float(mm2 / math.pi))
    strand_count = _get_strand_count(mm2_to_awg(mm2, strands=1), strands)

    return float(round(_solid_to_bundle(solid_d_mm, strand_count), 4))


def mm2_to_d_in(mm2: float | _d, strands: int | _d = 1) -> float:
    """
    Convert area in mm² to approximate conductor diameter in inches.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Approximate diameter in inches.
    :rtype: float
    """

    return float(round(mm2_to_d_mm(mm2, strands) / 25.4, 4))


def d_mm_to_awg(d_mm: float | _d, strands: int | _d = 1) -> int:
    """
    Convert diameter in millimetres to AWG.

    :param d_mm: Diameter in millimetres.
    :type d_mm: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Rounded AWG value.
    :rtype: int
    """

    # Convert bundle diameter back to solid equivalent, then derive AWG
    approx_awg = mm2_to_awg(d_mm_to_mm2(float(d_mm), strands), strands=1)
    strand_count = _get_strand_count(approx_awg, strands)
    solid_d_mm = _bundle_to_solid(float(d_mm), strand_count)

    return mm2_to_awg(d_mm_to_mm2(solid_d_mm, strands), strands=1)


def mm2_to_in2(mm2: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert area in mm² to square inches.

    :param mm2: Area in square millimetres.
    :type mm2: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Area in square inches.
    :rtype: float
    """

    return float(round(mm2 / MM2_PER_IN2, 4))


def in2_to_mm2(in2: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert area in square inches to mm².

    :param in2: Area in square inches.
    :type in2: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Area in square millimetres.
    :rtype: float
    """

    return float(round(in2 * MM2_PER_IN2, 4))
