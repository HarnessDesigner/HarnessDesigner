# harness_designer/drag_handlers/editor_3d/wire_route.py

`__call__` calls `_update_hover` on every move. That repeats the hover pick for the route's end. Candidate: skip the pick when the cursor has not left the current target. Not profiled.
