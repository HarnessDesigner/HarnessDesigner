# harness_designer/wire_routing/shield_ring.py

Places the dashed shield ring of a shielded cable's solder sleeve. Runs when a housing moves, a sleeve is added or the ring is dragged, not per frame.

## Line 252-274 (`foreign_pins`) — loops over every schematic wire per candidate position
For each ring candidate it loops over every schematic wire in the project and tests both ends, so it is O(wires) per candidate, and `auto_place` calls it while it searches for a free place and pushes the ring out one pitch at a time. For a project with hundreds of wires and a ring that needs several pushes that is thousands of cheap float tests. A per-project list of wire end positions (a NumPy array of `(x, z)`, rebuilt only when a wire's end moves) would turn each call into one vectorised mask; memory: 16 bytes per wire end. Not worth it until a profile shows it, since it runs once per ring placement.

## Line 490-536 (`move_ring`, `refresh`) — one `route_shield_group` per ring drag step
Dragging the narrow end calls `refresh`, which calls `reroute.route_shield_group` for the whole cable: a full reroute of the cable's wires and the ring placement, per mouse move. That is the cost to watch; it is the same per-move reroute described in `routing.md` and `reroute.md`.

## Line 217-290 (`ordered_gates`, `excluded_for`, `_rect_blocked`)
Small loops over the cable's own wires and the housing's rects. Fine.
