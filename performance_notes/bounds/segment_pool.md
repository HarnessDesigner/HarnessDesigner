# harness_designer/bounds/segment_pool.py

Callers of `segments()` (all in `wire_routing/routing.py`): `_wire_segments` (line 470), `_wire_segments_of` (1706) and `_static_segments` (1724). They run once per route computation, which is per mouse move while a wire is dragged in the schematic, so this is a drag-path function.

## Line 182-222 (`segments`) — whole-pool rebuild on every call
`np.stack(self._buffers)[:, [0, 2]]` copies every registered wire vertex into a new array and drops the Y column (a second copy), then `np.concatenate(wanted)` builds the index list, then `vertices[...]` makes a third array of `(S, 2, 2)`. With the `window` argument it also computes four reductions over all segments. Cost is linear in the total number of wire vertices in the project, per route call, even if the caller only needs the segments near the route.
Options: (1) apply the window to the vertices before the fancy index, so only nearby segments are materialised; (2) keep an `(N, 2)` x/z array in step with the buffers (the live-view design is why it does not exist: each vertex is a view onto a `Point`'s own buffer so a moving point needs no copy). Option 2 would duplicate vertex data (8 bytes per vertex for float32 x/z, tiny) but would need a write on every point move, which is the cost the current design avoids. Option 1 costs nothing in memory and is the first thing to try. Benchmark with a project with hundreds of wires before changing; for a small project the whole call is microseconds.

## Line 133-168 (`register`) and 171-179 (`release`)
`register` runs only when a wire's point list changes shape (a plain waypoint move needs no call because the vertices reference the live Point buffers). It allocates two small arrays. `release` drops vertex references on wire deletion. Neither is a concern.

## Line 111-124 (`_drop`)
Loops over a wire's vertices to decrement refcounts and calls `.tolist()` once. O(vertices in the wire). Fine.
