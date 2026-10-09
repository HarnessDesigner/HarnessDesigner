# rope_pull.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The peg-board rope-pull solver's compiled hot path -- see
``rope_pull.rope_pull_py`` for the pure-Python reference this is a
line-for-line port of; that module's own docstring carries the full
design rationale (the whole-chain/stateless model, the reference
skeleton, the proportional slack split, the closed-form bow count and
height derivation, and why this works unchanged for either a wire's or
a bundle's peg-board chain). This file only documents what differs
because it is Cython.

``drag_end`` here is a plain ``int`` (``0`` = start anchor, ``1`` = stop
anchor, ``2`` = interior waypoint) rather than the pure-Python module's
``rope_pull_py.DragEnd`` -- this module is pure numeric geometry with no
Python-level objects at its boundary at all (``BUNDLE_PLACEMENT.md``
section 6b's own "no DB and no objects" scope, taken literally all the
way down to not importing ``enum.Enum`` either); ``rope_pull.__init__``'s
dispatcher is what translates a real ``DragEnd`` to this ``int`` before
calling in, and translates this function's plain ``(accepted, points)``
tuple back into a ``rope_pull_py.ChainResult`` on the way out, so every
other caller sees the same return shape regardless of which
implementation actually ran.
"""

from libc.math cimport hypot, sqrt, floor


cdef double _EPS = 1e-9
cdef double _MIN_DIAMETER_MM = 1.0

cdef int _START = 0
cdef int _STOP = 1
cdef int _WAYPOINT = 2


cdef double _polyline_length(list points):
    cdef double total = 0.0
    cdef int i
    cdef double ax, az, bx, bz

    for i in range(len(points) - 1):
        ax = points[i][0]
        az = points[i][1]
        bx = points[i + 1][0]
        bz = points[i + 1][1]
        total += hypot(bx - ax, bz - az)

    return total


cdef list _solve_span(double ax, double az, double bx, double bz, double target_length,
                      double diameter, double zigzag_length_factor, double threshold_factor,
                      double tolerance):
    """One skeleton segment's own zig-zag -- see ``rope_pull_py._solve_span``
    for the count and threshold rules this follows exactly.
    """
    cdef double dx, dz, straight, spacing, threshold, excess_sq, excess, height
    cdef double ux, uz, px, pz
    cdef double t_zero, t_apex, sign, apex_x, apex_z
    cdef int count, i, max_count
    cdef list waypoints

    dx = bx - ax
    dz = bz - az
    straight = hypot(dx, dz)

    if target_length <= straight + tolerance:
        return []

    spacing = zigzag_length_factor * diameter
    if spacing < _EPS:
        spacing = _EPS
    max_count = <int> floor(straight / spacing)
    if max_count < 1:
        max_count = 1

    threshold = threshold_factor * diameter
    if threshold < _EPS:
        threshold = _EPS

    excess_sq = target_length * target_length - straight * straight
    if excess_sq < 0.0:
        excess_sq = 0.0
    excess = sqrt(excess_sq)

    count = <int> floor(excess / (2.0 * threshold))
    if count < 1:
        count = 1
    if count > max_count:
        count = max_count

    height = excess / (2.0 * count)

    if straight < _EPS:
        ux = 1.0
        uz = 0.0
    else:
        ux = dx / straight
        uz = dz / straight

    # perpendicular to (ux, uz) in the peg-board (x, z) plane -- see
    # rope_pull_py._solve_span's own comment for the bow_midpoint
    # convention this matches.
    px = uz
    pz = -ux

    waypoints = []
    for i in range(count):
        t_apex = (i + 0.5) / <double> count

        if i % 2 == 0:
            sign = 1.0
        else:
            sign = -1.0

        apex_x = ax + t_apex * dx + px * height * sign
        apex_z = az + t_apex * dz + pz * height * sign
        waypoints.append((apex_x, apex_z))

    return waypoints


def solve_chain(tuple start, tuple stop, double required_length, int drag_end,
                tuple target, double diameter_mm, double zigzag_length_factor,
                double threshold_factor, double tolerance=1e-6):
    """See ``rope_pull.rope_pull_py.solve_chain`` -- identical behavior;
    *drag_end* is ``0``/``1``/``2`` (start/stop/waypoint) instead of a
    :class:`~rope_pull.rope_pull_py.DragEnd`.

    :returns: ``(accepted, points)`` -- a plain 2-tuple (not a
        :class:`~rope_pull.rope_pull_py.ChainResult`, to keep this
        boundary free of Python-level helper types); *points* is a list
        of ``(x, z)`` float tuples, meaningful only when *accepted* is
        ``True``.
    """
    cdef double sx, sz, ex, ez, tx, tz
    cdef double base_length, needed_slack, straight, share, span_target, diameter
    cdef double ax, az, bx, bz
    cdef list skeleton, points
    cdef int span_count, i

    sx = <double> start[0]
    sz = <double> start[1]
    ex = <double> stop[0]
    ez = <double> stop[1]
    tx = <double> target[0]
    tz = <double> target[1]

    if drag_end == _START:
        skeleton = [(tx, tz), (ex, ez)]
    elif drag_end == _STOP:
        skeleton = [(sx, sz), (tx, tz)]
    else:
        skeleton = [(sx, sz), (tx, tz), (ex, ez)]

    base_length = _polyline_length(skeleton)

    if base_length > required_length + tolerance:
        return False, []

    needed_slack = required_length - base_length
    span_count = len(skeleton) - 1

    diameter = diameter_mm
    if diameter < _MIN_DIAMETER_MM:
        diameter = _MIN_DIAMETER_MM

    points = [skeleton[0]]

    for i in range(span_count):
        ax = skeleton[i][0]
        az = skeleton[i][1]
        bx = skeleton[i + 1][0]
        bz = skeleton[i + 1][1]
        straight = hypot(bx - ax, bz - az)

        if base_length < _EPS:
            share = needed_slack / span_count
        else:
            share = needed_slack * (straight / base_length)

        span_target = straight + share

        points.extend(_solve_span(ax, az, bx, bz, span_target, diameter,
                                  zigzag_length_factor, threshold_factor, tolerance))
        points.append((bx, bz))

    return True, points
