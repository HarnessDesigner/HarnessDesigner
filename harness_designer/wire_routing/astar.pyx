# astar.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The search loop behind ``wire_routing.routing`` -- 4-directional A* over a
compressed grid, in C.

Everything here is integer math: ``routing`` scales every grid coordinate
by ``1_000_000`` (they are already rounded to 6 decimals, so that lands on
exact integers -- no epsilons, no drift) and every cost is an integer in the
same units.

Search state is ``(node, direction of arrival)``, encoded as
``sid = node * 3 + direction`` with direction ``0`` = horizontal step,
``1`` = vertical step, ``2`` = the start (no step taken yet), where
``node = i * nz + j`` for grid column ``i`` / row ``j``.

A path also carries its own straight runs so far, so a route can't turn and
run too close and parallel to an earlier stretch of itself. Those live in an
arena as immutable, singly linked nodes ``(lane, lo, hi, parent)`` -- one
list for horizontal runs, one for vertical -- and a search state just holds
the index of the newest node of each. Extending the run a step continues
makes a fresh node that shares the older ones as its tail, so there is never
a list to copy.

Everything that does not depend on the path taken to reach a step -- the
destination is inside an obstacle, the edge cuts through one, the edge runs
too close to another wire -- is decided for the whole grid beforehand by
``routing._build_tables`` and arrives here as four flat ``left`` / ``right``
/ ``down`` / ``up`` allowed-step tables.
"""

import numpy as np
from libc.stdint cimport int32_t, int64_t
from libc.stdlib cimport malloc, calloc, realloc, free


ctypedef const unsigned char* Table

cdef int64_t _INF = 0x3FFFFFFFFFFFFFFF


cdef struct Item:
    int64_t pri
    int64_t cost
    int32_t sid
    int32_t oh
    int32_t ov


cdef struct Heap:
    Item* data
    Py_ssize_t n
    Py_ssize_t cap


cdef struct Runs:
    int64_t* lane
    int64_t* lo
    int64_t* hi
    int32_t* parent
    Py_ssize_t n
    Py_ssize_t cap


cdef inline bint _less(Item* a, Item* b) noexcept nogil:
    # Cheapest priority first; among equal priorities prefer the state that
    # has already travelled FARTHEST (highest cost so far, i.e. nearest the
    # goal) -- on a grid with many equally good routes, preferring the
    # shallowest one makes the search explore every one of them before
    # finishing any. Then sid, so the order is fully deterministic.
    if a.pri != b.pri:
        return a.pri < b.pri
    if a.cost != b.cost:
        return a.cost > b.cost
    return a.sid < b.sid


cdef int _heap_push(Heap* h, Item item) noexcept nogil:
    cdef Py_ssize_t i, parent
    cdef Item* data

    if h.n == h.cap:
        h.cap = h.cap * 2
        data = <Item*>realloc(h.data, h.cap * sizeof(Item))
        if data == NULL:
            return -1
        h.data = data

    data = h.data
    i = h.n
    h.n += 1

    while i > 0:
        parent = (i - 1) >> 1
        if not _less(&item, &data[parent]):
            break
        data[i] = data[parent]
        i = parent

    data[i] = item
    return 0


cdef Item _heap_pop(Heap* h) noexcept nogil:
    cdef Item* data = h.data
    cdef Item top = data[0]
    cdef Item last
    cdef Py_ssize_t i, child, n

    h.n -= 1
    n = h.n

    if n > 0:
        last = data[n]
        i = 0

        while True:
            child = 2 * i + 1
            if child >= n:
                break
            if child + 1 < n and _less(&data[child + 1], &data[child]):
                child += 1
            if not _less(&data[child], &last):
                break
            data[i] = data[child]
            i = child

        data[i] = last

    return top


cdef int32_t _run_new(Runs* r, int64_t lane, int64_t lo, int64_t hi, int32_t parent) noexcept nogil:
    cdef int64_t* p64
    cdef int32_t* p32
    cdef Py_ssize_t cap

    if r.n == r.cap:
        cap = r.cap * 2

        p64 = <int64_t*>realloc(r.lane, cap * sizeof(int64_t))
        if p64 == NULL:
            return -2
        r.lane = p64

        p64 = <int64_t*>realloc(r.lo, cap * sizeof(int64_t))
        if p64 == NULL:
            return -2
        r.lo = p64

        p64 = <int64_t*>realloc(r.hi, cap * sizeof(int64_t))
        if p64 == NULL:
            return -2
        r.hi = p64

        p32 = <int32_t*>realloc(r.parent, cap * sizeof(int32_t))
        if p32 == NULL:
            return -2
        r.parent = p32

        r.cap = cap

    r.lane[r.n] = lane
    r.lo[r.n] = lo
    r.hi[r.n] = hi
    r.parent[r.n] = parent
    r.n += 1
    return <int32_t>(r.n - 1)


cdef inline Py_ssize_t _bisect_left(const int64_t* a, Py_ssize_t n, int64_t v) noexcept nogil:
    # First index whose value is >= v.
    cdef Py_ssize_t lo = 0
    cdef Py_ssize_t hi = n
    cdef Py_ssize_t mid

    while lo < hi:
        mid = (lo + hi) >> 1
        if a[mid] < v:
            lo = mid + 1
        else:
            hi = mid

    return lo


cdef inline Py_ssize_t _bisect_right(const int64_t* a, Py_ssize_t n, int64_t v) noexcept nogil:
    # First index whose value is > v.
    cdef Py_ssize_t lo = 0
    cdef Py_ssize_t hi = n
    cdef Py_ssize_t mid

    while lo < hi:
        mid = (lo + hi) >> 1
        if a[mid] <= v:
            lo = mid + 1
        else:
            hi = mid

    return lo


cdef inline void _fill(unsigned char[::1] table, Py_ssize_t stride, Py_ssize_t i0, Py_ssize_t i1,
                       Py_ssize_t j0, Py_ssize_t j1) noexcept nogil:
    # table[i * stride + j] = 1 for i in [i0, i1), j in [j0, j1)
    cdef Py_ssize_t i, j

    for i in range(i0, i1):
        for j in range(j0, j1):
            table[i * stride + j] = 1


def build_tables(const int64_t[::1] xs, const int64_t[::1] zs,
                 const int64_t[:, ::1] rects, const int64_t[:, ::1] h_lanes,
                 const int64_t[:, ::1] v_lanes, int64_t limit):
    """For every node of the grid, whether the step to its left / right /
    down / up neighbour is allowed -- ``(ok_left, ok_right, ok_down, ok_up)``,
    each a flat ``uint8`` array indexed ``i * len(zs) + j`` (a step off the
    edge of the grid is ``0``).

    A step is allowed when its destination isn't strictly inside an obstacle
    rect, the edge doesn't cut through one, and the edge doesn't run within
    *limit* of, and over a real stretch of, another wire's run. Every
    obstacle and every run is a contiguous block of the grid, so each is
    found with a binary search and filled directly -- the same tests, on the
    same scaled-integer coordinates, that the numpy version does with an
    outer product per obstacle.

    :param rects: ``(R, 4)`` -- ``min_x, min_z, max_x, max_z``, scaled.
    :param h_lanes: ``(H, 3)`` -- ``z, lo, hi`` of each horizontal run, scaled.
    :param v_lanes: ``(V, 3)`` -- ``x, lo, hi`` of each vertical run, scaled.
    :param limit: Scaled lane spacing, less its tolerance.
    """
    cdef Py_ssize_t nx = xs.shape[0]
    cdef Py_ssize_t nz = zs.shape[0]
    cdef Py_ssize_t r, k, i, j
    cdef Py_ssize_t ix0, ix1, jz0, jz1, ia, ib, ja, jb
    cdef int64_t min_x, min_z, max_x, max_z, pos, lo, hi
    cdef const int64_t* px = &xs[0]
    cdef const int64_t* pz = &zs[0]

    node_bad_arr = np.zeros(nx * nz, dtype=np.uint8)
    h_bad_arr = np.zeros(nx * nz, dtype=np.uint8)     # edge (i, j) -> (i + 1, j), stride nz
    v_bad_arr = np.zeros(nx * nz, dtype=np.uint8)     # edge (i, j) -> (i, j + 1), stride nz
    cdef unsigned char[::1] node_bad = node_bad_arr
    cdef unsigned char[::1] h_bad = h_bad_arr
    cdef unsigned char[::1] v_bad = v_bad_arr

    with nogil:
        for r in range(rects.shape[0]):
            min_x = rects[r, 0]
            min_z = rects[r, 1]
            max_x = rects[r, 2]
            max_z = rects[r, 3]

            # Grid columns / rows strictly inside the rect (1 unit = the
            # tolerance the float version calls _EPS).
            ix0 = _bisect_right(px, nx, min_x + 1)
            ix1 = _bisect_left(px, nx, max_x - 1)
            jz0 = _bisect_right(pz, nz, min_z + 1)
            jz1 = _bisect_left(pz, nz, max_z - 1)

            if ix0 < ix1 and jz0 < jz1:
                _fill(node_bad, nz, ix0, ix1, jz0, jz1)

            # Horizontal edges (i -> i + 1) whose span overlaps the rect's
            # x-range, on rows strictly inside its z-range.
            ia = _bisect_right(px, nx, min_x + 1) - 1
            if ia < 0:
                ia = 0
            ib = _bisect_left(px, nx, max_x - 1)
            if ib > nx - 1:
                ib = nx - 1
            if ia < ib and jz0 < jz1:
                _fill(h_bad, nz, ia, ib, jz0, jz1)

            # Vertical edges (j -> j + 1) whose span overlaps the rect's
            # z-range, on columns strictly inside its x-range.
            ja = _bisect_right(pz, nz, min_z + 1) - 1
            if ja < 0:
                ja = 0
            jb = _bisect_left(pz, nz, max_z - 1)
            if jb > nz - 1:
                jb = nz - 1
            if ix0 < ix1 and ja < jb:
                _fill(v_bad, nz, ix0, ix1, ja, jb)

        for k in range(h_lanes.shape[0]):
            pos = h_lanes[k, 0]
            lo = h_lanes[k, 1]
            hi = h_lanes[k, 2]

            jz0 = _bisect_right(pz, nz, pos - limit)
            jz1 = _bisect_left(pz, nz, pos + limit)
            ia = _bisect_right(px, nx, lo + 1) - 1
            if ia < 0:
                ia = 0
            ib = _bisect_left(px, nx, hi - 1)
            if ib > nx - 1:
                ib = nx - 1

            if ia < ib and jz0 < jz1:
                _fill(h_bad, nz, ia, ib, jz0, jz1)

        for k in range(v_lanes.shape[0]):
            pos = v_lanes[k, 0]
            lo = v_lanes[k, 1]
            hi = v_lanes[k, 2]

            ix0 = _bisect_right(px, nx, pos - limit)
            ix1 = _bisect_left(px, nx, pos + limit)
            ja = _bisect_right(pz, nz, lo + 1) - 1
            if ja < 0:
                ja = 0
            jb = _bisect_left(pz, nz, hi - 1)
            if jb > nz - 1:
                jb = nz - 1

            if ix0 < ix1 and ja < jb:
                _fill(v_bad, nz, ix0, ix1, ja, jb)

    ok_left_arr = np.zeros(nx * nz, dtype=np.uint8)
    ok_right_arr = np.zeros(nx * nz, dtype=np.uint8)
    ok_down_arr = np.zeros(nx * nz, dtype=np.uint8)
    ok_up_arr = np.zeros(nx * nz, dtype=np.uint8)
    cdef unsigned char[::1] ok_left = ok_left_arr
    cdef unsigned char[::1] ok_right = ok_right_arr
    cdef unsigned char[::1] ok_down = ok_down_arr
    cdef unsigned char[::1] ok_up = ok_up_arr
    cdef Py_ssize_t node

    with nogil:
        for i in range(nx):
            for j in range(nz):
                node = i * nz + j

                if i < nx - 1:
                    ok_right[node] = (not h_bad[node]) and (not node_bad[node + nz])
                if i > 0:
                    ok_left[node] = (not h_bad[node - nz]) and (not node_bad[node - nz])
                if j < nz - 1:
                    ok_up[node] = (not v_bad[node]) and (not node_bad[node + 1])
                if j > 0:
                    ok_down[node] = (not v_bad[node - 1]) and (not node_bad[node - 1])

    return ok_left_arr, ok_right_arr, ok_down_arr, ok_up_arr


def astar(const int64_t[::1] xs, const int64_t[::1] zs,
          int si, int sj, int gi, int gj,
          const unsigned char[::1] ok_left, const unsigned char[::1] ok_right,
          const unsigned char[::1] ok_down, const unsigned char[::1] ok_up,
          int64_t limit, int64_t bend_cost, int forbid_start, int forbid_goal):
    """Search from grid node ``(si, sj)`` to ``(gi, gj)``.

    :param xs: Column coordinates, scaled to integers, ascending.
    :param zs: Row coordinates, scaled to integers, ascending.
    :param ok_left: Flat ``i * len(zs) + j`` table -- may the step from that
        node to its ``i - 1`` neighbour be taken (same for the other three).
    :param limit: How close (scaled) a run may come to another parallel run
        of the same path -- the lane spacing, less its tolerance.
    :param bend_cost: Scaled extra cost of every bend.
    :param forbid_start: Step the very first move may not take (``0`` left,
        ``1`` right, ``2`` down, ``3`` up), or ``-1``.
    :param forbid_goal: Step the last move into the goal may not take, or ``-1``.

    :returns: The node indices ``i * len(zs) + j`` of the cheapest path,
        start to goal inclusive, as an ``int32`` array -- or ``None`` if the
        goal can't be reached.
    """
    cdef Py_ssize_t nx = xs.shape[0]
    cdef Py_ssize_t nz = zs.shape[0]
    cdef Py_ssize_t n_states = nx * nz * 3
    cdef int32_t goal_node = <int32_t>(gi * nz + gj)
    cdef int64_t gx = xs[gi]
    cdef int64_t gz = zs[gj]

    cdef int64_t* best = <int64_t*>malloc(n_states * sizeof(int64_t))
    cdef int32_t* came = <int32_t*>malloc(n_states * sizeof(int32_t))

    cdef Heap heap
    cdef Runs runs
    cdef Table[4] oks
    cdef int[4] mv_di
    cdef int[4] mv_dj
    cdef int[4] mv_nd
    cdef int[4] mv_off

    cdef Item it, nit
    cdef Py_ssize_t k, i, j, ni, nj, node, d, mv, nd, pos
    cdef int32_t sid, nsid, goal_sid, oh, ov, new_oh, new_ov, run, base
    cdef int64_t x1, z1, x2, z2, lo, hi, lane, lane_lo, lane_hi, cost, new_cost
    cdef bint blocked
    cdef int status = 0

    if best == NULL or came == NULL:
        free(best)
        free(came)
        raise MemoryError()

    heap.cap = 1024
    heap.n = 0
    heap.data = <Item*>malloc(heap.cap * sizeof(Item))

    runs.cap = 1024
    runs.n = 0
    runs.lane = <int64_t*>malloc(runs.cap * sizeof(int64_t))
    runs.lo = <int64_t*>malloc(runs.cap * sizeof(int64_t))
    runs.hi = <int64_t*>malloc(runs.cap * sizeof(int64_t))
    runs.parent = <int32_t*>malloc(runs.cap * sizeof(int32_t))

    if heap.data == NULL or runs.lane == NULL or runs.lo == NULL or runs.hi == NULL or runs.parent == NULL:
        free(best)
        free(came)
        free(heap.data)
        free(runs.lane)
        free(runs.lo)
        free(runs.hi)
        free(runs.parent)
        raise MemoryError()

    # Neighbour order is part of the search's tie-breaking -- keep it fixed:
    # left, right, down, up.
    oks[0] = &ok_left[0]
    oks[1] = &ok_right[0]
    oks[2] = &ok_down[0]
    oks[3] = &ok_up[0]

    mv_di[0] = -1; mv_dj[0] = 0; mv_nd[0] = 0; mv_off[0] = -<int>nz
    mv_di[1] = 1; mv_dj[1] = 0; mv_nd[1] = 0; mv_off[1] = <int>nz
    mv_di[2] = 0; mv_dj[2] = -1; mv_nd[2] = 1; mv_off[2] = -1
    mv_di[3] = 0; mv_dj[3] = 1; mv_nd[3] = 1; mv_off[3] = 1

    goal_sid = -1

    with nogil:
        for k in range(n_states):
            best[k] = _INF
            came[k] = -1

        sid = <int32_t>((si * nz + sj) * 3 + 2)
        best[sid] = 0

        it.pri = 0
        it.cost = 0
        it.sid = sid
        it.oh = -1
        it.ov = -1
        _heap_push(&heap, it)

        while heap.n > 0:
            it = _heap_pop(&heap)
            sid = it.sid

            if it.cost > best[sid]:
                # Stale entry -- a cheaper path to this state was found after
                # this one was pushed.
                continue

            node = sid // 3
            d = sid - node * 3

            if node == goal_node:
                goal_sid = sid
                break

            i = node // nz
            j = node - i * nz
            x1 = xs[i]
            z1 = zs[j]
            cost = it.cost
            oh = it.oh
            ov = it.ov

            for mv in range(4):
                if not oks[mv][node]:
                    continue

                ni = i + mv_di[mv]
                nj = j + mv_dj[mv]
                nd = mv_nd[mv]

                if nd == 0:
                    x2 = xs[ni]
                    if x1 < x2:
                        lo = x1
                        hi = x2
                    else:
                        lo = x2
                        hi = x1
                    lane = z1
                    run = oh
                else:
                    z2 = zs[nj]
                    if z1 < z2:
                        lo = z1
                        hi = z2
                    else:
                        lo = z2
                        hi = z1
                    lane = x1
                    run = ov

                # This path's own earlier runs, same lane rule.
                blocked = False
                lane_lo = lane - limit
                lane_hi = lane + limit
                while run != -1:
                    if (lane_lo < runs.lane[run] < lane_hi
                            and runs.hi[run] > lo and runs.lo[run] < hi):
                        blocked = True
                        break
                    run = runs.parent[run]

                if blocked:
                    continue

                if d == 2 and mv == forbid_start:
                    continue
                if ni == gi and nj == gj and mv == forbid_goal:
                    continue

                new_cost = cost + (hi - lo)
                if d != 2 and nd != d:
                    new_cost += bend_cost

                nsid = <int32_t>((node + mv_off[mv]) * 3 + nd)
                if new_cost >= best[nsid]:
                    continue

                best[nsid] = new_cost
                came[nsid] = sid

                # A step that carries on the way the path was already
                # heading just lengthens its last run (sharing its tail).
                new_oh = oh
                new_ov = ov

                if nd == 0:
                    if d == 0:
                        base = runs.parent[oh]
                        if runs.lo[oh] < lo:
                            lo = runs.lo[oh]
                        if runs.hi[oh] > hi:
                            hi = runs.hi[oh]
                    else:
                        base = oh
                    new_oh = _run_new(&runs, lane, lo, hi, base)
                    if new_oh == -2:
                        status = -1
                        break
                else:
                    if d == 1:
                        base = runs.parent[ov]
                        if runs.lo[ov] < lo:
                            lo = runs.lo[ov]
                        if runs.hi[ov] > hi:
                            hi = runs.hi[ov]
                    else:
                        base = ov
                    new_ov = _run_new(&runs, lane, lo, hi, base)
                    if new_ov == -2:
                        status = -1
                        break

                x2 = xs[ni]
                z2 = zs[nj]
                nit.cost = new_cost
                nit.pri = new_cost + (x2 - gx if x2 > gx else gx - x2) + (z2 - gz if z2 > gz else gz - z2)
                nit.sid = nsid
                nit.oh = new_oh
                nit.ov = new_ov

                if _heap_push(&heap, nit) != 0:
                    status = -1
                    break

            if status != 0:
                break

    free(heap.data)
    free(runs.lane)
    free(runs.lo)
    free(runs.hi)
    free(runs.parent)

    if status != 0:
        free(best)
        free(came)
        raise MemoryError()

    if goal_sid == -1:
        free(best)
        free(came)
        return None

    # Walk the came-from chain back from the goal.
    cdef Py_ssize_t length = 1
    sid = goal_sid
    while came[sid] != -1:
        sid = came[sid]
        length += 1

    path = np.empty(length, dtype=np.int32)
    cdef int32_t[::1] out = path

    pos = length - 1
    sid = goal_sid
    out[pos] = sid // 3
    while came[sid] != -1:
        sid = came[sid]
        pos -= 1
        out[pos] = sid // 3

    free(best)
    free(came)
    return path


# What a search remembers about one (node, arrival direction) state -- packed
# so touching a state is one cache line, not one miss in each of three arrays.
cdef struct State:
    int64_t best
    int32_t came
    int32_t stamp


# What is in the way at one grid node: the five availability counts, packed for
# the same reason (a move looks at up to two neighbouring cells, never five arrays).
cdef struct Cell:
    short node_bad
    short h_obst
    short v_obst
    short h_lane
    short v_lane
    short h_pack
    short v_pack


cdef enum:
    # A Cell is this many shorts wide (_bump steps through one field of a table of them).
    CELL_SHORTS = 7

    # Packing: a run counts as "packed" against a sibling's run when it lies one
    # lane spacing away from it. The window is the lane rule's own limit up to
    # this much beyond it (scaled units: 3 micrometres), so a lattice line a few
    # micrometres off the exact spacing still counts.
    PACK_SLACK = 3000


cdef inline void _bump(short* table, Py_ssize_t stride, Py_ssize_t i0, Py_ssize_t i1,
                       Py_ssize_t j0, Py_ssize_t j1, int delta) noexcept nogil:
    # cell field += delta for i in [i0, i1), j in [j0, j1); `table` points at one
    # field of the first Cell, and a Cell is CELL_SHORTS shorts wide.
    cdef Py_ssize_t i, j

    for i in range(i0, i1):
        for j in range(j0, j1):
            table[(i * stride + j) * CELL_SHORTS] += delta


cdef class Router:
    """One drag frame's routing grid, shared by every wire routed in it.

    ``routing.route`` used to build a grid, decide which steps of it are
    allowed, and allocate the search's working arrays, from scratch, for
    every wire. Here all of that is built once: the grid lines
    (``xs``/``zs``), how many obstacles / other wires' runs make each step
    unavailable, and the search buffers. Painting a housing or a wire's
    runs into the grid, or taking them back out, is a handful of range
    additions, so routing wire after wire only has to add the runs of the
    wire that just settled (and remove the stubs it had reserved).

    Availability is kept as COUNTS, not flags, precisely so that painting
    is reversible: ``node_bad`` / ``h_obst`` / ``v_obst`` count the
    obstacles covering a node / a horizontal edge / a vertical edge and
    ``h_lane`` / ``v_lane`` count the other wires' runs -- a step is open
    when its counts are zero. Edge ``(i, j)`` means ``(i, j)`` to
    ``(i + 1, j)`` for the horizontal tables and ``(i, j)`` to
    ``(i, j + 1)`` for the vertical ones, all indexed ``i * nz + j``.

    Coordinates are ``int64``, scaled by 10 ** 6 like the rest of this
    module.
    """
    cdef Py_ssize_t nx, nz
    cdef object xs_arr
    cdef object zs_arr
    cdef const int64_t* px
    cdef const int64_t* pz
    cdef Cell* cells
    cdef State* states
    cdef int32_t gen
    cdef int64_t limit
    cdef public Py_ssize_t last_pops
    cdef Py_ssize_t pack_runs

    def __cinit__(self, xs, zs, int64_t limit):
        """
        :param xs: Grid columns, ascending, unique, scaled.
        :param zs: Grid rows, ascending, unique, scaled.
        :param limit: Lane spacing, less its tolerance, scaled -- how close a
            wire's run may come to another parallel run.
        """
        cdef const int64_t[::1] xv
        cdef const int64_t[::1] zv
        cdef Py_ssize_t n

        self.cells = NULL
        self.states = NULL
        self.gen = 0
        self.last_pops = 0
        self.pack_runs = 0

        self.xs_arr = np.ascontiguousarray(xs, dtype=np.int64)
        self.zs_arr = np.ascontiguousarray(zs, dtype=np.int64)
        xv = self.xs_arr
        zv = self.zs_arr
        self.px = &xv[0]
        self.pz = &zv[0]
        self.nx = xv.shape[0]
        self.nz = zv.shape[0]
        self.limit = limit

        n = self.nx * self.nz
        self.cells = <Cell*>calloc(n, sizeof(Cell))
        self.states = <State*>calloc(n * 3, sizeof(State))

        if self.cells == NULL or self.states == NULL:
            raise MemoryError()

    def __dealloc__(self):
        free(self.cells)
        free(self.states)

    @property
    def shape(self):
        return self.nx, self.nz

    cdef void _rect(self, int64_t min_x, int64_t min_z, int64_t max_x, int64_t max_z,
                    int delta) noexcept nogil:
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t ix0, ix1, jz0, jz1, ia, ib, ja, jb

        # Grid columns / rows strictly inside the rect (1 unit = the
        # tolerance the float version calls _EPS).
        ix0 = _bisect_right(self.px, nx, min_x + 1)
        ix1 = _bisect_left(self.px, nx, max_x - 1)
        jz0 = _bisect_right(self.pz, nz, min_z + 1)
        jz1 = _bisect_left(self.pz, nz, max_z - 1)

        if ix0 < ix1 and jz0 < jz1:
            _bump(&self.cells[0].node_bad, nz, ix0, ix1, jz0, jz1, delta)

        # Horizontal edges whose span overlaps the rect's x-range, on rows
        # strictly inside its z-range.
        ia = ix0 - 1
        if ia < 0:
            ia = 0
        ib = ix1
        if ib > nx - 1:
            ib = nx - 1
        if ia < ib and jz0 < jz1:
            _bump(&self.cells[0].h_obst, nz, ia, ib, jz0, jz1, delta)

        # Vertical edges whose span overlaps the rect's z-range, on columns
        # strictly inside its x-range.
        ja = jz0 - 1
        if ja < 0:
            ja = 0
        jb = jz1
        if jb > nz - 1:
            jb = nz - 1
        if ix0 < ix1 and ja < jb:
            _bump(&self.cells[0].v_obst, nz, ix0, ix1, ja, jb, delta)

    cdef void _lane_h(self, int64_t pos, int64_t lo, int64_t hi, int delta) noexcept nogil:
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t jz0 = _bisect_right(self.pz, nz, pos - self.limit)
        cdef Py_ssize_t jz1 = _bisect_left(self.pz, nz, pos + self.limit)
        cdef Py_ssize_t ia = _bisect_right(self.px, nx, lo + 1) - 1
        cdef Py_ssize_t ib = _bisect_left(self.px, nx, hi - 1)

        if ia < 0:
            ia = 0
        if ib > nx - 1:
            ib = nx - 1

        if ia < ib and jz0 < jz1:
            _bump(&self.cells[0].h_lane, nz, ia, ib, jz0, jz1, delta)

    cdef void _lane_v(self, int64_t pos, int64_t lo, int64_t hi, int delta) noexcept nogil:
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t ix0 = _bisect_right(self.px, nx, pos - self.limit)
        cdef Py_ssize_t ix1 = _bisect_left(self.px, nx, pos + self.limit)
        cdef Py_ssize_t ja = _bisect_right(self.pz, nz, lo + 1) - 1
        cdef Py_ssize_t jb = _bisect_left(self.pz, nz, hi - 1)

        if ja < 0:
            ja = 0
        if jb > nz - 1:
            jb = nz - 1

        if ix0 < ix1 and ja < jb:
            _bump(&self.cells[0].v_lane, nz, ix0, ix1, ja, jb, delta)

    cdef void _pack_h(self, int64_t pos, int64_t lo, int64_t hi, int delta) noexcept nogil:
        # Rows one lane spacing above and below a horizontal run of a sibling.
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t ia = _bisect_right(self.px, nx, lo + 1) - 1
        cdef Py_ssize_t ib = _bisect_left(self.px, nx, hi - 1)
        cdef Py_ssize_t jz0, jz1

        if ia < 0:
            ia = 0
        if ib > nx - 1:
            ib = nx - 1
        if ia >= ib:
            return

        jz0 = _bisect_left(self.pz, nz, pos + self.limit)
        jz1 = _bisect_right(self.pz, nz, pos + self.limit + PACK_SLACK)
        if jz0 < jz1:
            _bump(&self.cells[0].h_pack, nz, ia, ib, jz0, jz1, delta)

        jz0 = _bisect_left(self.pz, nz, pos - self.limit - PACK_SLACK)
        jz1 = _bisect_right(self.pz, nz, pos - self.limit)
        if jz0 < jz1:
            _bump(&self.cells[0].h_pack, nz, ia, ib, jz0, jz1, delta)

    cdef void _pack_v(self, int64_t pos, int64_t lo, int64_t hi, int delta) noexcept nogil:
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t ja = _bisect_right(self.pz, nz, lo + 1) - 1
        cdef Py_ssize_t jb = _bisect_left(self.pz, nz, hi - 1)
        cdef Py_ssize_t ix0, ix1

        if ja < 0:
            ja = 0
        if jb > nz - 1:
            jb = nz - 1
        if ja >= jb:
            return

        ix0 = _bisect_left(self.px, nx, pos + self.limit)
        ix1 = _bisect_right(self.px, nx, pos + self.limit + PACK_SLACK)
        if ix0 < ix1:
            _bump(&self.cells[0].v_pack, nz, ix0, ix1, ja, jb, delta)

        ix0 = _bisect_left(self.px, nx, pos - self.limit - PACK_SLACK)
        ix1 = _bisect_right(self.px, nx, pos - self.limit)
        if ix0 < ix1:
            _bump(&self.cells[0].v_pack, nz, ix0, ix1, ja, jb, delta)

    def paint_pack(self, const int64_t[:, ::1] h_lanes, const int64_t[:, ::1] v_lanes, int delta):
        """Add (``delta`` = 1) or take back (``-1``) runs to PACK against --
        same layout as :meth:`paint_lanes`. Unlike lanes these block nothing:
        once any are painted, a step alongside one (a lane spacing away, over
        the run's length) is cheaper than one that is not, so a wire being
        routed hugs its siblings for as long as it can."""
        cdef Py_ssize_t k

        with nogil:
            for k in range(h_lanes.shape[0]):
                self._pack_h(h_lanes[k, 0], h_lanes[k, 1], h_lanes[k, 2], delta)

            for k in range(v_lanes.shape[0]):
                self._pack_v(v_lanes[k, 0], v_lanes[k, 1], v_lanes[k, 2], delta)

        self.pack_runs += delta * (h_lanes.shape[0] + v_lanes.shape[0])

    def paint_rects(self, const int64_t[:, ::1] rects, int delta):
        """Add (``delta`` = 1) or take back (``-1``) obstacle rects --
        ``(R, 4)`` of ``min_x, min_z, max_x, max_z``, scaled."""
        cdef Py_ssize_t r

        with nogil:
            for r in range(rects.shape[0]):
                self._rect(rects[r, 0], rects[r, 1], rects[r, 2], rects[r, 3], delta)

    def paint_lanes(self, const int64_t[:, ::1] h_lanes, const int64_t[:, ::1] v_lanes, int delta):
        """Add (``delta`` = 1) or take back (``-1``) other wires' runs --
        ``(H, 3)`` of ``z, lo, hi`` for horizontal ones and ``(V, 3)`` of
        ``x, lo, hi`` for vertical ones, scaled."""
        cdef Py_ssize_t k

        with nogil:
            for k in range(h_lanes.shape[0]):
                self._lane_h(h_lanes[k, 0], h_lanes[k, 1], h_lanes[k, 2], delta)

            for k in range(v_lanes.shape[0]):
                self._lane_v(v_lanes[k, 0], v_lanes[k, 1], v_lanes[k, 2], delta)

    def search(self, int si, int sj, int gi, int gj, int64_t bend_cost,
               int forbid_start, int forbid_goal, bint use_lanes):
        """A* from grid node ``(si, sj)`` to ``(gi, gj)`` over what is
        currently painted -- see :func:`astar` for the search itself.

        :param use_lanes: ``False`` ignores the wire-lane counts (housings
            still block) -- the last-resort retry when the lanes leave no way
            through.

        :returns: Node indices ``i * nz + j`` start to goal as ``int32``, or
            ``None`` if unreachable.
        """
        cdef Py_ssize_t nx = self.nx
        cdef Py_ssize_t nz = self.nz
        cdef Py_ssize_t n_states = nx * nz * 3
        cdef int32_t goal_node = <int32_t>(gi * nz + gj)
        cdef int64_t gx = self.px[gi]
        cdef int64_t gz = self.pz[gj]
        cdef const int64_t* xs = self.px
        cdef const int64_t* zs = self.pz
        cdef State* st = self.states
        cdef Cell* cells = self.cells
        cdef int64_t limit = self.limit

        cdef Heap heap
        cdef Runs runs
        cdef int[4] mv_di
        cdef int[4] mv_dj
        cdef int[4] mv_nd
        cdef int[4] mv_off

        cdef Item it, nit
        cdef Py_ssize_t k, i, j, ni, nj, node, d, mv, nd, pos
        cdef int32_t sid, nsid, goal_sid, oh, ov, new_oh, new_ov, run, base
        cdef int64_t x1, z1, x2, z2, lo, hi, lane, lane_lo, lane_hi, cost, new_cost
        cdef bint blocked, allowed, packed, want_pack
        cdef int status = 0
        cdef Py_ssize_t length
        cdef int64_t hx, hz, hb
        cdef int32_t gen
        cdef Py_ssize_t pops = 0

        # A state's best cost / came-from only mean anything if its stamp is
        # this search's generation, so nothing has to be cleared between
        # searches -- on a grid of hundreds of thousands of states that
        # clearing used to cost more than the search itself.
        if self.gen == 0x7FFFFFFF:
            for k in range(n_states):
                st[k].stamp = 0
            self.gen = 0

        self.gen += 1
        gen = self.gen
        want_pack = self.pack_runs > 0

        heap.cap = 1024
        heap.n = 0
        heap.data = <Item*>malloc(heap.cap * sizeof(Item))

        runs.cap = 1024
        runs.n = 0
        runs.lane = <int64_t*>malloc(runs.cap * sizeof(int64_t))
        runs.lo = <int64_t*>malloc(runs.cap * sizeof(int64_t))
        runs.hi = <int64_t*>malloc(runs.cap * sizeof(int64_t))
        runs.parent = <int32_t*>malloc(runs.cap * sizeof(int32_t))

        if heap.data == NULL or runs.lane == NULL or runs.lo == NULL or runs.hi == NULL or runs.parent == NULL:
            free(heap.data)
            free(runs.lane)
            free(runs.lo)
            free(runs.hi)
            free(runs.parent)
            raise MemoryError()

        # Neighbour order is part of the search's tie-breaking -- keep it fixed:
        # left, right, down, up.
        mv_di[0] = -1; mv_dj[0] = 0; mv_nd[0] = 0; mv_off[0] = -<int>nz
        mv_di[1] = 1; mv_dj[1] = 0; mv_nd[1] = 0; mv_off[1] = <int>nz
        mv_di[2] = 0; mv_dj[2] = -1; mv_nd[2] = 1; mv_off[2] = -1
        mv_di[3] = 0; mv_dj[3] = 1; mv_nd[3] = 1; mv_off[3] = 1

        goal_sid = -1

        with nogil:
            sid = <int32_t>((si * nz + sj) * 3 + 2)
            st[sid].best = 0
            st[sid].came = -1
            st[sid].stamp = gen

            it.pri = 0
            it.cost = 0
            it.sid = sid
            it.oh = -1
            it.ov = -1
            _heap_push(&heap, it)

            while heap.n > 0:
                it = _heap_pop(&heap)
                sid = it.sid

                if it.cost > st[sid].best:
                    continue

                pops += 1

                node = sid // 3
                d = sid - node * 3

                if node == goal_node:
                    goal_sid = sid
                    break

                i = node // nz
                j = node - i * nz
                x1 = xs[i]
                z1 = zs[j]
                cost = it.cost
                oh = it.oh
                ov = it.ov

                for mv in range(4):
                    # Is this step open? (edge on the grid, destination and
                    # edge clear of obstacles, edge clear of other wires.)
                    if mv == 0:
                        if i == 0:
                            continue
                        allowed = not (cells[node - nz].h_obst or cells[node - nz].node_bad
                                       or (use_lanes and cells[node - nz].h_lane))
                        packed = cells[node - nz].h_pack > 0
                    elif mv == 1:
                        if i == nx - 1:
                            continue
                        allowed = not (cells[node].h_obst or cells[node + nz].node_bad
                                       or (use_lanes and cells[node].h_lane))
                        packed = cells[node].h_pack > 0
                    elif mv == 2:
                        if j == 0:
                            continue
                        allowed = not (cells[node - 1].v_obst or cells[node - 1].node_bad
                                       or (use_lanes and cells[node - 1].v_lane))
                        packed = cells[node - 1].v_pack > 0
                    else:
                        if j == nz - 1:
                            continue
                        allowed = not (cells[node].v_obst or cells[node + 1].node_bad
                                       or (use_lanes and cells[node].v_lane))
                        packed = cells[node].v_pack > 0

                    if not allowed:
                        continue

                    ni = i + mv_di[mv]
                    nj = j + mv_dj[mv]
                    nd = mv_nd[mv]

                    if nd == 0:
                        x2 = xs[ni]
                        if x1 < x2:
                            lo = x1
                            hi = x2
                        else:
                            lo = x2
                            hi = x1
                        lane = z1
                        run = oh
                    else:
                        z2 = zs[nj]
                        if z1 < z2:
                            lo = z1
                            hi = z2
                        else:
                            lo = z2
                            hi = z1
                        lane = x1
                        run = ov

                    # This path's own earlier runs, same lane rule.
                    blocked = False
                    lane_lo = lane - limit
                    lane_hi = lane + limit
                    while run != -1:
                        if (lane_lo < runs.lane[run] < lane_hi
                                and runs.hi[run] > lo and runs.lo[run] < hi):
                            blocked = True
                            break
                        run = runs.parent[run]

                    if blocked:
                        continue

                    if d == 2 and mv == forbid_start:
                        continue
                    if ni == gi and nj == gj and mv == forbid_goal:
                        continue

                    new_cost = cost + (hi - lo)
                    if d != 2 and nd != d:
                        new_cost += bend_cost

                    # Packing: with siblings to hug, a step that is not alongside
                    # one pays a sixteenth extra. A surcharge on the others, rather
                    # than a discount on these, so the cost never drops below the
                    # distance and the heuristic stays a lower bound.
                    if want_pack and not packed:
                        new_cost += (hi - lo) >> 4

                    nsid = <int32_t>((node + mv_off[mv]) * 3 + nd)
                    if st[nsid].stamp == gen and new_cost >= st[nsid].best:
                        continue

                    st[nsid].best = new_cost
                    st[nsid].came = sid
                    st[nsid].stamp = gen

                    new_oh = oh
                    new_ov = ov

                    if nd == 0:
                        if d == 0:
                            base = runs.parent[oh]
                            if runs.lo[oh] < lo:
                                lo = runs.lo[oh]
                            if runs.hi[oh] > hi:
                                hi = runs.hi[oh]
                        else:
                            base = oh
                        new_oh = _run_new(&runs, lane, lo, hi, base)
                        if new_oh == -2:
                            status = -1
                            break
                    else:
                        if d == 1:
                            base = runs.parent[ov]
                            if runs.lo[ov] < lo:
                                lo = runs.lo[ov]
                            if runs.hi[ov] > hi:
                                hi = runs.hi[ov]
                        else:
                            base = ov
                        new_ov = _run_new(&runs, lane, lo, hi, base)
                        if new_ov == -2:
                            status = -1
                            break

                    x2 = xs[ni]
                    z2 = zs[nj]
                    nit.cost = new_cost

                    # Priority = cost so far + a lower bound on what's left:
                    # the straight-line distance to the goal, plus one bend if
                    # a bend can't be avoided -- the goal is off both axes, or
                    # it's on one and we're heading along the other. Never
                    # overestimates, so the result is still the cheapest path,
                    # but with a 20 mm bend penalty it prunes far more states
                    # than distance alone.
                    hx = x2 - gx if x2 > gx else gx - x2
                    hz = z2 - gz if z2 > gz else gz - z2
                    hb = bend_cost
                    if hx == 0 and hz == 0:
                        hb = 0
                    elif hx == 0:
                        if nd == 1:
                            hb = 0
                    elif hz == 0:
                        if nd == 0:
                            hb = 0
                    nit.pri = new_cost + hx + hz + hb
                    nit.sid = nsid
                    nit.oh = new_oh
                    nit.ov = new_ov

                    if _heap_push(&heap, nit) != 0:
                        status = -1
                        break

                if status != 0:
                    break

        free(heap.data)
        free(runs.lane)
        free(runs.lo)
        free(runs.hi)
        free(runs.parent)

        self.last_pops = pops

        if status != 0:
            raise MemoryError()

        if goal_sid == -1:
            return None

        length = 1
        sid = goal_sid
        while st[sid].came != -1:
            sid = st[sid].came
            length += 1

        path = np.empty(length, dtype=np.int32)
        cdef int32_t[::1] out_view = path

        pos = length - 1
        sid = goal_sid
        out_view[pos] = sid // 3
        while st[sid].came != -1:
            sid = st[sid].came
            pos -= 1
            out_view[pos] = sid // 3

        return path
