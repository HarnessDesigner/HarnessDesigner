# harness_designer/geometry/cavity_layout.py

Pure geometry for the cavity stack of a housing: `compute_stack_geometry` (from a cavity count) and `compute_housing_cavity_geometry` (lines 149-337, per-cavity positions, one Python loop over the cavities plus a natural sort of the names).

## Callers (all in `database/project_db/pjt_housing.py` except one)
- `PJTHousingsTable.insert` (lines 309 and 354) and `PJTHousing.update_cavities` (586 and 631): once per housing creation, a one-time cost.
- `PJTHousing._compute_cavity_geometry` (1031) and `PJTHousing.stack_geometry` (1057): properties; how often a render or move path reads them has not been checked. If either is read per frame it should cache its result for the life of the housing (the cavity count and names do not change).
- `wire_routing/routing.py` `_lane_spacing` (line 99): calls `compute_stack_geometry` on a routing call. Routing runs per mouse move during a schematic drag, so confirm `_lane_spacing` is not recomputing the same stack for each wire; the result depends only on the cavity count, so a per-count cache (a dict holding one small object per distinct count) costs almost nothing in memory and removes the call.

## Line 149-337 (`compute_housing_cavity_geometry`)
Cost is O(n log n) in the cavity count (the sort) with a constant of a few microseconds per cavity. For a 50-pin housing this is well under a millisecond. Not a concern as a one-time call; revisit only if a caller turns out to call it per frame.
