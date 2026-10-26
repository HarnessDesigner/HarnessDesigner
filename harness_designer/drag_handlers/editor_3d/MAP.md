## FILES

#### __init__.py

`DragHandler3D(DragHandlerBase)` — owns `_delta3d`/`_axis_locked_delta3d` (project an anchor to screen space, add the raw mouse delta, re-project to world space, optionally lock to the dominant axis) and the move-arrows gizmo render. Ported from `gl.canvas_3d.dragging.base.DragObjectBase`. Concrete per-object-type handlers each track their own notion of "anchor" and decide what the computed world-space delta actually moves. A free-orbit 3D camera makes a raw screen-space mouse delta ambiguous (it could mean movement along any of X/Y/Z), so every 3D drag locks to whichever single axis dominates once the first couple of events have settled past initial click jitter, and shows a directional-arrows gizmo (`drag_handlers.move_arrows.MoveArrows`) once that lock engages — the one piece of drag mechanics that's genuinely 3D-only, since the 2D-style editors (schematic/pegboard) have an unambiguous locked top-down projection and never need it.

#### bundle.py

`Bundle(DragHandler3D)` — rigid-translate drag; moves the start point, every interior waypoint, and the stop point together by the same world-space delta, anchored wherever the mouse actually grabbed the bundle's true path (via `WireTypeMixin.get_closest_point`). Unlike Wire, a Bundle always moves as one rigid body no matter where it's grabbed — no anchor semantics, nothing to snap onto. Ported from `gl.canvas_3d.dragging.base.PathDragObject`.

#### generic.py

`Generic(DragHandler3D)` — moves `obj3d.position` directly; applies to housing, transition, splice, wire service loops, bundle layouts, wire layouts (anything whose entire position is the one thing a drag needs to move). Also realizes peg-board length changes every frame (`_realize_pegboard_length`, via `handlers.rope_pull_handler.realize_length_change`/`realize_3d_move`) for whatever chain(s) are anchored at this object's point(s). This logic must enumerate ALL of an object's points (every branch of a Transition, both ends of a Splice/WireServiceLoop), not just a single "center" point — a gap confirmed missing in an earlier pass after a live report that dragging a transition in 3D wasn't lengthening its attached bundle's peg-board chain at all.

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
