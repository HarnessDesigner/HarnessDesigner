# harness_designer/utils/snap_pool.py

## Line 14-24 (`SnapPool.__init__`) — NumPy array built once per pool
Converts the snap points to an array once. Cheap per pool.

## Line 25-38 (`SnapPool.query`) — vectorised distance per mouse move
One subtraction and one sum over all points per query, then `argmin`. Linear in the number of points, but in NumPy. Called from the snap handlers on each mouse move.

**Edge case (flagged, not changed):** `query` checks only `if not self.objects` (line 26). If `objects` is non-empty and `snap_points` is empty, `dist_sq.argmin()` raises `ValueError: attempt to get argmin of an empty sequence`. The callers in this codebase build both lists from the same set, so this has not been seen in practice. A guard on the point count would remove the risk.

## Line 39-70 (`SnapPool.query_ray`) — perpendicular distance to a ray per mouse move
Same shape as `query`, but computes the perpendicular distance from each point to a ray. Linear in the number of points, vectorised. Same empty-points edge case as `query`.

**Typing (fixed in this pass):** `SnapPool` is generic over the object type (`_T`), since callers pass housings, seals and terminals. `query` and `query_ray` return `_T | None`.
