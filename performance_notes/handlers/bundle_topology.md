# harness_designer/handlers/bundle_topology.py

## Line 25-119 (`merge_bundles`) — one merge, several database writes
Creates the merged bundle row, rewrites two waypoint routes, re-parents concentric layers (a loop over each bundle's layers), and deletes both originals. The waypoint and layer loops are linear in the number of waypoints and layers, which are small. Runs when the user joins two bundles, not per frame.

Both originals are deleted after their waypoints and layers have been moved over. The docstring says the now-empty concentric rows are left behind, which is an existing pattern in this codebase (no cascade). Those orphans accumulate over many merges.
