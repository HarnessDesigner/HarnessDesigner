# harness_designer/shapes/arrow.py

## Line 28-37 (`create_vbo`) — cached move-arrow VBO
Returns the cached VBO for the move arrow, creating it once. Repeated calls are cheap. The arrow is built from cached primitives (see `shapes/__init__.md`), so no per-frame cost.
