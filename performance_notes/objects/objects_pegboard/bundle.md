# harness_designer/objects/objects_pegboard/bundle.py

## Line 447-... (`Bundle.render`) — full `BaseVar` pipeline per sub-segment
Same structure as the 3D bundle: one full render pass per segment, so the per-object pipeline overhead multiplies with the segment count. See `performance_notes/objects/objects_3d/bundle.md`.

## Line 303-... (`_recalculate_geometry`) and 327-... (`_update_position`) — recalculation per move
Same recalculation shape as the 3D bundle: one call per endpoint or waypoint move. See `objects_3d/bundle.md`.

**Fixed for the rope-pull drag path specifically (2026-10-16).** Mirrors `objects_pegboard.wire.Wire`'s identical fix exactly -- see that file's own note. Added `unregister_geometry_updates()`/`reregister_geometry_updates()` so `handlers.rope_pull_handler._apply_mid_drag` recalculates once per call instead of once per waypoint moved during its per-point `_place_active` loop, and skips even that one recalculation cheaply (no re-derivation) on a true no-op.
