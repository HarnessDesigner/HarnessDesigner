# harness_designer/rotation_handlers/rotation_ring/inner_ring.py

## Line 63-86 (`InnerRing.__init__`) — builds the drag ring
Creates the inner ring's torus and its pick geometry. Runs when the gizmo opens.

## Line 89-90 (`_get_label_color`) — a dict lookup per axis
Returns the axis label colour from a constant table. Cheap.

## Line 130-160 (`begin_inner_drag` path) — reads the start value with `_axis.get_axis`
Records the angle at the start of a drag. Runs once per drag.

## `hit_test` -- drag-start test per mouse move (static read, not measured)
Samples the band 65 times and for each sample builds two `Point`s through `Angle @ ndarray` and calls `camera.ProjectPoint` twice (about 130 projections and 130 `Angle` rotations per mouse move while the ring is visible, each of the order of tens of microseconds through the `Decimal` types). The ring's matrix is already stored (`_ring_matrix`), so the 130 world points could be one matmul and the projection one array multiply with the camera's matrices: probably under 0.5 ms instead of several ms. Not done.

## Line 303-end (`delete`) — teardown
Releases the GPU buffers. Runs once per session.
