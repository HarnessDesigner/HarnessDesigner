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

#### cover.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### cpa_lock.py

One file per harness part, same `Base3D(parent, db_obj)` shape.

#### generic.py

One file per harness part, same `Base3D(parent, db_obj)` shape — the catch-all for part types without dedicated geometry handling.

#### housing.py

Builds this housing's `Cavity` wrappers **synchronously** in `Housing.__init__` (not deferred) — see MEMORY.md's 2026-09-04 fix entry; a once-broken 3D cavity-selection-overlay/context-menu mechanism (`_surf_to_cavity`/`_cavity_markers`) has since been moved onto `Cavity3D` itself (see `cavity.py` above). Its legacy cavity-surface/marker overlay draw (`_draw_overlay_triangles`) used raw fixed-function GL (`glVertexPointer`/`glColor4f`) until the 2026-08-21 VBO/shader rewrite replaced it with `_draw_overlay_faces` — if an overlay/decal mysteriously stops drawing after a canvas change, see MEMORY.md "Legacy fixed-function immediate-mode GL calls silently render nothing under the new shader pipeline."

#### menu_ops.py

Shared context-menu callback helpers (`select_object`, `clone_object`, `delete_object`, `show_properties`, `start_handler`, `run_attached_handler`, `get_part_id`-style helpers) used by every part type's context menu. Must be imported lazily from call sites outside `objects_3d` itself — see the circular-import trap in `objects/MAP.md` (`objects/<type>.py` imports `objects_3d/<type>.py` at module level; `handlers` imports `objects`; `ui` imports `handlers`).

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

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.

## FOLDERS

#### mixins/

Wire-type mixin only; see `mixins/MAP.md`. CODEBASE_MAP.md additionally lists `angle`/`move` mixins here — neither exists; see the drift note in `objects/MAP.md`.
