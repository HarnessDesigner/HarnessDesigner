# harness_designer/handlers/wire_layout_handler.py

## Line 25-38 (`_wire_segments`) — builds a list of segments on each call
Reads the start and stop positions and each waypoint's point, converting each to a NumPy array, and zips them into a list. Called once per wire inside `_find_wire`'s loop over every wire.

## Line 41-75 (`_find_wire`) — scans every wire on each miss
When the object picker does not hit a wire directly, the function falls back to a closest-segment search. It loops over every wire in the project (`project.wires`), skips the ones not in the 3D view, and for each wire computes the closest point to the mouse on every segment, in Python, with NumPy scalar operations. Cost is roughly (number of wires) × (segments per wire) per call, with a few array operations each.

This runs during wire-layout hover (the snap-to-wire search), so it runs on mouse moves whenever the picker misses. For a large project it is the most expensive step in this file. The fix is to compute the candidate list once per camera change (or limit it to wires near the cursor, using their bounding boxes), instead of testing every segment on every move.

## Line 78-103 (`_find_insertion_index`) — one pass over one wire's segments
Runs when a waypoint is inserted, not per move, unless a caller passes no index. Fine.

## Line 106-168 (`_create_wire_layout_at_endpoint`, `_create_wire_layout_on_wire`) — database writes on click
Each call inserts a point, a path row, a layout row, and constructs a layout view, then refreshes the wire's waypoints. Runs once per click. Fine.
