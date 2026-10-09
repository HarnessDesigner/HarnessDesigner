# harness_designer/objects/objects_pegboard/bundle.py

## Line 447-... (`Bundle.render`) — full `BaseVar` pipeline per sub-segment
Same structure as the 3D bundle: one full render pass per segment, so the per-object pipeline overhead multiplies with the segment count. See `performance_notes/objects/objects_3d/bundle.md`.

## Line 303-... (`_recalculate_geometry`) and 327-... (`_update_position`) — recalculation per move
Same recalculation shape as the 3D bundle: one call per endpoint or waypoint move. See `objects_3d/bundle.md`.
