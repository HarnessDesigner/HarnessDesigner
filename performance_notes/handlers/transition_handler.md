# harness_designer/handlers/transition_handler.py

## Line 75-130 (`_repoint_all_references`, `_delete_point_if_orphaned`) — SQL per referenced table
`_repoint_all_references` runs one `UPDATE` per referenced table (line 89-92). `_delete_point_if_orphaned` runs one `SELECT` per table (line 107-115). These run on a point merge or delete, not per frame. Fine.

## Line 141-203 (`_walk_bundle_chain`, `_walk_direction`) — one query per chain step
Walks the bundle chain, querying the layouts and bundles tables at each step. Runs on a placement, so the number of steps is the length of the chain. Fine.

## Line 346-375 (`_find_bundle`) — scans every bundle on a miss
Same pattern as `wire_layout_handler._find_wire`: when the picker misses, every bundle in the project is tested segment by segment on each call (line 356). It runs from a placement hover, so it runs on mouse moves. See `bundle_layout_handler.md` for the fix.

## Line 376-395 (`is_bundle_end_free`) — one SELECT per call
Checks whether a bundle end is already attached to a branch. Called per candidate end during placement.

## Line 396-430 (`_find_free_bundle_end`) — scans every bundle
Loops over every bundle (line 414). Called per hover from the add handlers. Cost linear in bundles, plus the per-endpoint checks.

## Line 432-470 (`_find_free_branch_ray`) — scans every transition, with a hit test each
Loops over every transition (line 454) and, for each, calls `hit_test_branch_ray` (line 451). The docstring says this is the free-branch lookup for bundle placement. `add_handlers/editor_3d/bundle.py:268` calls it from `hover`, so it runs on every mouse move during a bundle placement. Cost is (transitions) hit tests per move. A bounding-box pre-filter per transition would cut most of them.

## Line 650-720 (`RouteThroughTransitionHandler._highlight_branches`, `hover`) — every branch of every transition per hover
`_highlight_branches` loops over every transition (line 660) and every branch of each (line 661). `hover` (line 675) updates the highlights. Runs on every mouse move while the handler is armed. Highlights could be recomputed only when the hovered transition changes.

## Line 738-800 (`RouteThroughBundleHandler`) and 872-900 (`RoutedWireHandler`) — hover and release paths
Same shape as above: per-hover iteration over transitions and branches. The module docstring says `RoutedWireHandler` has no UI entry point and is kept for later. Its cost only matters if it is revived.

## Line 504-612 (`_apply_rotation`, `_branch_local_direction`, `_align_branch_to_bundle`) — matrix work on placement
Rotation matrices and Euler conversions. Runs on placement. Fine.
