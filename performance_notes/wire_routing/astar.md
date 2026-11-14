# harness_designer/wire_routing/astar.pyx

Compiled core of the schematic router: a 4-directional A* over a compressed grid (`astar`, `build_tables`) and the `Router` class, one drag frame's grid shared by every wire routed in it. Compiled with `boundscheck=False`, `wraparound=False`, `cdivision=True`, `nonecheck=False`; the heap, the run arena and the tables are `malloc`'d C arrays and the search is `nogil`, all integer math (coordinates scaled by 1,000,000). `routing.py` falls back to the pure-Python `_astar_py` if the extension is missing; the fallback is also the reference the compiled result is checked against.

## `Router.__cinit__` — memory is `calloc`'d and only paid for when touched
The router allocates `nx * nz` cells (7 shorts = 14 bytes) and `3 * nx * nz` search states (16 bytes each), about 62 bytes per grid node. Measured (2026-11-13): creating and freeing a `Router` takes about 0.03 ms whatever the size (100x100 up to 1500x1000 nodes), because `calloc` returns lazily-zeroed pages; the memory (about 10 MB at 170,000 nodes, 93 MB at 1.5 million) is committed only as `paint_rects`, `paint_lanes` and `search` touch it. So the cost of a large grid is in painting and searching it, not in creating it.

## `paint_rects`, `paint_lanes`, `paint_pack`, `search` — incremental by design
Each paint takes `delta = +1` or `-1`, so a rect or a wire's lanes can be added and taken back without rebuilding the grid. `search` counts its pops in `last_pops`. This API is what makes it possible to keep one router for a whole drag and update only what moved (see `routing.md`: today `build_frame` builds a new frame on every mouse move).

## Memory versus speed
62 bytes per node is a good trade for an integer-indexed search with O(1) cell tests. The number of nodes is what matters (`routing.md`: the lattice covers the whole project extent).
