## FILES

#### __init__.py

Package init for the actual renderable 3D views — constructed as `SomeType(parent=wrapper, db_obj=pjt_entry)` from the matching `objects/<type>.py` wrapper. Geometry comes from `db_obj.part` (model3d reference, dims) via `gl/` VBOs. This directory is named `objects3d` (no underscore) in CODEBASE_MAP.md — the real on-disk name is `objects_3d`; see `objects/MAP.md` for the full rename note. `Base3D.identify()` and the schematic-side menus were still stubs/WIP as of 2026-06-11 per MEMORY.md — re-check current status before assuming either is complete. Drag/rotate interaction for 3D objects is being rebuilt as object-driven handler classes (`drag_handlers/editor_3d/`) rather than the old `gl/canvas_3d/mouse_handler.py`/`rotation_rings.py`/`move_arrows.py` — those old files are confirmed dead code the user is rewriting personally; don't propose fixing or wiring them back up (MEMORY.md).

#### base_3d.py

`Base3D(BaseVar)` (~960 lines) — the base 3D object; see `objectsvar/MAP.md` for what's inherited vs. defined here. Overrides `_update_angle`/`_update_position` for 3D-specific VBO/world-space geometry handling.

#### boot.py

One file per harness part, a `Base3D` subclass taking `(parent, db_obj)` — same shape across this whole directory.

#### bundle.py

3D + peg-board only (no schematic view); design in `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md`.

#### bundle_layout.py

Companion to `bundle.py`, same 3D + peg-board-only scope.

#### cavity.py

