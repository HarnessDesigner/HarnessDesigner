# harness_designer/shapes/torus.py

## Line 93-148 (`create`, nested `vert_idx`) — mesh loops over the torus grid
Builds the torus with nested loops over the radial and tubular resolutions. Each vertex index is computed by the nested `vert_idx` helper. The loops are in Python, so the cost grows with the square of the resolution. Fine at the default resolution of 20.

**Typing (fixed in this pass):** the resolutions are `int`, the radii are `float`, and `vert_idx` takes and returns `int`.
