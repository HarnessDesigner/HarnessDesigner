# harness_designer/objects/objects_3d/cable.py

The 3D view of a cable and its context menu. The draw goes through `TubeMixin` (see `objects/mixins/tube.md`).

## Line 261-335 (`_lead_frames`, `_end_frame`) — rebuilt from the twist plan; seven NumPy allocations per end
`_lead_frames` calls `_twist_segments()` (the plan that `mixins/tube.md` recommends building lazily) and `_end_frame` makes seven small arrays per end. Used when the fan-out or split geometry is needed, on user actions. Not per frame.

## Line 353-380 (`fan_out_positions`)
A loop with a sort over the conductors; user-action frequency.

## Line 397-407 (`refresh_waypoints`)
Per waypoint edit. Rebuilds the path (see tube.md). Cost is the twist-plan rebuild.

## Line 565-890 (`CableMenu`)
Menu actions; each defers its work with `QTimer.singleShot`. Not performance relevant.
