# harness_designer/objects/objects_pegboard/table_placement.py

## Line 140-173 (`obstacle_rects_from_objects`) — linear in the objects in view, once per table creation
Walks the objects in view once and reads each one's `vbo` and `aabb`. Runs only when a new peg-board table is placed (the module docstring says so), so the cost is one linear pass per user action. No change needed.

## Line 176-... (`find_free_position`) — fixed-size ring search
Expands rings with a fixed angle count per ring. Runs once per new table, not per frame, and the module docstring explains the choice. No change needed.
