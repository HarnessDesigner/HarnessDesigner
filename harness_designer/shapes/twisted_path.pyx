# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# twisted_path.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The path building behind ``objects.objects_3d.wire.Wire._twist_segments``, in C, on plain arrays.

One call, :func:`build_path`, takes a wire's straight segments (start, rotation matrix, quaternion, length, "starts where the
previous one ends") and returns, for every piece that is drawn, its position, rotation (quaternion and matrix), length, twist
phase, the two mitres and the ring count -- everything ``shapes.twisted_wire.TwistedTube.draw`` needs. It does what
``twisted_wire.round_bends`` + the frame of each new chord + ``twisted_wire.plan`` + ``twisted_wire.ring_count`` do, in that order,
and those pure-Python functions stay as its reference (and as what the ribbon code still calls); read their docstrings for what
each step means. Nothing here makes a Python object per piece: the old path built a ``Point`` and an ``Angle`` (through the
Decimal-backed geometry classes) for every chord, which was about 70 percent of the rebuild.

The frame of a chord is the minimal rotation taking +Z to the chord's direction, as a quaternion ``(w, x, y, z)`` and the rotation
matrix of that quaternion (the columns are the piece's local axes in world space); it is what
``Wire._rotation_from_direction`` gives, to about 1e-7 (that one goes through float32). A piece cut from an input segment keeps
that segment's own rotation, so a ribbon cable's roll survives.

The epsilons and the U-turn limit below are the same numbers as in ``twisted_wire`` (``_U_TURN``, ``_ROUND_MIN``, ``_STRAIGHT``);
the tunables that other code reads (the bend step, rings per turn, the ring limit) are passed in so there is one copy of them.
"""

import numpy as np

from libc.math cimport sqrt, sin, cos, tan, acos, atan2, ceil, fabs, M_PI


# A corner sharper than this (cosine of the angle between the two directions) is a U-turn: left as it is.
cdef double _U_TURN = -0.99

# A bend smaller than this (radians, half a degree) is not rounded.
cdef double _ROUND_MIN = 0.5 * M_PI / 180.0

# A bend smaller than this (radians) needs no mitre.
cdef double _STRAIGHT = 1e-4

# A piece of a segment shorter than this (mm) is dropped.
cdef double _MIN_STRAIGHT = 1e-6


cdef inline double _clamp_unit(double value) noexcept nogil:
    if value > 1.0:
        return 1.0

    if value < -1.0:
        return -1.0

    return value


cdef void _frame(double dx, double dy, double dz, double* q, double* m) noexcept nogil:
    """The minimal rotation taking +Z to the unit vector (dx, dy, dz): the quaternion into q[0:4] as (w, x, y, z), and its rotation
    matrix, row major, into m[0:9]."""
    cdef double w, x, y, z, n

    if fabs(dz - 1.0) < 1e-6:
        w = 1.0
        x = 0.0
        y = 0.0
        z = 0.0
    elif fabs(dz + 1.0) < 1e-6:
        w = 0.0
        x = 1.0
        y = 0.0
        z = 0.0
    else:
        # axis = z cross d = (-dy, dx, 0); the half-angle form of the same rotation
        w = 1.0 + dz
        x = -dy
        y = dx
        z = 0.0
        n = sqrt(w * w + x * x + y * y)
        w = w / n
        x = x / n
        y = y / n

    q[0] = w
    q[1] = x
    q[2] = y
    q[3] = z

    m[0] = 1.0 - 2.0 * (y * y + z * z)
    m[1] = 2.0 * (x * y - z * w)
    m[2] = 2.0 * (x * z + y * w)
    m[3] = 2.0 * (x * y + z * w)
    m[4] = 1.0 - 2.0 * (x * x + z * z)
    m[5] = 2.0 * (y * z - x * w)
    m[6] = 2.0 * (x * z - y * w)
    m[7] = 2.0 * (y * z + x * w)
    m[8] = 1.0 - 2.0 * (x * x + y * y)


cdef double _transport_delta(const double* p, const double* c) noexcept nogil:
    """``twisted_wire._transport_delta``: the angle, about the current piece's direction, from its own X axis to the previous
    piece's X axis carried round the bend by the minimal rotation. *p* and *c* are 3x3 row-major rotation matrices (column j of m
    is (m[j], m[3 + j], m[6 + j]))."""
    cdef double d1x = p[2]
    cdef double d1y = p[5]
    cdef double d1z = p[8]
    cdef double d2x = c[2]
    cdef double d2y = c[5]
    cdef double d2z = c[8]
    cdef double x1x = p[0]
    cdef double x1y = p[3]
    cdef double x1z = p[6]

    cdef double ax = d1y * d2z - d1z * d2y
    cdef double ay = d1z * d2x - d1x * d2z
    cdef double az = d1x * d2y - d1y * d2x
    cdef double sine = sqrt(ax * ax + ay * ay + az * az)
    cdef double cosine = d1x * d2x + d1y * d2y + d1z * d2z

    cdef double kx, ky, kz, angle, ca, sa, kdx, kdy, kdz, kdot
    cdef double carried_x = x1x
    cdef double carried_y = x1y
    cdef double carried_z = x1z

    if sine >= 1e-9:
        kx = ax / sine
        ky = ay / sine
        kz = az / sine
        angle = atan2(sine, cosine)
        ca = cos(angle)
        sa = sin(angle)

        # k cross x1
        kdx = ky * x1z - kz * x1y
        kdy = kz * x1x - kx * x1z
        kdz = kx * x1y - ky * x1x
        kdot = kx * x1x + ky * x1y + kz * x1z

        carried_x = x1x * ca + kdx * sa + kx * kdot * (1.0 - ca)
        carried_y = x1y * ca + kdy * sa + ky * kdot * (1.0 - ca)
        carried_z = x1z * ca + kdz * sa + kz * kdot * (1.0 - ca)

    # carried . (current's Y axis), carried . (current's X axis)
    return atan2(carried_x * c[1] + carried_y * c[4] + carried_z * c[7],
                 carried_x * c[0] + carried_y * c[3] + carried_z * c[6])


cdef int _ring_count(double length, double rate, double start_fade, double end_fade, double outer_radius,
                     int samples_per_turn, int max_rings) noexcept nogil:
    """``twisted_wire.ring_count``."""
    cdef double turns = fabs(rate) * length / (2.0 * M_PI)
    cdef long rings = <long>ceil(turns * samples_per_turn) + 1
    cdef long needed

    if start_fade > 0.0 or end_fade > 0.0:
        needed = <long>ceil(length / outer_radius) + 1

        if needed > rings:
            rings = needed

    if rings < 2:
        rings = 2

    if rings > max_rings:
        rings = max_rings

    return <int>rings


def build_path(double[:, ::1] starts, double[:, :, ::1] rotations, double[:, ::1] quats, double[::1] lengths,
               unsigned char[::1] joined, double bend_radius, bint rounded, double rate, double outer_radius,
               double start_phase, double bend_step, int samples_per_turn, int max_rings):
    """The pieces of a bent wire with everything needed to draw them.

    :param starts: ``(n, 3)`` world position of each input segment's start.
    :param rotations: ``(n, 3, 3)`` each input segment's rotation matrix (columns are its local axes in world space; column 2 is
        its direction).
    :param quats: ``(n, 4)`` each input segment's rotation as ``(w, x, y, z)``.
    :param lengths: ``(n,)`` each input segment's length, mm.
    :param joined: ``(n,)`` uint8, non-zero where segment ``i`` starts where segment ``i - 1`` ends (``joined[0]`` is never read).
    :param bend_radius: The radius every corner is rounded with, mm (``twisted_wire.BEND_RADIUS_DIAMETERS`` cable diameters).
    :param rounded: Round the corners (a ribbon cable is not rounded).
    :param rate: Twist rate, radians per mm.
    :param outer_radius: Radius of the circle that holds the whole cable, mm.
    :param start_phase: The first piece's phase, radians.
    :param bend_step: The turn of one chord of a rounded corner, radians (``twisted_wire.BEND_STEP``).
    :param samples_per_turn: Rings per full turn (``twisted_wire.SAMPLES_PER_TURN``).
    :param max_rings: The most rings a piece gets (``twisted_wire.MAX_RINGS``).
    :returns: ``(positions (m, 3), quats (m, 4), lengths (m,), phases (m,), start mitres (m, 4), end mitres (m, 4), rings (m,),
        sources (m,), matrices (m, 3, 3))``, one row per piece in path order. A mitre is ``(x, y, z, fade)`` as in
        ``twisted_wire.SegmentTwist``. *sources* is the input segment a piece is cut from, or -1 for a chord of a rounded corner.
    """
    cdef Py_ssize_t n = starts.shape[0]
    cdef Py_ssize_t per_corner = <Py_ssize_t>ceil(M_PI / bend_step) + 2
    cdef Py_ssize_t cap = n * (per_corner + 1)
    cdef Py_ssize_t i, k, j, r, c, m, steps, src

    cdef double cosine, bend, cut, half, cut_start, cut_end, tight, turn, ang, sa, ca, straight
    cdef double dx, dy, dz, px, py, pz, sx, sy, sz, snorm, dotp
    cdef double ax, ay, az, lx, ly, lz, qx, qy, qz, cx, cy, cz, clen
    cdef double previous_end, fade, d1x, d1y, d1z, d2x, d2y, d2z, mitre

    cdef double[::1] cuts
    cdef double[::1] bends
    cdef double[:, ::1] pos
    cdef double[:, ::1] dirs
    cdef double[::1] plen
    cdef unsigned char[::1] pjoin
    cdef int[::1] psrc
    cdef double[:, ::1] quat
    cdef double[:, :, ::1] rot
    cdef double[::1] phase
    cdef double[:, ::1] mit_start
    cdef double[:, ::1] mit_end
    cdef int[::1] ring_out

    cuts_arr = np.zeros(n)
    bends_arr = np.zeros(n)
    pos_arr = np.empty((cap, 3))
    dirs_arr = np.empty((cap, 3))
    plen_arr = np.empty(cap)
    pjoin_arr = np.zeros(cap, dtype=np.uint8)
    psrc_arr = np.empty(cap, dtype=np.intc)
    quat_arr = np.empty((cap, 4))
    rot_arr = np.empty((cap, 3, 3))
    phase_arr = np.zeros(cap)
    mit_start_arr = np.zeros((cap, 4))
    mit_end_arr = np.zeros((cap, 4))
    ring_arr = np.empty(cap, dtype=np.intc)

    cuts = cuts_arr
    bends = bends_arr
    pos = pos_arr
    dirs = dirs_arr
    plen = plen_arr
    pjoin = pjoin_arr
    psrc = psrc_arr
    quat = quat_arr
    rot = rot_arr
    phase = phase_arr
    mit_start = mit_start_arr
    mit_end = mit_end_arr
    ring_out = ring_arr

    # ---- round the corners: how far each corner cuts into its two segments ----
    if rounded:
        for i in range(1, n):
            if joined[i] == 0:
                continue

            cosine = (rotations[i - 1, 0, 2] * rotations[i, 0, 2] + rotations[i - 1, 1, 2] * rotations[i, 1, 2] +
                      rotations[i - 1, 2, 2] * rotations[i, 2, 2])

            if cosine <= _U_TURN:
                continue

            bend = acos(_clamp_unit(cosine))

            if bend < _ROUND_MIN:
                continue

            bends[i] = bend
            cut = bend_radius * tan(bend * 0.5)

            half = lengths[i - 1] * 0.5
            if half < cut:
                cut = half

            half = lengths[i] * 0.5
            if half < cut:
                cut = half

            cuts[i] = cut

    # ---- the pieces, in path order ----
    m = 0

    for i in range(n):
        dx = rotations[i, 0, 2]
        dy = rotations[i, 1, 2]
        dz = rotations[i, 2, 2]

        cut_start = cuts[i]
        cut_end = 0.0

        if i + 1 < n:
            cut_end = cuts[i + 1]

        if cut_start > 0.0:
            px = rotations[i - 1, 0, 2]
            py = rotations[i - 1, 1, 2]
            pz = rotations[i - 1, 2, 2]

            tight = cut_start / tan(bends[i] * 0.5)
            dotp = px * dx + py * dy + pz * dz
            sx = dx - px * dotp
            sy = dy - py * dotp
            sz = dz - pz * dotp
            snorm = sqrt(sx * sx + sy * sy + sz * sz)
            sx = sx / snorm
            sy = sy / snorm
            sz = sz / snorm

            steps = <Py_ssize_t>ceil(bends[i] / bend_step)
            if steps < 1:
                steps = 1

            turn = bends[i] / steps

            ax = starts[i, 0] - px * cut_start
            ay = starts[i, 1] - py * cut_start
            az = starts[i, 2] - pz * cut_start
            lx = ax
            ly = ay
            lz = az

            for k in range(1, steps + 1):
                ang = turn * k
                sa = sin(ang)
                ca = cos(ang)

                qx = ax + tight * (px * sa + sx * (1.0 - ca))
                qy = ay + tight * (py * sa + sy * (1.0 - ca))
                qz = az + tight * (pz * sa + sz * (1.0 - ca))

                cx = qx - lx
                cy = qy - ly
                cz = qz - lz
                clen = sqrt(cx * cx + cy * cy + cz * cz)

                pos[m, 0] = lx
                pos[m, 1] = ly
                pos[m, 2] = lz
                dirs[m, 0] = cx / clen
                dirs[m, 1] = cy / clen
                dirs[m, 2] = cz / clen
                plen[m] = clen
                pjoin[m] = 1
                psrc[m] = -1
                m += 1

                lx = qx
                ly = qy
                lz = qz

        straight = lengths[i] - cut_start - cut_end

        if straight > _MIN_STRAIGHT:
            pos[m, 0] = starts[i, 0] + dx * cut_start
            pos[m, 1] = starts[i, 1] + dy * cut_start
            pos[m, 2] = starts[i, 2] + dz * cut_start
            dirs[m, 0] = dx
            dirs[m, 1] = dy
            dirs[m, 2] = dz
            plen[m] = straight

            if cut_start > 0.0 or (i > 0 and joined[i] != 0):
                pjoin[m] = 1
            else:
                pjoin[m] = 0

            psrc[m] = <int>i
            m += 1

    # ---- each piece's frame: an input segment's own rotation, or the minimal one for a chord ----
    for i in range(m):
        src = psrc[i]

        if src >= 0:
            for j in range(4):
                quat[i, j] = quats[src, j]

            for r in range(3):
                for c in range(3):
                    rot[i, r, c] = rotations[src, r, c]
        else:
            _frame(dirs[i, 0], dirs[i, 1], dirs[i, 2], &quat[i, 0], &rot[i, 0, 0])

    # ---- the twist: phase carried round every bend, and the mitre at both ends of every joint ----
    for i in range(m):
        mit_start[i, 2] = 1.0
        mit_end[i, 2] = 1.0

    if m > 0:
        phase[0] = start_phase

    for i in range(1, m):
        previous_end = phase[i - 1] + rate * plen[i - 1]

        if pjoin[i] == 0:
            phase[i] = previous_end
            continue

        d1x = rot[i - 1, 0, 2]
        d1y = rot[i - 1, 1, 2]
        d1z = rot[i - 1, 2, 2]
        d2x = rot[i, 0, 2]
        d2y = rot[i, 1, 2]
        d2z = rot[i, 2, 2]
        cosine = d1x * d2x + d1y * d2y + d1z * d2z

        if cosine <= _U_TURN:
            phase[i] = previous_end
            continue

        phase[i] = previous_end + _transport_delta(&rot[i - 1, 0, 0], &rot[i, 0, 0])

        bend = acos(_clamp_unit(cosine))

        if bend < _STRAIGHT:
            continue

        # The ring shift is at most outer_radius * tan(bend / 2); fading it in over twice that keeps the rings in order.
        fade = 2.0 * outer_radius * tan(bend * 0.5)

        # each end gets the OTHER piece's direction, in its own frame: current^T d1 for the start, previous^T d2 for the end
        mit_start[i, 0] = rot[i, 0, 0] * d1x + rot[i, 1, 0] * d1y + rot[i, 2, 0] * d1z
        mit_start[i, 1] = rot[i, 0, 1] * d1x + rot[i, 1, 1] * d1y + rot[i, 2, 1] * d1z
        mit_start[i, 2] = rot[i, 0, 2] * d1x + rot[i, 1, 2] * d1y + rot[i, 2, 2] * d1z

        mitre = plen[i] * 0.5
        if fade < mitre:
            mitre = fade
        mit_start[i, 3] = mitre

        mit_end[i - 1, 0] = rot[i - 1, 0, 0] * d2x + rot[i - 1, 1, 0] * d2y + rot[i - 1, 2, 0] * d2z
        mit_end[i - 1, 1] = rot[i - 1, 0, 1] * d2x + rot[i - 1, 1, 1] * d2y + rot[i - 1, 2, 1] * d2z
        mit_end[i - 1, 2] = rot[i - 1, 0, 2] * d2x + rot[i - 1, 1, 2] * d2y + rot[i - 1, 2, 2] * d2z

        mitre = plen[i - 1] * 0.5
        if fade < mitre:
            mitre = fade
        mit_end[i - 1, 3] = mitre

    for i in range(m):
        ring_out[i] = _ring_count(plen[i], rate, mit_start[i, 3], mit_end[i, 3], outer_radius, samples_per_turn, max_rings)

    return (pos_arr[:m], quat_arr[:m], plen_arr[:m], phase_arr[:m], mit_start_arr[:m], mit_end_arr[:m], ring_arr[:m],
            psrc_arr[:m], rot_arr[:m])
