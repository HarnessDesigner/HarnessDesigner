## FILES

#### __init__.py

`DragHandlerSchematic(DragHandlerBase)` — owns only the screen<->world projection (`_world_xz`), nothing else (no clamp, no gizmo). Like the peg board, this view's camera is a locked top-down orthographic projection, so there's no directional-arrows gizmo and no axis lock. Unlike the peg board, schematic dragging is never length-budget clamped — a schematic wire's path is entirely auto-routed around whatever's connected to it, not a fixed-length physical run.

#### generic.py

`Generic(DragHandlerSchematic)` — locked-X/Z drag for housing, terminal, splice. Every wire directly attached to the dragged object is live-rerouted on every move (`wire_routing.reroute.wires_attached_to`/`reroute_wire`), routed shortest-crow-flies-distance first, each pass excluding siblings not yet routed THIS pass from the "too close to another wire" check (an unsettled sibling's path is stale mid-drag — this rule exists specifically to prevent two siblings chasing each other's stale path back and forth every frame during the same drag). On release, `wire_routing.reroute.sweep_for_overlaps` catches any other wire left crossing the object's new footprint.

#### wire.py

`Wire(DragHandlerSchematic)` — interior-segment drag. Every schematic wire is a strictly orthogonal (H/V-only) chain; only a segment fully bounded by two real waypoints (not the wire's true start/stop) can be dragged directly — dragging it moves both bounding waypoints by the same perpendicular delta. A segment touching a true end gets its missing waypoints planted first (`_plan_end_segment_drag`). Five things happen live every move: straightening (redundant waypoints hidden, not deleted, until release), an obstacle hard-clamp on the two connecting edges, push/shove on the dragged segment itself (cascading up to `_MAX_PUSH_DEPTH` deep before falling back to a clamp), partial-move/jog (splits the drag in two when only part of the segment is blocked), and a full re-route fallback (`_maybe_reroute_past`) once a push chain fails outright and the user keeps dragging past it. This is by far the most algorithmically involved file in any of the `*_handlers` packages — read its module docstring in full before touching it; the push-depth limit (`_MAX_PUSH_DEPTH`) and the straighten-by-hiding-not-deleting behavior (DB delete only happens once, on release) are both deliberate, not incidental.

#### wire_marker.py

`WireMarker(DragHandlerSchematic)` — no gizmo (unlike the 3D editor's rotated arrow); the locked top-down camera makes drag direction unambiguous and the marker object's own re-projection onto its wire is the only constraint that matters.
