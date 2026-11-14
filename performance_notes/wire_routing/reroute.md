# harness_designer/wire_routing/reroute.py

## Line 298-320 (`build_frame`) — builds a new routing frame, and is called on every mouse move of a schematic drag
`drag_handlers/editor_schematic/generic.py` `Generic._route` calls it per move (and `rotation_handlers/editor_schematic/generic.py` per rotate step, `route_shield_group` per shield cable). The earlier note that it runs once per drag was wrong. See `routing.md` for the cost and the fix (a persistent frame updated incrementally, or a window around the batch).

## Line 656-820 (`reroute_wire`) — one search per wire, per move
Routes one wire through the frame, then writes its waypoints. Called per attached wire per mouse move in the schematic drag, so with N attached wires a move costs N searches plus the frame build. Writes go through `apply_shifts` (one `batch_update`, a single database call; inside a drag gesture it only changes the in-memory store).

## Line 391-483 (`follow_moved`), 487-514 (`_skipped_stub_segments`) — nested loops over the moved object's wires
Moves the wires attached to a moved object along with it. Loops over wires and their segments; the attached wire count is small.

## Line 869-927 (`route_shield_group`)
A frame plus routing for each cable end's group, shield wires first. Called per move for shielded cables and once per sleeve placement.

## Line 1013-1106 (`_schematic_wires`, `sweep_for_overlaps`)
Loops over every schematic wire per sweep; a sweep is run after an edit, not per frame.

## Line 518-637 (`add_waypoint`, `remove_waypoint`, `set_waypoints`)
Per user action; database writes inside a gesture. Fine.
