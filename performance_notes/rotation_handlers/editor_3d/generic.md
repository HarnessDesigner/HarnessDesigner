# harness_designer/rotation_handlers/editor_3d/generic.py

## Line 127-150 (`_build_colors`) — colours from config, on demand
Reads the three axis colours from the rotation config. Runs when the rings are built and when the config changes. Not per frame.

## Line 151-169 (`_refresh_from_config`) — pushes config into each ring
Loops over the rings and updates them. Runs on config change.

## Line 170-210 (`_update_position`, `_compute_aabb`, `_compute_obb`) — runs on each object move
Recomputes the bounds of the gizmo when the object moves or is rotated. Runs per transform change, which can be every mouse move while an object is dragged. Cost is small (a few vectors and one box).

## Line 314-332 (`apply_drag_angle`) — writes one Euler component
Unbinds the angle callback, writes the component with `_axis.set_axis`, and rebinds in a `finally`. The unbind/rebind keeps the write from re-entering this handler. Runs per drag step.

## Line 333-360 (`pick`) — ray test against the rings
Picks which ring the mouse is over. Runs per mouse move while the gizmo is shown.

## Line 423-492 (`update_inner_drag`, `update_outer_hover`) — per-move drag and hover
Compute the new angle while dragging, and the outer protractor hover, each mouse move. Each runs a ray test per ring.

## Line 493-end (`render`) — per-frame draw
Loops over the rings and asks each to draw. Runs every frame while the gizmo is shown. The per-ring draw calls dominate.

**Reflection removed (fixed in this pass):** `_rings` is read directly, with a class-level `None` default (set in `__init__`), instead of `getattr(self, '_rings', None)`. The axis reads and writes go through `_axis`. The `_rings` read happens during `__init__`, before the attribute exists, which is why the class default is needed.
