# harness_designer/shapes/disc_ring.py

## Line 37-45 (`create_vbo`) — cached disc-ring VBO
Returns the cached VBO for the default disc ring, creating it once.

## Line 66-140 (`create`, nested `vert_idx`) — annulus mesh loops
Builds the flat annulus with loops over the segments and rows, computing each vertex index with the nested `vert_idx(row, seg)` helper. The loops are Python, so cost grows with the segment count. Fine at the default resolution.