`Cavity3D` owns its own selection/overlay state (`render_selected_overlay`, `render()`, its own `_terminal_marker`/`_wire_marker`) via the generic `is_selected` mechanism, reaching `Housing3D` only for the shared ray-mesh/picker primitives — this replaced an earlier, broken design where `Housing3D._surf_to_cavity`/`_cavity_markers` tracked selection as a hand-synchronized copy, which could desync from the real `is_selected` state (MEMORY.md, "Fixed (2026-09-04)... architectural root cause found"). Bind to `db_obj.angle3d` (the project cavity's world-space angle), never `db_obj.part.angle3d` (the baked catalog angle) — and don't override `_update_angle`/`_update_position` here; `Base3D`'s own implementation handles it correctly once the right angle is bound. The override existed at one point to propagate rotation deltas to the terminal, but combined with the project-angle binding it created a callback chain that fired during project loading (before all objects were initialized) and froze the app (MEMORY.md, "Cavity 3D angle binding").

#### circuit.py

The 3D editor's view of a circuit: an inert placeholder (`Base3D` built with no vbo/angle/position/scale/material, never visible, `obb` None), built like a `Note` that was never placed in this editor. A circuit has nothing to draw; the view exists so the canvas can hold the circuit as its one selected object (see `objects/circuit.py`). The mouse can not pick it. Added 2026-10-25. Its `set_selected` is overridden (2026-10-25): deselecting also calls `Circuit.deselect_in_editor()`, so the circuit editor stops showing the circuit's row as selected (it clears the row only when that row is the selected one, otherwise it does nothing).

#### cover.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### cpa_lock.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### generic.py

One file per harness part, same `Base3D(parent, db_obj)` shape — the catch-all for part types without dedicated geometry handling.

#### housing.py

Builds this housing's `Cavity` wrappers **synchronously** in `Housing.__init__` (not deferred) — see MEMORY.md's 2026-09-04 fix entry; a once-broken 3D cavity-selection-overlay/context-menu mechanism (`_surf_to_cavity`/`_cavity_markers`) has since been moved onto `Cavity3D` itself (see `cavity.py` above). Its legacy cavity-surface/marker overlay draw (`_draw_overlay_triangles`) used raw fixed-function GL (`glVertexPointer`/`glColor4f`) until the 2026-08-21 VBO/shader rewrite replaced it with `_draw_overlay_faces` — if an overlay/decal mysteriously stops drawing after a canvas change, see MEMORY.md "Legacy fixed-function immediate-mode GL calls silently render nothing under the new shader pipeline."

#### menu_ops.py

Shared context-menu callback helpers (`select_object`, `clone_object`, `delete_object`, `show_properties`, `start_handler`, `run_attached_handler`, `get_part_id`-style helpers) used by every part type's context menu. `trace_circuit(view, db_obj=None)` accepts any editor's view object (3D, schematic or peg-board) and hands the work to `Circuit.highlight(True)`; it used to call `obj3d.editor3d.Refresh()`, which a peg-board view does not have. The schematic menus' `on_trace_circuit` (and every other action in those four `objects_schematic` menus) is still an empty `pass` stub. Must be imported lazily from call sites outside `objects_3d` itself — see the circular-import trap in `objects/MAP.md` (`objects/<type>.py` imports `objects_3d/<type>.py` at module level; `handlers` imports `objects`; `ui` imports `handlers`).

#### note.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### project_model.py

One file per harness part, same `Base3D(parent, db_obj)` shape; hardcodes position/scale at the origin today since `objects/project.py`'s `Project.model_id`/`color_id` have no position/scale/angle columns yet (MEMORY.md, "Empty-space right-click menus" entry).

#### seal.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### splice.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### table.py

`Table(Base3D)` — the floating wire table's 3D-view rendering; same class name as `objects_pegboard/table.py`'s and `objects_schematic/table.py`'s own `Table`, not shared code — the facade is `objects/pegboard_table.py`.

#### terminal.py

Owns `detach_wires()` (terminal delete cuts wires free in all views) and `render_cavity_overlay` (wire/pin-side tint matching its seated cavity's marker) — both **NOT yet run in the GUI**, see `objects/MAP.md`'s terminal.py entry for the full mechanics. Its legacy overlay code shared the same fixed-function-GL trap as `housing.py` above until the same 2026-08-21 rewrite.

#### tpa_lock.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### transition.py

Model-building design in `TRANSITION_DESIGN.md` — read it in full before touching transition model-building code here.

#### wire.py

Part of the wire family (with `wire_layout.py`/`wire_marker.py`/`wire_service_loop.py`).

`segment_obbs()` is the public per-section box a collision test needs: `(S, 8, 3)`, one oriented box per wire section in the bounds pool's corner order (0 = min corner, 1 toggles x, 3 toggles y, 4 toggles z). **A wire's pool OBB (`obb`, from `_compute_obb`) is NOT that**: it is the axis-aligned union envelope of every section, so a diagonal or bent wire's `obb` is a far larger box than the wire — fine for picking, wrong for collision. `_segment_world_corners` (the min/max source for `obb` and `aabb`) reuses `segment_obbs`.

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family. The 3D loop view; its placement collision avoidance (`_resolve_collision`: the nearest clear roll about the WIRE in 2 degree steps, then slide along the wire up to the two wire points and any marker) is the part with history. **The loop rolls about the wire, not about the line between its own start and stop points** (user, 2026-10-25): that line sits at an angle to the coil's axis (the helix's connection vector is 27.2 degrees off the wire direction, the stop point 2.8 mm off the wire line), so rolling about it makes the coil wobble. `_wire_points` finds the wire point just before the loop (previous point of the attached wire that ends at the loop's STOP point: a waypoint or its start) and the one just after it (next point of the attached wire that starts at the loop's START point) -- the stop point is the one on the side the wire comes from, the helix's endpoint lies behind its start, and `split_wire_for_loop` leaves the wires that way (checked against saved projects); `_wire_pivot` makes the axle their line and the pivot the point where it meets the start/stop line (the start point, which is on the wire); `_implied_stop` is the stop point the mesh implies (`_p2` can be stale mid-move). A roll is a rigid rotation about the axle through the pivot of the mesh AND the start/stop points; **the object turns about its OWN origin, so the angle handed back is the roll composed AFTER the current angle (`q_roll (x) q0`, Q·R0), together with the new start point** — the old code's `q0 (x) q_roll` twisted the mesh about a vector in its own frame and dragged the stop point 1.7-6.6 mm off the wire (up to 14.7 mm of mesh error at large angles). With no wire on both sides (a project still loading its wires) there is nothing to roll about and `_resolve_collision` does nothing. **Rotate on Wire (user, 2026-10-25):** the context menu's "Rotate on Wire" (disabled without `can_roll_on_wire`) calls `start_wire_roll`, which selects the loop and arms `rotation_handlers.rotation_rings.WireRollRings` as its `_active_handler` and the canvas's `active_handler_obj`. `WireRoll` freezes the loop's pose (`begin_wire_roll`: axle and pivot from `_wire_points`/`_wire_pivot`, the angle's matrix, the start point) and `pose(degrees)` is the rigid roll from it (`R' = Q R0`, start carried round the pivot); `roll_to` writes it through `_apply_resolved` and re-derives the stop point. No collision search runs on it: the roll the user drags is the roll the loop gets. The ordinary three-axis gizmo still turns the loop about its CENTROID (`centroid` property; `_update_angle`), and its rings are centered on that centroid, not on `position` -- see `rotation_handlers/editor_3d/MAP.md`. `begin_move_session` (called by the add handler and the drag/rotate handlers, paired with `end_move_session`) gathers every candidate — visible wires other than the two attached ones, other loops, markers on the attached wires — as boxes (a wire is one box per section via `Wire.segment_obbs`, tagged `KIND_CYLINDER` because a section's mesh is a cylinder; anything else its pool `obb`, tagged `KIND_BOX`) and builds ONE `wire_service_loop_search.LoopSearch` from them plus the loop's own mesh (`self._vbo.vertices`, the first `vertex_count * 3` floats of the packed data); `_resolve_collision` only works out the axle, pivot and slide limits and applies what `LoopSearch.search` returns (the new angle and start point). Reached outside a session (the `__init__` call) it builds a one-shot session. **Do not put a pose test back in Python**: adding a loop used to freeze the app (mesh-vs-mesh test, ~6 s per overlapping pose, then ~610 us per pose in numpy because `Angle.from_quat` alone is ~240 us); see MEMORY.md's "Adding a wire service loop froze the app".

#### wire_service_loop_search.pyx

Hand-written Cython (`LoopSearch`) holding the whole roll/slide search in C: quaternion twist and matrix, no `Angle`/numpy per pose (~0.55 us per box-only pose). **Two stages per candidate** (the user's design, 2026-10-25): (1) the HIT LIST: an oriented-box separating-axis test behind an axis-aligned reject (conservative, a coil does not fill its box); (2) the MESH stage, only for boxes that overlap: the loop's own mesh vertices (~30,000, indexed once in a cached 10x10x10 grid) against the candidate's real shape — `KIND_CYLINDER` (a wire section's mesh IS a 360-sided cylinder, so the exact cylinder inscribed in its box along the box's z axis, flat ends) or `KIND_BOX` (another loop or a marker: its own box, so tight on our side and still conservative on theirs). A candidate collides only when BOTH stages say so; a wire passing through the coil's hole touches no vertex and is clear. Built once per move session: `LoopSearch(boxes, kinds, local_obb, scale, loop_vertices)`; `search(p1, p2, pivot, axis, q0, t0, pos_limit, neg_limit, slide_step, roll_deg, slide_roll_deg)` takes the per-call inputs (the loop's current start/stop points and angle, the wire's axis and the pivot) and returns `(t, theta_deg, (w, x, y, z), start, stop)` or `None`: the NEAREST clear roll at the current spot in `roll_deg` steps (+k then -k outward; both clear at one distance: less contact at the first step wins, equal: +), else the same scan at each slide position in the coarser `slide_roll_deg` steps, closest slide wins. `pose_at` is the pure maths (pose after a roll and slide) for checking; `is_clear`, `contact` and `boxes_overlap` (stage one alone) exist for diagnosis. The rotation is documented in the module docstring ("Rotation: about the WIRE, through the pivot"). The loop's scale must be uniform (a cylinder has to stay a cylinder in the loop's frame). Its rotation matrix is `Angle.as_matrix_numpy`'s column-vector `R` (the loop's box axes are its COLUMNS). It has NO pure-Python fallback (the user's "No fallback paths" rule): `wire_service_loop.py` imports it directly, so the compiled `.pyd` must sit beside it (gitignored; rebuild after every edit, recipe in MEMORY.md's "Cython extensions" entry) and it is registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS`. A box that is flat in any axis falls back to its own axis-aligned bounds (and to `KIND_BOX`); touching counts as a collision. **The real boxes are FLOAT32** (`Point.as_numpy` and `Angle.as_matrix_numpy` are float32, so `Wire.segment_obbs` computes in float32): a `KIND_CYLINDER` box is square across x and y only to float32 noise (2e-6 mm at 50 mm from the origin, 8e-5 mm at 2 m), so the constructor accepts a difference of up to 1% of the radius (radius = the mean of the two widths) and raises `ValueError` beyond that. A tolerance tighter than that raised on the first real run.

#### wire_service_loop_search.pyi

Type stub for the compiled module above (`KIND_BOX`/`KIND_CYLINDER`, `LoopSearch.__init__`/`search`/`pose_at`/`is_clear`/`contact`/`boxes_overlap`).

## FOLDERS

#### mixins/

Wire-type mixin only; see `mixins/MAP.md`. CODEBASE_MAP.md additionally lists `angle`/`move` mixins here — neither exists; see the drift note in `objects/MAP.md`.
