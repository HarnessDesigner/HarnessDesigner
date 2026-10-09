# harness_designer/objects/objects_3d/bundle.py

## Line 646-664 (`Bundle.render`) — full `BaseVar.render` per sub-segment
Each sub-segment calls `super().render(shaders)`, which is `BaseVar.render`
(`objectsvar/base_var.py:1021`). That runs the `is_visible`/`is_dirty` checks,
two `mark_visible` calls on the AABB and OBB managers, a `with shaders.faces:`
bind/unbind, and a material uniform upload, all once per segment. For a bundle
with N segments that is N full render passes, when the only thing changing
between them is the transform. The material and program binds could be done
once around the loop, with only the transform and draw repeated. The per-segment
`_segment_transforms()` generator (line 660) also rebuilds `Point`/`Angle` objects
on every frame. The same caching opportunity as `wire.md` applies.

## Line 667-686 (`Bundle.render_selected_overlay`) — per-segment overlay, plus waypoint overlay loop
Same shape as `render`: one `_segment_transforms()` walk per frame for the
selected bundle, then `_render_waypoint_layouts`, which swaps the sphere VBO in
and out and draws the overlay group once per waypoint (lines 707-709). With
waypoints, each one costs a `glDepthMask` toggle through `_render_overlay_group`
(see `base_3d.md`). Only runs for the selected bundle.

## Line 510-539 (`Bundle._update_position`), 463-509 (`_update_angle`), 452-462 (`_update_scale`) — shadow `Base3D` without calling super
These do not call `super()`, which means the `BaseVar` update path (with its
`with self.editor.context:` GL context acquire, `_o_position` copy, and
`Refresh(False)`) is bypassed here. Whether that is correct depends on what
`Bundle` needs from those hooks; checking that is a functional question, not a
performance one. Flagged for the functional review, not analysed for
performance here.

## Line 540-574 (`_compute_obb`) and 575-645 (`_compute_aabb`) — recomputed per segment, and again per frame when dirty
`BaseVar.render` calls `_compute_aabb`/`_compute_obb` when `_vbo.is_dirty` is
set (`base_var.py:1036-1038`). For a multi-segment bundle, the dirty flag is
checked once per segment, not once per bundle, so a dirty bundle can rebuild its
bounds N times in one frame. That is only a cost while the flag stays dirty,
but worth confirming the flag clears on the first rebuild.

## Line 407-445 (`refresh_waypoints`, `refresh_diameter`) — called from handlers, not per frame
Not a per-frame cost; each call rebuilds geometry. Fine as written.
