# harness_designer/shapes/sphere.py

## Line 21-47 (`create_vbo`) — cached sphere VBO
Returns the cached sphere VBO, creating it once. Repeated calls are cheap.

## Line 47-107 (`create`) — vertex and face arrays for a sphere
Builds the mesh once per resolution. Fine.

**Typing (fixed in this pass):** `radius` is `float`; `resolution` is `int | None`.
