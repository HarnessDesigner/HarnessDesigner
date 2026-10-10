# harness_designer/wire_routing/reroute.py

## Line 207-230 (`build_frame`) — builds a routing frame for the current batch
Creates the frame that the router works on. Runs once per drag or reroute request.

## Line 228-260 (`shift_targets`, `apply_shifts`) — one database write for many waypoints
`apply_shifts` moves every waypoint in a list with a single database write (see its docstring). That keeps a multi-wire shift to one write. The shift targets are built with a Python loop over the updates. Cost is linear in the number of waypoints moved.

## Line 284-365 (`follow_moved`, `_skipped_stub_segments`) — follows an object's move
Moves the wires attached to an object along with it. Runs on each drag step for the attached wires. The number of attached wires is small.

## Line 390-408 (`add_waypoint`, `remove_waypoint`) — database writes for one waypoint
Add or remove one waypoint row and its layout. Runs on a user action.

## Line 502-600 (`reroute_wire`) — full route for one wire
Routes one wire through the router (see `routing.md`), then writes its waypoints. This is the expensive call: it runs a full search per wire. It is called from the schematic drag path (see `drag_handlers/editor_schematic/generic.md` and the `wire.md` note there), so the number of calls per mouse move depends on how many wires are attached to the dragged object. A reroute on every move is the cost to watch.

## Line 658-735 (`wires_attached_to`, `sweep_for_overlaps`) — attachment and overlap checks
`wires_attached_to` gathers the wires touching an object. `sweep_for_overlaps` checks the moved object's bounds against wire segments, with a cheap box test first. Both are linear in the wires touching or near the object. Fine.

**Typing (fixed in this pass):** `fixed_prefix` is `list[tuple[float, float]] | None`; `skip_wires` is a `frozenset` of wires; `frame` is `_Union` over `RoutingFrame`; waypoint targets are `_point.Point`.
