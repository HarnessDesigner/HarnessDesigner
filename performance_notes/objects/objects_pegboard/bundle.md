# harness_designer/objects/objects_pegboard/bundle.py

Rewritten 2026-11-13; the fix history (the rope-pull rebind, the duplicated bounds calls, `suspend_updates` / `resume_updates`) is done. `Bundle.render` (line 575) delegates to `_render_tubes` (see `objects/mixins/tube.md`).

## Line 363-385 (`_rotation_from_direction`), 463-573 (`_compute_obb`, `_segment_world_corners`, `hit_test_step3`)
The same Angle-per-segment cost (about 130 us per construction) and per-segment mesh transform on a pick as the peg-board wire; see [wire.md](wire.md).

## Line 277-302 (`refresh_waypoints`, `refresh_diameter`)
Called from handlers on a waypoint or diameter change, not per frame.
