# harness_designer/add_handlers/editor_3d/splice.py

## `hover` - per move
Calls `find_object` (ray pick), `_wire_fits`, and `wire.obj3d.get_closest_point`. The first two run per move. Not yet measured.

## `_recreate_preview` - whenever the snapped wire changes
Deletes the old preview and inserts three 3D point rows and one splice row in the project DB. Moving the mouse across several wires therefore causes DB churn. Candidate: keep one preview and move its points, instead of recreating it on each wire change. Needs a check that nothing else references those row IDs during the session.
