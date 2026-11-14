# performance_notes/bounds

Covers `harness_designer/bounds/` (`array_pool.py`, `aabb.py`, `obb.py`, `segment_pool.py`, `manager.py`, `__init__.py`).

The main per-move path is `ArrayPool.hit_test` through `gl.object_picker.find_object`. Its cost is one `np.concatenate` of every block plus a vectorised ray test, both linear in the object count. The main load-time cost is the linear `_refs` scan in `ArrayPool.__getitem__` (O(N^2) to fill a pool). `SegmentPool.segments` rebuilds the wire vertex array for every route computation during a schematic drag. See [array_pool.md](array_pool.md) and [segment_pool.md](segment_pool.md).

Memory is not a concern in this package: a row is 6 floats (AABB) or 24 (OBB), so 10,000 objects is under 1 MB per pool. That means speed fixes that cost a little memory here (an object -> slot dict, a cached x/z array) are cheap in memory terms; the real price of the bigger ones is complexity, because the pools are built around fixed block addresses.
