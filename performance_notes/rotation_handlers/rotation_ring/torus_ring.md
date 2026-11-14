# harness_designer/rotation_handlers/rotation_ring/torus_ring.py

## Line 59-99 (`TorusRing.__init__`, `rebuild`) — builds the torus geometry
Builds the torus mesh (a sampled loop, line 153) and its buffers. `rebuild` runs when the ring size changes, not per frame.

## Line 187-194 (`delete`) — teardown
Releases the buffers. Runs once per session.
