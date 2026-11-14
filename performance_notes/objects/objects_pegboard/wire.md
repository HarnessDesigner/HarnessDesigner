# harness_designer/objects/objects_pegboard/wire.py

Rewritten 2026-11-13: the history of the drag-path fixes (parts 1-4: the rope-pull rebind, the stub over-binding, the duplicated `_compute_obb`/`_compute_aabb`, `suspend_updates`/`resume_updates`) is done and is not repeated here. The current shape: `_recalculate_geometry` (line 472) honours `_update_suspended` (sets `_update_pending` instead of recalculating), computes the length and chord once and no longer calls `_compute_obb` / `_compute_aabb` a second time; `_bind_waypoints` (line 239) binds the geometry callback only to the innermost stub through the innermost trailing stub.

## Line 551-591 (`_segment_transforms`), 741-763 (`_rotation_from_direction`) — an `Angle` per segment per call
Same cost as the 3D wire (about 130 us per `Angle.from_axis_angle`), called from `_segment_world_corners` (bounds), `hit_test_step3` (line 683) and `_twist_segments`. See [../objects_3d/wire.md](../objects_3d/wire.md) for the fixes (cache per path version, derive from the compiled path).

## Line 705-711 (`render`)
Delegates to the tube batch (`mixins/tube.md`). One entry per conductor per frame.

## Line 683-703 (`hit_test_step3`)
Per segment: a full mesh transform plus the triangle test; same remedy as the 3D wire (local-space ray).
