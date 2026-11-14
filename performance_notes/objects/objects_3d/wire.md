# harness_designer/objects/objects_3d/wire.py

Rewritten 2026-11-13. `Wire.render` is now six lines that call `TubeMixin._render_tubes` (one batched draw for all wires, see `objects/mixins/tube.md` and `gl/wire_batch.md`), so the earlier note about nine program binds per segment no longer applies. What remains costly is the geometry work done around a path change and while the wire is selected. Measured on the real classes (interpreted Python, 2026-11-13): `Angle.from_axis_angle` 132 us, `Angle.from_quat` 94 us, `Point(...)` 2.1 us.

## Line 363-399 (`_recalculate_geometry`) — bounds computed twice per path change (still)
`self._scale.z = total_length` (line 385) fires `BaseVar._update_scale`, which takes the GL context, calls `_compute_obb()` and `_compute_aabb()` and `editor.Refresh(False)`; then lines 398-399 call `_compute_obb()` and `_compute_aabb()` again. The peg-board wire (`objects_pegboard/wire.py` line 472-534) had the same duplicate and no longer does. Removing the two trailing calls here (and in `objects_3d/bundle.py` lines 547-548) halves the bounds work per path change, with no behaviour change (the scale assignment already recomputes them). `_compute_obb` and `_compute_aabb` each call `_segment_world_corners`, which walks `_segment_transforms` (below), so each saved call saves a full pass of Angle constructions.

## Line 412-450 (`_segment_transforms`) and 679-701 (`_rotation_from_direction`) — an `Angle` per segment per call, about 130 us each
Each yielded segment builds `Angle.from_axis_angle(...)` (132 us) plus two `Point`s. `_segment_transforms` is called from `_segment_world_corners` (so from every `_compute_obb` / `_compute_aabb`), `segment_obbs` (line 502), `hit_test_step3` (line 558, per pick candidate), `_twist_segments` (per rebuild) and `render_selected_overlay` (line 588, every frame while the wire is selected). A path change therefore constructs about five Angles per segment (two bounds passes of two calls each, plus the plan), and a selected wire does one Angle per segment every frame: a selected wire with 20 segments spends about 2.6 ms per frame in these constructions alone.
Fixes, in order: (1) remove the duplicate bounds calls above; (2) cache the transform list per path version (invalidate where `_recalculate_geometry` already sets `_twist_plan = None`): memory is one `(position, angle, scale, length)` tuple per segment, about 0.5 KB per segment, which is a good trade for a result that is read several times per change and every frame while selected; (3) derive the rotation from the compiled path (`twisted_path.build_path` already returns each piece's quaternion and matrix) or compute it in floats instead of through `Angle`, which removes the 130 us per call (see `geometry/decimal.md`).

## Line 558-578 (`hit_test_step3`) — full mesh transform per segment on every pick candidate
For every segment it transforms the whole cylinder mesh (`(vertices_local * scale) @ angle`) and runs the vectorised triangle test, on top of the Angle construction above. As for `BaseVar.hit_test_step3` (see `objects/objectsvar/base_var.md`), transforming the ray into each segment's local space instead and testing the untransformed mesh removes the per-segment mesh transform.

## Line 266-294 (`is_housing_attached`) — full project scan
Loops over wires and their ends; called on user actions, not per frame.

## Line 588-664 (`render_selected_overlay`, `_render_waypoint_layouts`) — per frame while selected
The overlay renders each segment through `super().render_selected_overlay` with swapped transforms (one full render call per segment) and then the floor outline (see `gl/floor_outline.md`). Selected wires are few, so this is bounded; the Angle constructions above are the largest part.
