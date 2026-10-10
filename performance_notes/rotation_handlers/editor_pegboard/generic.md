# harness_designer/rotation_handlers/editor_pegboard/generic.py

## Line 140-200 (`_build_colors`, `_refresh_from_config`, `_update_position`, `_compute_aabb`, `_compute_obb`) — as in the 3D handler
Colour and bound updates on config change or object move. Cheap.

## Line 255-320 (`apply_drag_angle`, `pick`, `update_inner_drag`) — per drag step and per mouse move
Same shape as the 3D handler: a single-axis angle write, a ray test against the rings, and the drag update. The peg-board handler has one axis (`AXES = ('y',)`), so there is one ring to test.

## Line 336-380 (`update_outer_hover`) — hover per mouse move
Tests the outer protractor under the mouse. Runs on each mouse move while the gizmo is shown.

## Line 381-end (`render`) — per-frame draw
Draws the single ring each frame.

**Reflection removed (fixed in this pass):** `_rings` read directly with a class-level default; the axis write goes through `_axis.set_axis`.
