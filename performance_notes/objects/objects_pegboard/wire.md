# harness_designer/objects/objects_pegboard/wire.py

## Line 499-... (`Wire.render`) — same structure and costs as the 3D wire
The pegboard wire renders each sub-segment through the full `BaseVar` pipeline, and it rebuilds the per-segment conductor `Point` every frame when a crimp segment is drawn. The stripe pass and its per-frame helix lookup have the same shape as the schematic wire. The shared costs and fixes are written up in `performance_notes/objects/objects_3d/wire.md` and `objects_schematic/wire.md`; they apply here unchanged.

## Line 288-340 (`_update_angle`, `_recalculate_geometry`, `_update_position`) — recalculation on every drag move
Same pattern as the 3D wire: every endpoint or waypoint move recalculates length, bounds, and the stripe capacity. See `objects_3d/wire.md`.

## Line 458-... (`hit_test_step3`) — full mesh transformed per segment on pick
Same full-mesh structure as the 3D `hit_test_step3`; see `objects_3d/wire.md`.

## `_segment_transforms` — same hidden-segment filtering as the 3D wire
See `objects_3d/wire.md`'s own note on this -- identical shape here (one extra list build from `self._waypoints(self.db_obj)`, no new query; the cache itself is populated by `_bind_waypoints`).
