# harness_designer/shapes/sphere.py

## Line 21-43 (`create_vbo`) — cached sphere VBO
Returns the cached sphere VBO, creating it once. Repeated calls are cheap.

## Line 47-107 (`create`) — vertex and face arrays for a sphere
Builds the mesh once per resolution. Fine.
