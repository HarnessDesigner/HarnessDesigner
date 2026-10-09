# harness_designer/handlers/wire_routing_drag.py

## Line 330-344 (`_update_hover`) - runs on every mouse move during a routed drag
`find_drop_hit` runs on every move (line 336). It calls `object_picker.find_object`, which is the full picker (see performance_notes/gl/object_picker.md), and then, for each eligible branch, a ray-sphere test through `_view_transition(...).hit_test_branch_ray` (line 204). The picker call dominates. The hover highlight is only redrawn when the target changes (line 339), which is the right guard. Caching the pick between moves while the cursor stays in one region would cut the per-move cost.

## Line 178-208 (`find_drop_hit`) - bundles first, then branches
The bundle check reuses the picker result, so no second pick is made for bundles. Branches are tested with a loop over eligible branches, each a ray-sphere test, so the cost is linear in eligible branches per move. The eligible set is small (only fitting bundle ends and branches), so this is fine.

## Line 108-... (`compute_eligible_targets`) - once per drag start
Walks project bundles and transitions once and checks freeness per end. The `is_in_*` checks it makes now read the view pools (see performance_notes/gl/camera notes), so this is one array read per object rather than a camera scan.
