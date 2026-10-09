# harness_designer/objects/objects_3d/base_3d.py

## Line 225-307 (`_update_position`, `_update_angle`, `_update_scale`) — floor-lock bodies are commented out, so these are cheap
All three call `super()` and then only contain commented-out floor-lock code
(2026-09-06). No per-event cost is added here, so nothing to change. The
overrides do add a Python frame per drag event, which is negligible.

## Line 532-574 (`render_selected_overlay`) — per-frame guard chain before any work
Four attribute reads and `is_visible`/`is_selected` checks run every frame for
every object in the scene before the early return, and the overlay itself is
only drawn for the selected object. The early return is correct; the cost is
trivial because it is only attribute reads.

## Line 620-670 (`_render_overlay_group`) — `glDepthMask` toggled per selected object
Each selected object toggles `GL_DEPTH_WRITEMASK` off and back on around the
three overlays. This is one state change per frame for the selected object,
so it is fine. It only becomes a cost when the same method runs for many
waypoints (the `Wire`/`Bundle` waypoint-layout loop), where it toggles once per
waypoint. Hoisting the mask change out of the per-waypoint loop would remove
that churn.

## Line 673-717 (`render_aabb_overlay`) — rebuilds the AABB every frame
When `draw_aabb` is on, the corner array (`np.array([... for sx ... for sy ... for sz ...])`, line 707), the world transform, `adjust_aabb`, and two `Point` constructions all run every frame for the selected object. The
result changes only when the object moves, so it could be cached on the same
dirty signal `BaseVar.render` already uses. Debug-only and single-object, so
low priority.

## Line 719-748 (`render_obb_overlay`) — same pattern as the AABB
Recomputes the world center and extents every frame when `draw_obb` is on.
Same caching opportunity; debug-only.

## Line 759-773 (`_debug_box_corners`) and 861-884 (`_debug_box_edge_color`) — per-call small arrays
Each debug box builds an 8-corner array with a list comprehension, and the edge
color is recomputed per call. Both are tiny. Neither is a bottleneck on its own.

## Line 776-859 (`_render_debug_box`, `_render_debug_box_edges`) — roughly 20 draw calls per debug box
With both the AABB and OBB debug toggles on, a selected object issues one box
fill, then 12 cylinder draws and 8 sphere draws for the edges, for each of the
two boxes. That is about 40 separate draw calls per frame for one object, each
with its own `Point`/`Angle`/`Generic` material allocation (lines 852-859).
The VBOs themselves are cached (`create_vbo()` is a cached `global` lookup in
`shapes/box.py`, `cylinder.py`, `sphere.py`, and `square_outline.py`), so the
cost is Python and draw-call overhead, not mesh rebuilding. Batching the 12
edges into one instanced draw (or one pre-built edge-line mesh) would cut this
to a handful of calls. Debug-only.

## Line 886-956 (`render_floor_projection`) — runs every frame for the selected object
This one is not behind a debug toggle, so it is always on for the selected object.
It is a single outline draw, so the cost is one draw plus the world-corner math
(lines 917-938). The math could be cached on the same dirty signal as above.

## Inherited from `objectsvar/base_var.py` (`BaseVar.render` and the update hooks)
`Base3D` inherits its per-frame draw path from `BaseVar`, so these costs apply to every 3D object:

- `BaseVar.render` (`base_var.py:1021`) enters `with shaders.faces:` and uploads the material for every object, every frame (lines 1043-1046). That is a program bind/unbind pair per object. Batching objects by program would cut this, but it is a change to the canvas draw loop, not to this file.
- `BaseVar._update_position` (`base_var.py:476-507`) takes `with self.editor.context:` on every position event, even though the body only does numpy translation of `_obb`/`_aabb`. The GL context is not needed: `harness_designer/bounds/` imports only numpy and its own modules, so `_obb`/`_aabb` are CPU-side pool arrays (confirmed with `dep_trace.py`). This is the cheapest drag-path fix in the folder. See `performance_notes/objects/objectsvar/base_var.md`.
- `BaseVar._update_angle` and `_update_scale` (`base_var.py:510-544`) recompute the full OBB and AABB on every event, under the same context acquire.
