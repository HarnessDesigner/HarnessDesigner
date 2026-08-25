# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Small screen-space hit-test helpers shared by the ring/tick pick tests."""

import math

from .... import check_types as _check_types


@_check_types.do
def point_near_segment(px: float, py: float, ax: float, ay: float,
                       bx: float, by: float, tolerance: float) -> bool:
    """Return whether (px, py) is within *tolerance* pixels of segment A-B.

    :param px: Mouse X in screen pixels.
    :param py: Mouse Y in screen pixels.
    :param ax: Segment start X.
    :param ay: Segment start Y.
    :param bx: Segment end X.
    :param by: Segment end Y.
    :param tolerance: Maximum pixel distance still counted as a hit.
    :rtype: bool
    """
    dx = bx - ax
    dy = by - ay
    len_sq = dx * dx + dy * dy

    if len_sq < 1e-9:
        t = 0.0
    else:
        t = ((px - ax) * dx + (py - ay) * dy) / len_sq
        t = max(0.0, min(1.0, t))

    nearest_x = ax + t * dx
    nearest_y = ay + t * dy

    dist = math.hypot(px - nearest_x, py - nearest_y)
    return dist <= tolerance
