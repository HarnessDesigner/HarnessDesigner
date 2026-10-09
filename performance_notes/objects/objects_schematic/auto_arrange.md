# harness_designer/objects/objects_schematic/auto_arrange.py

## Line 148-204 (`_force_layout`) — O(N²) pure-Python pair loop, 500 iterations, and a constant recomputed every iteration
This is the most expensive code in the folder. For N nodes (housings and splices), each of up to `_MAX_ITERATIONS = 500` iterations walks every pair in Python (lines 167-192), so the work is about 500 × N²/2 pair evaluations, each with a function call.

Concrete waste inside that loop:
- `_min_separation(node_a, node_b, half_extents, weight, avg_od_mm)` (line 176) depends only on static inputs: the footprints (`half_extents`, computed once at line 159), the pair's wire count (`weight`), and `avg_od_mm` (once, line 160). None of them change across iterations, so the minimum separation per pair can be computed once before the loop and looked up. That removes one function call and a `frozenset` lookup per pair per iteration.
- `frozenset((node_a, node_b))` (line 175) is rebuilt on every pair every iteration. The weight matrix is also static, so it can be built once.

The bigger change is vectorization. Positions can live in an `(N, 2)` numpy array, the pairwise deltas and distances come from broadcasting over an `(N, N)` grid, and the precomputed `min_sep` and weight matrices feed straight into the force expression. One iteration then costs a handful of O(N²) numpy operations instead of N²/2 Python loop bodies. Iteration count and the convergence test (`_CONVERGENCE_EPS`, line 201) stay the same, so the result is unchanged up to floating-point order.

Scale: at 50 nodes this is about 1,250 pairs × up to 500 iterations, which is tolerable. At a few hundred nodes it is the difference between seconds and minutes, so it's worth doing before large projects are routinely auto-arranged.

## Line 207-249 (`_snap_and_resolve`) — O(N²) per pass, up to 20 passes, again pure Python
The overlap-nudging loop (lines 222-240) walks every pair on every pass, for up to 20 passes, and calls `_rects_overlap` per pair. The same vectorization applies: build all rectangles as arrays, compute the overlap mask in one broadcast, and only touch the flagged pairs. Most passes after the first should flag few or no pairs, so a mask-first approach makes the late passes nearly free.

## Line 99-123 (`_edge_weights`, `_average_od_mm`) — per-wire walk, once per arrange
These walk `project.wires` once per arrange action and call `_node_housing` per sibling. That is linear in the number of wires and runs once per user action, so it is fine.

## Line 43-67 (`_footprint_half_extent`, `_node_center`, `_node_housing`) — once per node
Each calls `node.objschematic.get_bounds()` once per node per arrange (lines 159 and 162 build the caches up front). Cheap, and correctly done once rather than inside the iteration loop.
