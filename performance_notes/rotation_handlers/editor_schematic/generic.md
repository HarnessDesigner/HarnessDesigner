# harness_designer/rotation_handlers/editor_schematic/generic.py

## Line 168-240 (`_build_colors`, `_refresh_from_config`, `_update_position`, `_compute_aabb`, `_compute_obb`) — config and bounds
Cheap updates on config change or object move.

## Line 285-325 (`apply_drag_angle`) — one-axis angle write with an equality guard
Compares the current component with `float(_axis.get_axis(...))` before writing, so an unchanged value does not write. Runs per drag step.

## Line 354-424 (`pick`, `update_inner_drag`) — ray test and drag update per mouse move
Same pattern as the other handlers.

## Line 424-468 (`update_outer_hover`) — hover per mouse move
Tests the outer protractor under the mouse.

## Line 469-end (`render`) — per-frame draw
Draws the single schematic ring each frame.

**Reflection removed (fixed in this pass):** `_rings` read directly with a class-level default; the axis read and write go through `_axis`.
