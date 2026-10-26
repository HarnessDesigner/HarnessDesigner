# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# wire_service_loop_search.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The roll/slide collision search behind ``WireServiceLoop._resolve_collision``.

Adding a wire service loop used to freeze the app ("Application Not
Responding"): every candidate pose was tested mesh against mesh (about 6 s
for ONE test), and a placement tries 16 rolls at every slide step on every
mouse move. Boxes fixed the test itself; this module fixes what is left, the
cost of a pose. In numpy each pose cost ~610 us (``Angle.from_quat`` alone is
~240 us, ``points @ angle`` ~55 us) however cheap the test was, so a search
that had to slide ~30 steps took ~0.5 s per mouse move and one where nothing
clears ~8 s. Here a pose is a quaternion product, a 3x3 matrix and a handful
of float compares.

One ``LoopSearch`` is built per move session by
``WireServiceLoop.begin_move_session`` from everything the loop can hit, and
``search`` then answers every ``_resolve_collision`` of that session. Nothing
in the search touches Python objects: no ``Angle``, no numpy.

Two stages per candidate
------------------------
1. **Boxes** (the hit list). A candidate is an oriented box in the bounds
   pool's corner order (0 = min corner, 1 toggles x, 3 toggles y, 4 toggles
   z): one per wire section (``objects_3d.wire.Wire.segment_obbs``, because a
   wire's pool OBB is only the axis-aligned envelope of its whole path), one
   for another loop or a marker (its pool OBB). The loop is the box
   ``local_obb`` scaled by ``scale``. Two boxes overlap when a separating-axis
   test finds no gap (touching counts). This is conservative: a coil does not
   fill its box.
2. **Mesh** (only for the boxes that overlap). The loop's own mesh vertices
   (``loop_vertices``, ~30,000 of them, indexed once in a 10x10x10 grid that
   is cached) are tested against the candidate's real shape:

   - ``KIND_CYLINDER``: a wire section's mesh IS a cylinder (360-sided), so the
     shape is the exact cylinder inscribed in its box along the box's z axis
     (radius = half the box's x width). A vertex inside it, ends flat and
     touching counted, means the loop's surface touches the wire. The loop's
     tessellation (~0.2 mm) is far finer than a wire, so a surface can't
     cross the wire without a vertex landing inside it: this is the mesh
     test's answer without 10,000 x 720 triangle pairs.
   - ``KIND_BOX``: another loop or a marker is its own box, so the test is a
     loop vertex inside that box (the loop's coil against the other thing's
     bounding box: tight on our side, still conservative on theirs).

   A candidate collides only when BOTH stages say so. A wire passing through
   the coil's hole, or a box sitting in it, touches no vertex: clear.

Rotation: about the WIRE, through the pivot
-------------------------------------------
The loop is a coil in a wire, so it can only spin about the wire. ``search``
is handed that axle (``axis``: the direction of the line through the wire's two
nearest points, one each side of the loop) and the pivot ``P`` (where that
line meets the line through the loop's own start and stop points; ``P`` is on
the wire, usually the start point). A roll by ``theta`` is the rigid rotation
``Q`` of everything about the axis through ``P``::

    start' = P + Q (start - P)        stop' = P + Q (stop - P)
    R'     = Q R0                     (the object's own angle)

The last line is the part that is easy to get wrong. The object (and its VBO)
turns about its OWN origin (the start point), not about ``P``, so the rotation
handed back with the new start and stop points is the composition ``Q R0``:
the roll applied AFTER the current orientation, about a WORLD axis, i.e. the
quaternion ``q_Q (x) q0``. (``q0 (x) q_Q`` would twist the mesh about a vector
in its own frame and drag the stop point off the wire.) ``pose_at`` returns
exactly this, so it can be checked against a rigidly rotated mesh.

Sliding moves everything along the axis: ``P``, start and stop all gain
``t * axis``, so the roll is unchanged.

Search order
------------
At the current spot the roll is tried at ``roll_deg`` steps outward from the
current angle, +k then -k, and the first clear angle wins: the NEAREST clear
roll, found without knowing which side it is on. Only when both sides clear at
the same distance is the side with less contact at the first step taken (the
vertices inside an obstacle; equal -> positive). If no roll clears, the loop
slides along the axis, ``slide_step`` at a time up to the limits, and at each
spot scans the full turn at ``slide_roll_deg`` (coarser, because a long slide
multiplies the work); the clear spot closest to the start wins.

Rotation convention
-------------------
Poses are quaternions ``[w, x, y, z]``, turned into the column-vector matrix
``R`` that ``Angle.as_matrix_numpy`` holds (``R @ v`` rotates a column vector;
the rest of the codebase applies it to rows as ``v @ R.T``, which lands in the
same place). The loop's box axes are therefore the COLUMNS of ``R``, and a
point of the loop's mesh lands at ``R @ (scale * v) + start``; the candidate is
moved into the loop's own frame with ``R.T @ (x - start) / scale`` (the loop's
scale is uniform, so a cylinder stays a cylinder).
"""

from libc.math cimport cos, fabs, floor, sin
import numpy as np

cdef double _PI = 3.141592653589793
cdef double _EPS = 1e-9
cdef int _GRID = 10
cdef signed char _BOX = 0
cdef signed char _CYLINDER = 1

KIND_BOX = 0
KIND_CYLINDER = 1

# loop mesh -> grid, keyed by the mesh's bytes (one loop mesh exists; the build
# sorts ~30,000 points, worth doing once per run, not once per move session)
_GRID_CACHE = {}


def _grid_for(loop_vertices):
    verts = np.ascontiguousarray(loop_vertices, dtype=np.float64).reshape(-1, 3)
    key = (verts.shape[0], hash(verts.tobytes()))
    grid = _GRID_CACHE.get(key)

    if grid is None:
        lo = verts.min(axis=0)
        cell = np.maximum(verts.max(axis=0) - lo, 1e-9) / _GRID
        idx = np.minimum(((verts - lo) / cell).astype(np.int64), _GRID - 1)
        cell_id = (idx[:, 0] * _GRID + idx[:, 1]) * _GRID + idx[:, 2]
        order = np.argsort(cell_id, kind='stable')
        start = np.zeros(_GRID ** 3 + 1, dtype=np.int32)
        start[1:] = np.cumsum(np.bincount(cell_id, minlength=_GRID ** 3))
        grid = (np.ascontiguousarray(verts[order]), start, lo, cell)
        _GRID_CACHE[key] = grid

    return grid


cdef void _quat_mul(double* a, double* b, double* out) noexcept nogil:
    # Hamilton product of two [w, x, y, z] quaternions
    out[0] = a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]
    out[1] = a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2]
    out[2] = a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1]
    out[3] = a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]


cdef void _quat_to_matrix(double* q, double* R) noexcept nogil:
    # row-major 3x3, column-vector convention; tolerant of a non-unit q
    cdef double w = q[0]
    cdef double x = q[1]
    cdef double y = q[2]
    cdef double z = q[3]
    cdef double s = 2.0 / (w * w + x * x + y * y + z * z)

    R[0] = 1.0 - s * (y * y + z * z)
    R[1] = s * (x * y - w * z)
    R[2] = s * (x * z + w * y)
    R[3] = s * (x * y + w * z)
    R[4] = 1.0 - s * (x * x + z * z)
    R[5] = s * (y * z - w * x)
    R[6] = s * (x * z - w * y)
    R[7] = s * (y * z + w * x)
    R[8] = 1.0 - s * (x * x + y * y)


cdef void _compose(double* p1, double* p2, double* P, double* a, double* q0, double t, double theta,
                   double* q_out, double* p1_out, double* p2_out) noexcept nogil:
    # the pose after rolling by theta about the unit axis a through P, having
    # slid t along it: q' = q_Q (x) q0 (the roll comes AFTER the current
    # orientation, about a WORLD axis), p' = P + Q (p - P) + t * a
    cdef double h = 0.5 * theta
    cdef double sh = sin(h)
    cdef double qq[4]
    cdef double Rq[9]
    cdef int i

    qq[0] = cos(h)
    qq[1] = a[0] * sh
    qq[2] = a[1] * sh
    qq[3] = a[2] * sh
    _quat_mul(qq, q0, q_out)
    _quat_to_matrix(qq, Rq)

    for i in range(3):
        p1_out[i] = (P[i] + Rq[3 * i] * (p1[0] - P[0]) + Rq[3 * i + 1] * (p1[1] - P[1])
                     + Rq[3 * i + 2] * (p1[2] - P[2]) + t * a[i])
        p2_out[i] = (P[i] + Rq[3 * i] * (p2[0] - P[0]) + Rq[3 * i + 1] * (p2[1] - P[1])
                     + Rq[3 * i + 2] * (p2[2] - P[2]) + t * a[i])


cdef bint _clip(double* p, double* d, double* lo, double* hi,
                double* t0_out, double* t1_out) noexcept nogil:
    # the part of the segment p + t * d, t in [0, 1], inside the box [lo, hi]
    cdef double t0 = 0.0
    cdef double t1 = 1.0
    cdef double inv, ta, tb, tmp
    cdef int i

    for i in range(3):
        if fabs(d[i]) < 1e-14:
            if p[i] < lo[i] or p[i] > hi[i]:
                return False
        else:
            inv = 1.0 / d[i]
            ta = (lo[i] - p[i]) * inv
            tb = (hi[i] - p[i]) * inv

            if ta > tb:
                tmp = ta
                ta = tb
                tb = tmp

            if ta > t0:
                t0 = ta

            if tb < t1:
                t1 = tb

            if t0 > t1:
                return False

    t0_out[0] = t0
    t1_out[0] = t1

    return True


cdef class LoopSearch:
    cdef Py_ssize_t n
    cdef double[:, ::1] bmin
    cdef double[:, ::1] bmax
    cdef double[:, ::1] bcenter
    cdef double[:, ::1] bhalf
    cdef double[:, :, ::1] baxes
    cdef signed char[::1] bkind
    cdef double[:, ::1] cyl_a
    cdef double[:, ::1] cyl_d
    cdef double[::1] cyl_r
    cdef double lcenter[3]
    cdef double lhalf[3]
    cdef double lscale
    cdef double[:, ::1] gpts
    cdef int[::1] gstart
    cdef double gmin[3]
    cdef double gcell[3]
    cdef double ginv[3]

    def __init__(self, boxes, kinds, local_obb, scale, loop_vertices):
        """
        :param boxes: every box the loop can hit, ``(K, 8, 3)`` or a list of
            ``(8, 3)`` arrays, in the pool's corner order; may be empty.
        :param kinds: ``K`` ints, ``KIND_BOX`` or ``KIND_CYLINDER`` (the box
            holds a cylinder along its z axis), one per box.
        :param local_obb: the loop mesh's own ``(8, 3)`` OBB, unscaled.
        :param scale: the loop's ``(3,)`` scale, uniform.
        :param loop_vertices: the loop mesh's points, unscaled, ``(M, 3)``
            (a triangle soup is fine).
        """
        boxes = np.ascontiguousarray(boxes, dtype=np.float64).reshape(-1, 8, 3)
        kinds = np.ascontiguousarray(kinds, dtype=np.int8).reshape(-1)
        self.n = boxes.shape[0]

        if kinds.shape[0] != self.n:
            raise ValueError(f'{kinds.shape[0]} kinds for {self.n} boxes')

        scale = np.asarray(scale, dtype=np.float64)
        if np.abs(scale - scale[0]).max() > 1e-9 * max(1.0, abs(scale[0])):
            raise ValueError(f'the loop scale must be uniform, got {scale.tolist()}')

        bmin = np.ascontiguousarray(boxes.min(axis=1))
        bmax = np.ascontiguousarray(boxes.max(axis=1))

        c0 = boxes[:, 0]
        u = boxes[:, 1] - c0
        v = boxes[:, 3] - c0
        w = boxes[:, 4] - c0
        lu = np.linalg.norm(u, axis=1)
        lv = np.linalg.norm(v, axis=1)
        lw = np.linalg.norm(w, axis=1)

        flat = (lu < 1e-9) | (lv < 1e-9) | (lw < 1e-9)
        lu1 = np.where(flat, 1.0, lu)
        lv1 = np.where(flat, 1.0, lv)
        lw1 = np.where(flat, 1.0, lw)

        center = c0 + (u + v + w) / 2.0
        half = np.stack([lu, lv, lw], axis=1) / 2.0
        axes = np.stack([u / lu1[:, None], v / lv1[:, None], w / lw1[:, None]], axis=1)

        # a flat box has no usable axis: fall back to its own axis-aligned bounds
        center[flat] = (bmin[flat] + bmax[flat]) / 2.0
        half[flat] = (bmax[flat] - bmin[flat]) / 2.0
        axes[flat] = np.eye(3)
        kinds = np.where(flat, KIND_BOX, kinds).astype(np.int8)

        # the cylinder inscribed in a KIND_CYLINDER box: axis along the box's z
        # (its two z faces' centres), radius half the x width
        # (The real boxes are built from float32 positions and matrices, so a true
        # cylinder's box is square only to float32 noise -- 2e-6 mm at 50 mm from the
        # origin, 8e-5 mm at 2 m. 1% of the radius is ~100x that, and a box that really
        # is not square is off by far more.)
        cyl = kinds == KIND_CYLINDER
        if np.any(np.abs(half[cyl, 0] - half[cyl, 1]) > 0.01 * half[cyl, 0]):
            raise ValueError('a KIND_CYLINDER box must be square across its x and y')

        zdir = axes[:, 2]
        cyl_a = center - zdir * half[:, 2:3]
        cyl_d = zdir * (2.0 * half[:, 2:3])
        cyl_r = (half[:, 0] + half[:, 1]) / 2.0

        self.bmin = bmin
        self.bmax = bmax
        self.bcenter = np.ascontiguousarray(center)
        self.bhalf = np.ascontiguousarray(half)
        self.baxes = np.ascontiguousarray(axes)
        self.bkind = kinds
        self.cyl_a = np.ascontiguousarray(cyl_a)
        self.cyl_d = np.ascontiguousarray(cyl_d)
        self.cyl_r = np.ascontiguousarray(cyl_r)

        local_obb = np.asarray(local_obb, dtype=np.float64)
        lo = local_obb.min(axis=0)
        hi = local_obb.max(axis=0)
        self.lscale = float(scale[0])

        pts, start, glo, gcell = _grid_for(loop_vertices)
        self.gpts = pts
        self.gstart = start

        cdef int i
        for i in range(3):
            self.lcenter[i] = float((lo[i] + hi[i]) / 2.0 * scale[i])
            self.lhalf[i] = float((hi[i] - lo[i]) / 2.0 * abs(scale[i]))
            self.gmin[i] = float(glo[i])
            self.gcell[i] = float(gcell[i])
            self.ginv[i] = 1.0 / float(gcell[i])

    cdef bint _overlaps(self, Py_ssize_t k, double* c, double* R) noexcept nogil:
        # Ericson's OBB-OBB separating-axis test (Real-Time Collision
        # Detection 4.4.1). A = the loop pose (centre c, axes = the columns of
        # R), B = candidate k. True when they overlap; touching counts.
        cdef double Rm[3][3]
        cdef double AbsR[3][3]
        cdef double t[3]
        cdef double d[3]
        cdef double ae[3]
        cdef double be[3]
        cdef double ra, rb
        cdef int i, j

        for i in range(3):
            ae[i] = self.lhalf[i]
            be[i] = self.bhalf[k, i]
            d[i] = self.bcenter[k, i] - c[i]

        for i in range(3):
            for j in range(3):
                # A_i . B_j, with A_i = column i of R
                Rm[i][j] = (R[i] * self.baxes[k, j, 0] + R[3 + i] * self.baxes[k, j, 1]
                            + R[6 + i] * self.baxes[k, j, 2])
                AbsR[i][j] = fabs(Rm[i][j]) + _EPS

        for i in range(3):
            t[i] = d[0] * R[i] + d[1] * R[3 + i] + d[2] * R[6 + i]

        for i in range(3):
            ra = ae[i]
            rb = be[0] * AbsR[i][0] + be[1] * AbsR[i][1] + be[2] * AbsR[i][2]
            if fabs(t[i]) > ra + rb:
                return False

        for i in range(3):
            ra = ae[0] * AbsR[0][i] + ae[1] * AbsR[1][i] + ae[2] * AbsR[2][i]
            rb = be[i]
            if fabs(t[0] * Rm[0][i] + t[1] * Rm[1][i] + t[2] * Rm[2][i]) > ra + rb:
                return False

        ra = ae[1] * AbsR[2][0] + ae[2] * AbsR[1][0]
        rb = be[1] * AbsR[0][2] + be[2] * AbsR[0][1]
        if fabs(t[2] * Rm[1][0] - t[1] * Rm[2][0]) > ra + rb:
            return False

        ra = ae[1] * AbsR[2][1] + ae[2] * AbsR[1][1]
        rb = be[0] * AbsR[0][2] + be[2] * AbsR[0][0]
        if fabs(t[2] * Rm[1][1] - t[1] * Rm[2][1]) > ra + rb:
            return False

        ra = ae[1] * AbsR[2][2] + ae[2] * AbsR[1][2]
        rb = be[0] * AbsR[0][1] + be[1] * AbsR[0][0]
        if fabs(t[2] * Rm[1][2] - t[1] * Rm[2][2]) > ra + rb:
            return False

        ra = ae[0] * AbsR[2][0] + ae[2] * AbsR[0][0]
        rb = be[1] * AbsR[1][2] + be[2] * AbsR[1][1]
        if fabs(t[0] * Rm[2][0] - t[2] * Rm[0][0]) > ra + rb:
            return False

        ra = ae[0] * AbsR[2][1] + ae[2] * AbsR[0][1]
        rb = be[0] * AbsR[1][2] + be[2] * AbsR[1][0]
        if fabs(t[0] * Rm[2][1] - t[2] * Rm[0][1]) > ra + rb:
            return False

        ra = ae[0] * AbsR[2][2] + ae[2] * AbsR[0][2]
        rb = be[0] * AbsR[1][1] + be[1] * AbsR[1][0]
        if fabs(t[0] * Rm[2][2] - t[2] * Rm[0][2]) > ra + rb:
            return False

        ra = ae[0] * AbsR[1][0] + ae[1] * AbsR[0][0]
        rb = be[1] * AbsR[2][2] + be[2] * AbsR[2][1]
        if fabs(t[1] * Rm[0][0] - t[0] * Rm[1][0]) > ra + rb:
            return False

        ra = ae[0] * AbsR[1][1] + ae[1] * AbsR[0][1]
        rb = be[0] * AbsR[2][2] + be[2] * AbsR[2][0]
        if fabs(t[1] * Rm[0][1] - t[0] * Rm[1][1]) > ra + rb:
            return False

        ra = ae[0] * AbsR[1][2] + ae[1] * AbsR[0][2]
        rb = be[0] * AbsR[2][1] + be[1] * AbsR[2][0]
        if fabs(t[1] * Rm[0][2] - t[0] * Rm[1][2]) > ra + rb:
            return False

        return True

    cdef void _cell_range(self, double* lo, double* hi, int* ilo, int* ihi) noexcept nogil:
        # the grid cells a local-space box [lo, hi] touches, clamped to the grid
        cdef int i, a, b

        for i in range(3):
            a = <int>floor((lo[i] - self.gmin[i]) * self.ginv[i])
            b = <int>floor((hi[i] - self.gmin[i]) * self.ginv[i])

            if a < 0:
                a = 0

            if b > _GRID - 1:
                b = _GRID - 1

            ilo[i] = a
            ihi[i] = b

    cdef int _cyl_hit(self, double* a, double* d, double r, bint first_only) noexcept nogil:
        # how many loop-mesh vertices lie inside the cylinder with axis a + t*d,
        # t in [0, 1], radius r (all in the loop's own frame)? first_only stops
        # at 1 (a yes/no is enough)
        cdef double lo[3]
        cdef double hi[3]
        cdef double p0[3]
        cdef double sd[3]
        cdef double clo[3]
        cdef double chi[3]
        cdef double t0, t1, ta, tb, dd, r2, tt, w0, w1, w2, p, q, s
        cdef int ilo[3]
        cdef int ihi[3]
        cdef int i, ix, iy, iz, cell
        cdef Py_ssize_t m
        cdef int n = 0

        for i in range(3):
            lo[i] = self.gmin[i] - r
            hi[i] = self.gmin[i] + self.gcell[i] * _GRID + r

        # only the part of the axis near the loop matters (a wire can be metres long)
        if not _clip(a, d, lo, hi, &t0, &t1):
            return 0

        for i in range(3):
            p0[i] = a[i] + t0 * d[i]
            sd[i] = (t1 - t0) * d[i]

            if sd[i] >= 0.0:
                lo[i] = p0[i] - r
                hi[i] = p0[i] + sd[i] + r
            else:
                lo[i] = p0[i] + sd[i] - r
                hi[i] = p0[i] + r

        self._cell_range(lo, hi, ilo, ihi)

        dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
        r2 = r * r

        for ix in range(ilo[0], ihi[0] + 1):
            for iy in range(ilo[1], ihi[1] + 1):
                for iz in range(ilo[2], ihi[2] + 1):
                    clo[0] = self.gmin[0] + ix * self.gcell[0] - r
                    clo[1] = self.gmin[1] + iy * self.gcell[1] - r
                    clo[2] = self.gmin[2] + iz * self.gcell[2] - r
                    chi[0] = clo[0] + self.gcell[0] + 2.0 * r
                    chi[1] = clo[1] + self.gcell[1] + 2.0 * r
                    chi[2] = clo[2] + self.gcell[2] + 2.0 * r

                    if not _clip(p0, sd, clo, chi, &ta, &tb):
                        continue

                    cell = (ix * _GRID + iy) * _GRID + iz
                    for m in range(self.gstart[cell], self.gstart[cell + 1]):
                        w0 = self.gpts[m, 0] - a[0]
                        w1 = self.gpts[m, 1] - a[1]
                        w2 = self.gpts[m, 2] - a[2]

                        tt = (w0 * d[0] + w1 * d[1] + w2 * d[2]) / dd
                        if tt < 0.0 or tt > 1.0:
                            continue

                        p = w0 - tt * d[0]
                        q = w1 - tt * d[1]
                        s = w2 - tt * d[2]
                        if p * p + q * q + s * s <= r2:
                            n += 1
                            if first_only:
                                return 1

        return n

    cdef int _box_hit(self, double* c, double* ax, double* h, bint first_only) noexcept nogil:
        # how many loop-mesh vertices lie inside the oriented box centre c, axes
        # ax[3 * j + i] (component i of axis j), half extents h (loop frame)?
        cdef double lo[3]
        cdef double hi[3]
        cdef double ext, w0, w1, w2
        cdef int ilo[3]
        cdef int ihi[3]
        cdef int i, ix, iy, iz, cell
        cdef Py_ssize_t m
        cdef int n = 0

        for i in range(3):
            ext = fabs(ax[i]) * h[0] + fabs(ax[3 + i]) * h[1] + fabs(ax[6 + i]) * h[2]
            lo[i] = c[i] - ext
            hi[i] = c[i] + ext

            if hi[i] < self.gmin[i] or lo[i] > self.gmin[i] + self.gcell[i] * _GRID:
                return 0

        self._cell_range(lo, hi, ilo, ihi)

        for ix in range(ilo[0], ihi[0] + 1):
            for iy in range(ilo[1], ihi[1] + 1):
                for iz in range(ilo[2], ihi[2] + 1):
                    cell = (ix * _GRID + iy) * _GRID + iz
                    for m in range(self.gstart[cell], self.gstart[cell + 1]):
                        w0 = self.gpts[m, 0] - c[0]
                        w1 = self.gpts[m, 1] - c[1]
                        w2 = self.gpts[m, 2] - c[2]

                        if fabs(w0 * ax[0] + w1 * ax[1] + w2 * ax[2]) > h[0]:
                            continue

                        if fabs(w0 * ax[3] + w1 * ax[4] + w2 * ax[5]) > h[1]:
                            continue

                        if fabs(w0 * ax[6] + w1 * ax[7] + w2 * ax[8]) <= h[2]:
                            n += 1
                            if first_only:
                                return 1

        return n

    cdef int _mesh_hit(self, Py_ssize_t k, double* pos, double* R, bint first_only) noexcept nogil:
        # stage two for candidate k: does the loop's MESH (start point pos,
        # rotation R) touch its real shape? Candidate moved into the loop's frame.
        cdef double inv = 1.0 / self.lscale
        cdef double y[3]
        cdef double a[3]
        cdef double d[3]
        cdef double ax[9]
        cdef double h[3]
        cdef int i, j, m

        if self.bkind[k] == _CYLINDER:
            for i in range(3):
                y[i] = self.cyl_a[k, i] - pos[i]

            for j in range(3):
                a[j] = (R[j] * y[0] + R[3 + j] * y[1] + R[6 + j] * y[2]) * inv
                d[j] = (R[j] * self.cyl_d[k, 0] + R[3 + j] * self.cyl_d[k, 1]
                        + R[6 + j] * self.cyl_d[k, 2]) * inv

            return self._cyl_hit(a, d, self.cyl_r[k] * inv, first_only)

        for i in range(3):
            y[i] = self.bcenter[k, i] - pos[i]

        for j in range(3):
            a[j] = (R[j] * y[0] + R[3 + j] * y[1] + R[6 + j] * y[2]) * inv
            h[j] = self.bhalf[k, j] * inv

            for m in range(3):
                ax[3 * m + j] = (R[j] * self.baxes[k, m, 0] + R[3 + j] * self.baxes[k, m, 1]
                                 + R[6 + j] * self.baxes[k, m, 2])

        return self._box_hit(a, ax, h, first_only)

    cdef bint _clear(self, double* pos, double* R) noexcept nogil:
        # the loop at start point pos, rotated by R, against every candidate:
        # an axis-aligned reject, then the box test, and only for the boxes
        # that overlap, the mesh test
        cdef double c[3]
        cdef double ext[3]
        cdef Py_ssize_t k
        cdef int i

        for i in range(3):
            c[i] = (pos[i] + R[3 * i] * self.lcenter[0] + R[3 * i + 1] * self.lcenter[1]
                    + R[3 * i + 2] * self.lcenter[2])
            ext[i] = (fabs(R[3 * i]) * self.lhalf[0] + fabs(R[3 * i + 1]) * self.lhalf[1]
                      + fabs(R[3 * i + 2]) * self.lhalf[2])

        for k in range(self.n):
            if (self.bmin[k, 0] > c[0] + ext[0] or self.bmax[k, 0] < c[0] - ext[0]
                    or self.bmin[k, 1] > c[1] + ext[1] or self.bmax[k, 1] < c[1] - ext[1]
                    or self.bmin[k, 2] > c[2] + ext[2] or self.bmax[k, 2] < c[2] - ext[2]):
                continue

            if self._overlaps(k, c, R) and self._mesh_hit(k, pos, R, True) > 0:
                return False

        return True

    cdef long _contact(self, double* pos, double* R) noexcept nogil:
        # how much of the loop's mesh is inside the candidates it overlaps: the
        # number of its vertices that are (0 = clear)
        cdef double c[3]
        cdef long n = 0
        cdef Py_ssize_t k
        cdef int i

        for i in range(3):
            c[i] = (pos[i] + R[3 * i] * self.lcenter[0] + R[3 * i + 1] * self.lcenter[1]
                    + R[3 * i + 2] * self.lcenter[2])

        for k in range(self.n):
            if self._overlaps(k, c, R):
                n += self._mesh_hit(k, pos, R, False)

        return n

    cdef bint _pose_clear(self, double* p1, double* p2, double* P, double* a, double* q0,
                          double t, double theta, double* q_out, double* p1_out,
                          double* p2_out) noexcept nogil:
        cdef double R[9]

        _compose(p1, p2, P, a, q0, t, theta, q_out, p1_out, p2_out)
        _quat_to_matrix(q_out, R)

        return self._clear(p1_out, R)

    cdef long _pose_contact(self, double* p1, double* p2, double* P, double* a, double* q0,
                            double t, double theta) noexcept nogil:
        cdef double R[9]
        cdef double q[4]
        cdef double o1[3]
        cdef double o2[3]

        _compose(p1, p2, P, a, q0, t, theta, q, o1, o2)
        _quat_to_matrix(q, R)

        return self._contact(o1, R)

    cdef bint _roll_scan(self, double* p1, double* p2, double* P, double* a, double* q0,
                         double t, double step, double* q_out, double* p1_out,
                         double* p2_out, double* theta_out) noexcept nogil:
        # the NEAREST clear roll at slide offset t: the current angle, then +k
        # and -k steps outward, first clear wins. Both sides clear at the same
        # distance: the side with less contact at the first step (equal: +).
        cdef int nmax = <int>floor(_PI / step + 1e-9)
        cdef int k
        cdef bint plus_ok, minus_ok, take_minus
        cdef double qp[4]
        cdef double p1p[3]
        cdef double p2p[3]
        cdef double qm[4]
        cdef double p1m[3]
        cdef double p2m[3]
        cdef int i

        if self._pose_clear(p1, p2, P, a, q0, t, 0.0, q_out, p1_out, p2_out):
            theta_out[0] = 0.0
            return True

        for k in range(1, nmax + 1):
            plus_ok = self._pose_clear(p1, p2, P, a, q0, t, k * step, qp, p1p, p2p)
            minus_ok = self._pose_clear(p1, p2, P, a, q0, t, -k * step, qm, p1m, p2m)

            if not plus_ok and not minus_ok:
                continue

            take_minus = minus_ok and not plus_ok
            if plus_ok and minus_ok:
                take_minus = (self._pose_contact(p1, p2, P, a, q0, t, -step)
                              < self._pose_contact(p1, p2, P, a, q0, t, step))

            if take_minus:
                for i in range(4):
                    q_out[i] = qm[i]

                for i in range(3):
                    p1_out[i] = p1m[i]
                    p2_out[i] = p2m[i]

                theta_out[0] = -k * step
            else:
                for i in range(4):
                    q_out[i] = qp[i]

                for i in range(3):
                    p1_out[i] = p1p[i]
                    p2_out[i] = p2p[i]

                theta_out[0] = k * step

            return True

        return False

    def pose_at(self, p1, p2, pivot, axis, q0, double t, double theta_deg):
        """``(q, start, stop)`` after rolling by *theta_deg* about *axis*
        through *pivot*, having slid *t* along it (see the module docstring)."""
        cdef double c_p1[3]
        cdef double c_p2[3]
        cdef double c_P[3]
        cdef double c_a[3]
        cdef double c_q0[4]
        cdef double q[4]
        cdef double o1[3]
        cdef double o2[3]
        cdef double norm
        cdef int i

        for i in range(3):
            c_p1[i] = p1[i]
            c_p2[i] = p2[i]
            c_P[i] = pivot[i]
            c_a[i] = axis[i]

        for i in range(4):
            c_q0[i] = q0[i]

        norm = (c_a[0] * c_a[0] + c_a[1] * c_a[1] + c_a[2] * c_a[2]) ** 0.5
        for i in range(3):
            c_a[i] /= norm

        _compose(c_p1, c_p2, c_P, c_a, c_q0, t, theta_deg * _PI / 180.0, q, o1, o2)

        return ((q[0], q[1], q[2], q[3]), (o1[0], o1[1], o1[2]), (o2[0], o2[1], o2[2]))

    def is_clear(self, position, double w, double x, double y, double z):
        """Whether the loop with its start point at *position* and rotation
        ``[w, x, y, z]`` touches nothing."""
        cdef double pos[3]
        cdef double R[9]
        cdef double q[4]
        cdef int i

        for i in range(3):
            pos[i] = position[i]

        q[0] = w
        q[1] = x
        q[2] = y
        q[3] = z
        _quat_to_matrix(q, R)

        return self._clear(pos, R)

    def contact(self, position, double w, double x, double y, double z):
        """How many of the loop's mesh vertices are inside the candidates at
        this pose (0 = clear)."""
        cdef double pos[3]
        cdef double R[9]
        cdef double q[4]
        cdef int i

        for i in range(3):
            pos[i] = position[i]

        q[0] = w
        q[1] = x
        q[2] = y
        q[3] = z
        _quat_to_matrix(q, R)

        return self._contact(pos, R)

    def boxes_overlap(self, position, double w, double x, double y, double z):
        """Indices of the candidates whose BOX overlaps the loop's box at this
        pose (stage one only: the hit list ``is_clear`` goes on to refine)."""
        cdef double pos[3]
        cdef double R[9]
        cdef double q[4]
        cdef double c[3]
        cdef Py_ssize_t k
        cdef int i
        hits = []

        for i in range(3):
            pos[i] = position[i]

        q[0] = w
        q[1] = x
        q[2] = y
        q[3] = z
        _quat_to_matrix(q, R)

        for i in range(3):
            c[i] = (pos[i] + R[3 * i] * self.lcenter[0] + R[3 * i + 1] * self.lcenter[1]
                    + R[3 * i + 2] * self.lcenter[2])

        for k in range(self.n):
            if self._overlaps(k, c, R):
                hits.append(k)

        return hits

    def search(self, p1, p2, pivot, axis, q0, double t0, double pos_limit, double neg_limit,
               double slide_step, double roll_deg, double slide_roll_deg):
        """The nearest clear pose, as ``(t, theta_deg, (w, x, y, z), start, stop)``
        (the object's new angle and the new start and stop points), or ``None``.

        *p1* / *p2* are the loop's current start and stop points, *q0* its
        current angle, *axis* the direction of the wire and *pivot* the point
        on it the roll turns about. Tries the roll that is clear nearest the
        current angle at slide offset *t0* (steps of *roll_deg*); failing
        that, slides away from *t0* in both directions in *slide_step*
        increments, never past *pos_limit* / *neg_limit* (their offsets along
        *axis*), scanning the full turn at *slide_roll_deg* at each, and keeps
        the clear spot closest to *t0* (the positive side wins a tie).
        """
        cdef double c_p1[3]
        cdef double c_p2[3]
        cdef double c_P[3]
        cdef double c_a[3]
        cdef double c_q0[4]
        cdef double q[4]
        cdef double o1[3]
        cdef double o2[3]
        cdef double b_q[4]
        cdef double b_1[3]
        cdef double b_2[3]
        cdef double theta
        cdef double b_theta = 0.0
        cdef double best_t = 0.0
        cdef double best_d = 0.0
        cdef double t, t_next, limit, sign, dist, norm
        cdef double roll = roll_deg * _PI / 180.0
        cdef double slide_roll = slide_roll_deg * _PI / 180.0
        cdef bint have = False
        cdef int direction, i

        for i in range(3):
            c_p1[i] = p1[i]
            c_p2[i] = p2[i]
            c_P[i] = pivot[i]
            c_a[i] = axis[i]

        for i in range(4):
            c_q0[i] = q0[i]

        norm = (c_a[0] * c_a[0] + c_a[1] * c_a[1] + c_a[2] * c_a[2]) ** 0.5
        for i in range(3):
            c_a[i] /= norm

        if self._roll_scan(c_p1, c_p2, c_P, c_a, c_q0, t0, roll, q, o1, o2, &theta):
            return (t0, theta * 180.0 / _PI, (q[0], q[1], q[2], q[3]),
                    (o1[0], o1[1], o1[2]), (o2[0], o2[1], o2[2]))

        for direction in range(2):
            if direction == 0:
                limit = pos_limit
                sign = 1.0
            else:
                limit = neg_limit
                sign = -1.0

            t = t0
            while True:
                t_next = t + sign * slide_step

                if sign > 0.0:
                    if t_next > limit:
                        t_next = limit
                elif t_next < limit:
                    t_next = limit

                if t_next == t:
                    # already at the limit, and that spot was tested last time
                    break

                t = t_next

                if self._roll_scan(c_p1, c_p2, c_P, c_a, c_q0, t, slide_roll, q, o1, o2, &theta):
                    dist = fabs(t - t0)
                    if not have or dist < best_d:
                        have = True
                        best_d = dist
                        best_t = t
                        b_theta = theta
                        for i in range(4):
                            b_q[i] = q[i]

                        for i in range(3):
                            b_1[i] = o1[i]
                            b_2[i] = o2[i]

                    break

        if not have:
            return None

        return (best_t, b_theta * 180.0 / _PI, (b_q[0], b_q[1], b_q[2], b_q[3]),
                (b_1[0], b_1[1], b_1[2]), (b_2[0], b_2[1], b_2[2]))
