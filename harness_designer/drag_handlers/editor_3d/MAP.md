## FILES

#### __init__.py

`DragHandler3D(DragHandlerBase)` — owns `_delta3d`/`_axis_locked_delta3d` (project an anchor to screen space, add the raw mouse delta, re-project to world space, optionally lock to the dominant axis) and the move-arrows gizmo render. Ported from `gl.canvas_3d.dragging.base.DragObjectBase`. Concrete per-object-type handlers each track their own notion of "anchor" and decide what the computed world-space delta actually moves. A free-orbit 3D camera makes a raw screen-space mouse delta ambiguous (it could mean movement along any of X/Y/Z), so every 3D drag locks to whichever single axis dominates once the first couple of events have settled past initial click jitter, and shows a directional-arrows gizmo (`drag_handlers.move_arrows.MoveArrows`) once that lock engages — the one piece of drag mechanics that's genuinely 3D-only, since the 2D-style editors (schematic/pegboard) have an unambiguous locked top-down projection and never need it.

2026-10-30: once the axis lock engages, a handler that sets `self.cursor` gets `_latched_delta3d`: the point on the locked axis line closest to the mouse ray, so the dragged point stays under the pointer. Without a cursor the old per-frame delta is used. **Every 3D drag sets `self.cursor` (2026-11-08):** `WireDragMixin` (wire / cable ends and waypoint pairs, so wire-into-bundle too), `Generic` (waypoints of a wire / bundle / cable through their layout handles, housings, transitions, splices, ...), `Bundle`, `WireMarker` and `WireServiceLoop`. The latch keeps the point where it was relative to the pointer when the drag began: `_record_grab` (called on the drag's first event, before anything moves) stores the screen offset from the mouse-down spot to the anchor, and `_ray_distance_on_line` casts the ray through `cursor + offset`, so an object grabbed by its edge, or a waypoint handle sitting on the rounded path away from its waypoint, does not jump its origin under the pointer. `_line_latched_distance` is the same for a drag confined to a line (`WireMarker` along its wire, `WireServiceLoop` along `slide_axle()`, re-read every event): it is closed-loop (distance from where the object is NOW to the spot under the pointer), so an object that hit a stop catches up when the pointer returns instead of drifting. Both fall back to the old screen-delta move when the line points along the view ray.

#### bundle.py

`Bundle(DragHandler3D)` — rigid-translate drag; moves the start point, every interior waypoint, and the stop point together by the same world-space delta, anchored wherever the mouse actually grabbed the bundle's true path (via `WireTypeMixin.get_closest_point`). Unlike Wire, a Bundle always moves as one rigid body no matter where it's grabbed — no anchor semantics, nothing to snap onto. Ported from `gl.canvas_3d.dragging.base.PathDragObject`.

#### cable.py

`Cable(Wire)` (NEW 2026-11-07) - the 3D drag of a placed cable, the wire's drag with a cable's two differences: `plan_wire_drag` drops the snap (`plan.snap_point = None`: a cable's ends are always free, so no snap probes are built and nothing is committed on release) and `_route_locked_point_ids` is empty (a cable is not routed through bundles or transitions); and `__call__` lets the conductors follow each step (`objects.cable.Cable.follow_drag('3d', ...)`). Started by `objects_3d/cable.py` `Cable.handle_interaction` on a left-down on the SELECTED cable. Not run in the app (`pegboard_cable_test.py` covers the plan and `follow_drag` on stand-ins).

**Split end (2026-11-08):** a split end of the cable lies at the split plane (the end moves there when the cable is split), so the wire's own end test finds it and a click on the trunk's end drags just that end; `follow_drag` lays the split points on the new plane and carries the free ends of the leads, so the markers go with it.

#### generic.py

`Generic(DragHandler3D)` — moves `obj3d.position` directly; applies to housing, transition, splice, wire service loops, bundle layouts, wire layouts (anything whose entire position is the one thing a drag needs to move). Also realizes peg-board length changes every frame (`_realize_pegboard_length`, via `handlers.rope_pull_handler.realize_length_change`/`realize_3d_move`) for whatever chain(s) are anchored at this object's point(s). This logic must enumerate ALL of an object's points (every branch of a Transition, both ends of a Splice/WireServiceLoop), not just a single "center" point — a gap confirmed missing in an earlier pass after a live report that dragging a transition in 3D wasn't lengthening its attached bundle's peg-board chain at all.

**2026-11-08:** a waypoint of a wire or bundle is dragged with this handler through the layout's data object, started by the wire / bundle (`objects/mixins/waypoint_handles.py`), which passes itself as `arrow_object` (the move-arrows are sized by its box: the layout object has no geometry and so no box).

#### wire.py

`Wire(DragHandler3D, WireDragMixin)` — segment-local drag; thin view-specific shell around `handlers.wire_drag_base.WireDragMixin` (the shared planning/drag/live-snap-preview algorithm lives there, shared with the peg-board editor). Adds only the view accessors the mixin requires plus the 3D-only axis lock (`_move_delta` delegates to `_axis_locked_delta3d`). Ported from `gl.canvas_3d.dragging.wire.WireDragObject`.

#### wire_marker.py

`WireMarker(DragHandler3D)` — applies a plain, un-locked 3D world-space delta (no axis lock needed) since the marker's own `_update_position` callback always re-projects the result back onto the wire's current line regardless of direction. Uses the wire-aligned `wire_marker_arrow.WireMarkerArrow` gizmo instead of the axis-aligned `MoveArrows`.

#### wire_route.py

`WireRoute(Wire, WireRouteMixin)` — wire-into-skeleton drag-and-drop (`BUNDLE_PLACEMENT.md` section 12); thin per-view glue around `handlers.wire_routing_drag.WireRouteMixin`, subclassing this view's own ordinary `Wire` drag handler rather than `DragHandler3D`/`WireDragMixin` directly, so ordinary bend-drag behavior is inherited unchanged and only the eligibility scan / hover-highlight / drop-tracking is layered on top. Which concrete handler (`Wire` or `WireRoute`) gets constructed for a click is decided by `objects.objects_3d.wire.Wire.handle_interaction`, not here. Its eligibility scan was dead on arrival from a naming typo in the shared `WireRouteMixin` (`_moving` vs. `moving`) — see `handlers/MAP.md`'s `wire_routing_drag.py` entry; fixed 2026-10-08 but still unverified end-to-end in the live app.

#### wire_service_loop.py

`WireServiceLoop(Generic)` — the drag of a wire service loop whose context menu has **Lock to Wire** checked (`objects_3d.wire_service_loop.WireServiceLoop._create_drag_handler` picks it over `Generic`; the hook is `Base3D._create_drag_handler`). The mouse delta is applied as `wire_marker.py` does (`_delta3d`, no axis lock) but only its component along the wire counts: the direction is `WireServiceLoop.slide_axle()` (the line through the two wire points either side of the loop, NOT the start-to-stop line, which is ~27 degrees off), re-read every event because it turns when the loop is carried round a bend, and the distance goes to `WireServiceLoop.slide_along_wire`, which does the work (slide, hop a free bend, stop, pass a marker). The arrows are `wire_marker_arrow.WireMarkerArrow` on a Point of the handler's own kept on the loop's centroid (the loop's `position` is its start point, off to one end); their orientation is fixed when built, so they are deleted and rebuilt when the wire turns. The move gesture, the peg-board length realization and the collision session are all `Generic`'s, inherited; no collision search runs on the slide itself.

#### wire_snap.py

`SnapProbeSet(handlers.snap_probe_set.SnapProbeSet)` — the 3D-view concrete subclass (no module docstring; just the per-view specialization).


#### waypoint.py

`Waypoint(DragHandler3D)` (NEW 2026-11-08): the 3D drag of a waypoint that has no layout object, a cable's: the Point is moved by the same axis-locked screen delta `Generic` uses, in one write gesture; the cable's bound callbacks redraw it. Started by `WaypointOwnerMixin._arm_waypoint_drag` through the 3D `WireTypeMixin._make_waypoint_drag`.
