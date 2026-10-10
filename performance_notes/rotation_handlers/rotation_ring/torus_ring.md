# harness_designer/rotation_handlers/rotation_ring/torus_ring.py

## Line 53-80 (`TorusRing.__init__`, `rebuild`) — builds the torus geometry
Builds the torus mesh (a sampled loop, line 153) and its buffers. `rebuild` runs when the ring size changes, not per frame.

## Line 181-188 (`delete`) — teardown
Releases the buffers. Runs once per session.

**Typing (fixed in this pass):** the GL context is typed; `rebuild` and `delete` return `None`.
