# harness_designer/objects/objects_3d/wire_service_loop.py

Rewritten 2026-11-13. The collision search no longer runs in NumPy on meshes: it is the compiled `LoopSearch` in `wire_service_loop_search.pyx` (see its note), which replaced the mesh-against-mesh narrow phase, the `(M, N, 3)` intermediates and the 16-step roll loop that the earlier notes described. What is left in this file is the setup around the search.

## Line 579-628 (`begin_move_session`) — builds the whole search structure once per move session, with an `Angle` per wire segment in the viewport
It lists every candidate in the viewport (`_viewport_candidates`, which uses `AABB.visible_objects`), and for each wire calls `candidate.obj3d.segment_obbs()` (`objects_3d/wire.py` line 502), which goes through `_segment_transforms` and constructs an `Angle` per segment (about 130 us each, see `objects_3d/wire.md`). With 200 wires of 10 segments in view that is 2,000 constructions, about 260 ms of setup, before the C search starts; it is also copied into the C structure with `self._vbo.vertices.reshape(-1, 3)`. This is once per session, so it is a start-of-drag hitch rather than a per-move cost. The fixes to `_segment_transforms` (a per-path cache, or float math instead of `Angle`) remove most of it.

## Line 640-744 (`_resolve_collision`) — one search per move; a one-shot session when none is open
Per move it builds a few small arrays (seven NumPy allocations: pivot, axis, `q0`, scale, limits) and calls `session.loop_search.search(...)`. If no session exists (`self._move_session is None`, line 691) it builds one and discards it after the call ("one-shot"), which pays the whole `begin_move_session` cost for a single resolve. Callers that resolve repeatedly (a slide in a loop) should open a session first; check that the drag handler and `_hop` do.

## Line 1086-1131 (`_slide_once`), 1163-1302 (`_hop`), 1305-1349 (`_pass_markers`) — slide and hop along the wire
Loops with a few NumPy calls per step (eight allocations in `_hop`); the number of steps depends on how many markers and bends the loop passes. Per drag step, and bounded by the wire's marker count.

## Line 365-403 (`_update_angle`), 525-553 (`_apply_resolved`)
Per move: one angle write plus callbacks. Each `Angle`/`Point` write fires its listeners (`app_mixins/callback_mixin.md`, about 5 us with three listeners). Fine.

## Memory
The `_MoveSession` holds the attached wires, markers and the `LoopSearch` (C arrays of every candidate box and the loop mesh) for the duration of the move; it is released at the end of the session.
