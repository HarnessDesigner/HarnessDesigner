# harness_designer/wire_routing/routing.py

Orthogonal A* routing for schematic wires. The compiled search is `astar.pyx` (see `astar.md`); this file builds the grid, the obstacle tables and the frame.

## Line 2050-2065 (`build_frame`), 1465-1689 (`RoutingFrame`) — the frame is rebuilt on every mouse move of a schematic housing drag
Corrected 2026-11-13: the earlier note said the frame is built once per drag. `drag_handlers/editor_schematic/generic.py` `Generic._route` (line 233) calls `reroute.build_frame` on every move of a housing drag (and `rotation_handlers/editor_schematic/generic.py` does the same per rotate step), so a new `RoutingFrame` is built for every move. `RoutingFrame.__init__` (line 1490) collects every obstacle rect in the whole project (`_obstacle_rects(project, -inf, -inf, inf, inf)`), builds the grid axes with `_frame_axis` (line 1429: every exact obstacle/endpoint coordinate plus a lattice at one lane pitch across the whole extent, merged and de-duplicated with `np.unique`), creates the `Router`, paints all obstacle rects and all static wire segments (`_static_segments` loops over every wire of the project), then routes each wire in turn. The cost per move is therefore O(obstacles + wires + grid nodes touched) for the whole project even though only the housing and its attached wires moved. The grid has about `(extent / pitch)^2` nodes, 62 bytes each (`astar.md`).
Fix: keep one frame (router) for the drag and update it with the `paint_*(..., -1)` / `(+1)` calls for what moved: take back the housing's old rect and its attached wires' old lanes, add the new ones, then route. The static part (every other obstacle and wire) is painted once at drag start. Memory price: the router's grid stays allocated for the drag (about 10 MB at 170,000 nodes, 93 MB at 1.5 million, committed only as touched). A cheaper first step that needs no new state: restrict the frame to a window around the batch (the dragged object, its attached wires and a margin) instead of the whole project; obstacles and static segments outside the window cannot affect routes inside it, and the node count falls from the project extent to the window. `_search_window` (line 1319) already restricts the search itself; the build step does not use a window.

## Line 988-1198 (`_astar_py`), 1229-1287 (`_astar`) — pure-Python fallback versus the compiled search
`_astar_py` is the reference implementation (heapq, Python loops); the compiled extension is used when it imports. The choice is a module-level check per call. Keep the fallback as the reference; make sure packaged builds ship the `.pyd` (`builder/cython_build.py` `_HAND_WRITTEN_EXTENSIONS`, per MEMORY.md).

## Line 899-984 (`_build_tables`), 859-895 (`_prepare_lanes`) — NumPy table builds per frame
Nine array allocations and a loop to build the allowed-step tables for the frame. Part of the per-move frame cost above.

## Line 1693-1724 (`_wire_segments_of`, `_static_segments`) — every wire of the project, per frame
Both loop over wires and read their segment arrays from the `SegmentPool`; `SegmentPool.segments` rebuilds the whole vertex array on each call (see `bounds/segment_pool.md`). Together with the frame rebuild this is a per-move O(project) cost.

## Line 740-839 (`free_segment_blocked`), 635-677 (`segment_blocked`) — per candidate segment
Vectorised over obstacles (nine NumPy calls). Called from the add handlers on every mouse move while a wire is placed (`add_handlers/editor_schematic/wire.md`), so its cost per call matters; it scans every housing and wire rect each time.
