# harness_designer/add_handlers/editor_schematic/splice.py

## `hover` - per move
Calls `find_object`, `_wire_fits`, and `closest_point_on_wire_2d`. The last one is a Python loop over the wire's 2D points (true start, every waypoint, true stop) that computes a `hypot` per segment. It runs per move while a wire is snapped. Candidate: vectorise it with numpy.

## `_recreate_preview` - whenever the snapped wire changes
Deletes and recreates the preview, with DB inserts. Same churn candidate as [editor_3d/splice.md](../editor_3d/splice.md).
