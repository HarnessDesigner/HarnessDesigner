# harness_designer/objects/objects_pegboard/wire_highlight.py

Highlights the transition branches and wire ends a wire passes through, when the wire is hovered or selected in a table.

## Line 244-290 (`_light_branches`, `_light_ends`)
Loops over the wire's path rows, looks each branch up (`branch.transition.get_object()`), then loops over each transition's branches with a `db_id` comparison. Cost is O(path branches x branches per transition); both are small (a wire crosses a few transitions, a transition has a few branches). Runs per hover change, not per frame. Fine.
