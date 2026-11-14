# harness_designer/objects/objects_pegboard/cable.py

The peg-board view of a cable. Draw is `TubeMixin` (see `objects/mixins/tube.md`).

## Line 292-332 (`_seed_from_3d`) — once, when the cable first appears on the board
Unfolds the 3D route into the board plane with a loop over segments (`point.copy()` and NumPy per step). One time per cable. Not a concern.

## Line 239-268 (`fan_out_positions`), 172-204 (`_end_frame`)
As in the 3D cable view; user-action frequency.

## Line 347-357 (`refresh_waypoints`)
Per waypoint edit; cost is the twist-plan rebuild.
