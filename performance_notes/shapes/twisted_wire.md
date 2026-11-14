# harness_designer/shapes/twisted_wire.py

Pure-Python helpers for the twisted-wire geometry (`profile`, `round_bends`, `plan`, `ring_count`) plus the constants the shader and `twisted_path.pyx` share. The viewport path no longer uses `round_bends`/`plan`: `twisted_path.pyx` does the same work in C. They remain as the reference implementation and are still called by the ribbon-cable code.

## Line 305-378 (`round_bends`), 382-439 (`plan`) — Python loops with NumPy calls per bend and per piece
Nested loops with small NumPy calls (`np_loop`), so each ribbon-cable path rebuild costs microseconds per bend and per piece (and is slow compared with `build_path`). Ribbon cables are rare, so this only matters for a project with long ribbon runs being dragged. If it shows up, route the ribbon look through `build_path` too (pass `rounded=False`, which the compiled function already accepts).

## Line 141-201 (`profile`)
Builds the cross-section outline once per look; not per frame.

## Line 280-301 (`_transport_delta`) — six NumPy allocations per call
Used inside `round_bends` for each bend; the compiled version has its own `nogil` copy. Same remark as above.
