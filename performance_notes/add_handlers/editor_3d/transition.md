# harness_designer/add_handlers/editor_3d/transition.py

## `hover` - per move
Calls `_find_free_bundle_end` (scans the project's bundles for a free endpoint) and, when snapped, `hit_test_branch_ray` on each move. The bundle scan runs per move. Not yet measured.
It calls `identify(...)` on the snapped bundle only when the snapped bundle changes, which is correct.

## `_commit_free` and `_commit_attached` - once per placement
These insert the point and branch rows, then call `_align_branch_to_bundle`. Not a concern.
