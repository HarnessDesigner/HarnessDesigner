# harness_designer/handlers/snap_probe_set.py

## Line 151-189 (probe build) - checks every wire in the project for each open end, O(W^2)
For each wire that matches the part, `_is_open_wire_end` (line 170 and 182) walks every wire in the project and reads both endpoint positions through `_get_view_object`. That is one full project scan per open end, so building the probe set costs O(W) per open end and O(W^2) overall. The probe set is built once at drag start, not per move, so the cost is paid once per drag. For projects with a few hundred wires it is noticeable; a per-position count of endpoints, built once per probe set, would make each check constant time.

## Line 215-... (`_make_probe`) - one WireLayout facade per probe, built at drag start
Each probe constructs a facade. The cost is paid once per drag start, so no change is needed beyond the scan above.
