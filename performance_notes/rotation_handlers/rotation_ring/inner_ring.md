# harness_designer/rotation_handlers/rotation_ring/inner_ring.py

## Line 56-80 (`InnerRing.__init__`) — builds the drag ring
Creates the inner ring's torus and its pick geometry. Runs when the gizmo opens.

## Line 81-90 (`_get_label_color`) — a dict lookup per axis
Returns the axis label colour from a constant table. Cheap.

## Line 130-160 (`begin_inner_drag` path) — reads the start value with `_axis.get_axis`
Records the angle at the start of a drag. Runs once per drag.

## Line 303-end (`delete`) — teardown
Releases the GPU buffers. Runs once per session.

**Reflection removed (fixed in this pass):** `getattr(self._obj_angle, self.axis)` is now `_axis.get_axis(self._obj_angle, self.axis)`.
