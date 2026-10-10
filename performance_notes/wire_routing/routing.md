# harness_designer/wire_routing/routing.py

## Line 961-1200 (`_astar_py`) — pure-Python A* fallback
The reference implementation of the grid search, used when the compiled `astar` extension is not built (line 1233). It uses `heapq` and a Python loop over the open set, which is much slower than the compiled version for large grids. The compiled module is the one to build for production use. The function is kept as the reference the compiled one is checked against (docstring).

## Line 1200-1260 (`_astar`) — dispatch to the compiled search when it exists
Picks the compiled search if the extension was imported (line 1233), otherwise falls back to `_astar_py`. The choice is made per call from a module-level value, so the cost of the check is negligible.

## Line 931-943 — `bisect` to find grid cells
Binary search over sorted grid coordinates to find the cells a segment touches. Logarithmic per query. Fine.

## Line 1288-1310 (`_search_window`) — per-route search window
Chooses the rectangle the search may use. Runs once per route.

## Line 1456-1560 (`RoutingFrame.__init__`, `__contains__`, `route`) — one router per frame, one route per wire
`RoutingFrame` builds the router once (line 1506) and routes each wire of the batch in turn. The `route` method settles each wire into the grid, so later wires see earlier ones as obstacles. Cost is one search per wire, per frame. The frame is rebuilt whenever a drag starts (see `build_frame`), not per mouse move.

## Line 1640-1680 (`_wire_segments_of`, `_static_segments`) — rebuilt for each frame
`_static_segments` loops over every wire in the project (line 1670) to collect the segments that stay in place, and `_wire_segments_of` does the same for the batch (line 1657-1661). Both run when a frame is built. In a large project this is linear in the total number of wires per frame. A cache keyed on the project's wire set would avoid the rebuild when only the batch changes.

## Line 1911-2016 (`plan_shift`, `route`) — planning and the public route entry point
`plan_shift` computes new positions for shifted waypoints. `route` is the public entry point for one route. Both run on a drag step or a route request.

**Typing (fixed in this pass):** the run-test helpers take a `_Runs` alias for the four per-run arrays; nested helpers `moved`, `keeps_direction` and `add` are typed; `RoutingFrame` methods take `Wire` arguments; one local variable annotation that said `object` now says `Wire`.
