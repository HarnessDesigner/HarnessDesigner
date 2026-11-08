## FILES

#### __init__.py

Package init for the scene-objects layer: one wrapper class per harness part type (`ObjectBase` subclasses), each owning a 3D, schematic, and/or peg-board renderable view object, plus any child wrappers (e.g. a housing owns its cavities, tpa/cpa locks, seal, cover, boot). This is the layer that sits between project-db rows (`database/project_db/pjt_*.py`) and the per-view renderable objects — see CODEBASE_MAP.md's "Same-name modules: layer relationships & loading order" section for the full pipeline (`create_database` -> `global_db` -> `project_db` -> `objects` wrapper -> per-view renderable). Note CODEBASE_MAP.md's naming drift: it calls the per-view sibling packages `objects3d`/`objects2d` (no underscore, "2d" not "schematic") — the real on-disk names are `objects_3d`/`objects_schematic`. It also describes an `angle`/`move` mixin pair under each of those packages' `mixins/` that doesn't exist on disk: `objects_3d/mixins/` has only `wire_type.py`, and `objects_schematic/mixins/` is empty (`__init__.py` only) — that logic was folded directly into `Base3D`/`BaseSchematic` themselves, which override `_update_angle`/`_update_position` directly rather than via a separate mixin. A further undocumented fact worth real weight: `Base3D`, `BaseSchematic`, and `BasePegboard` all share one common ancestor, `objectsvar.base_var.BaseVar` (confirmed via `dep_trace.py --overrides`) — CODEBASE_MAP.md mentions `objectsvar` only in passing as a `ShaderProgram` consumer, not as this shared foundation.

#### bom.py

Bill-of-materials support: `BomLineItem`, `HousingTreeNode`, `WireCutRow`, `BundleCutRow`, `format_length()` (mm -> `70.0in (5'10")(1778mm)`, feet/inches rounded to the nearest inch), `resolve_wire_icon()`. Not a scene-object wrapper — shared data-shaping for BOM views built from the scene graph.

#### boot.py

One-file-per-part wrapper, same shape as `housing.py` — `ObjectBase` subclass fanning out to whichever of `objects_3d`/`objects_schematic`/`objects_pegboard` the part has a view in. Boot design (shape/geometry, whether/how it bends to follow the routed harness) lives in `BOOT_DESIGN.md` at the repo root — read it in full before touching boot code, and add new decisions there, not here.

#### bundle.py

Wrapper for bundles; 3D + peg-board only, no schematic view (`harness_designer/handlers/MAP.md` DESIGN NOTES "Bundles: design lives in BUNDLE_DESIGN.md"). Placement/cross-view reaction rules are in `BUNDLE_PLACEMENT.md`; the rest of the bundle design (create-from-wire, extend, shared-waypoint, 1-to-1 layout spec) is in `BUNDLE_DESIGN.md` — read both before touching bundle code and add new decisions there.

#### bundle_layout.py

Companion to `bundle.py` — same 3D + peg-board-only scope and same `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md` design docs.

#### cable.py

`Cable(ObjectBase)` (NEW 2026-11-05): a placed cable, i.e. a shielded wire part or one with more than one conductor (`Wire.is_cable`). A 3D view only (`obj3d`; the peg-board view comes with the peg-board work, and a cable is never in the schematic, where each conductor is drawn as its own wire). `start_sibling` / `stop_sibling` are always `None`: a cable's ends are free, a terminal or splice attaches to a conductor after the cable is split. `__init__` makes the live `Point` of every conductor's two end points so they follow the cable's ends. `delete` removes the view, the project registry entry and the row (which deletes its conductors). Placed through `objects_3d.wire.Wire._start_free_space`, which hands a cable part to `objects_3d.cable.Cable.start_add_cable`. **Split (5a + leads, 2026-11-05):** `is_split(start)`, `max_split_mm(start)` (the end segment's length less 2 mm, so no trunk waypoint is cut off), `split_end(start, distance)` (sets `start_split_mm` / `stop_split_mm`; for each conductor detaches its end point from the cable's end and moves it to its fan-out place, makes a split point on the plane, and makes the LEAD: an ordinary `pjt_wires` wire, `cable_conductor_id` set, from the end point to the split point, with a `Wire` facade added to the project), `lead_wires(start)`, `can_join(start)` (nothing attached to a lead's free end) and `join_end(start)` (deletes the leads and split points, re-attaches the end points as children of the cable's end). `delete` deletes the leads first. **Fan-out order (2026-11-06):** `fan_order(start)` (conductors by `start_order` / `stop_order`, ties by `idx`), `can_reorder(start)` (= `can_join`: nothing on a lead's free end), `conductor_label` and `set_fan_order(start, ordered)` (validates, stores the orders, and on a split end moves each end point to its new place); an unsplit end only stores the order, which the first split uses. `conductor_object(row)` / `conductor_objects`: the `CableConductor` junction of each conductor (stage 3); `split_end` attaches each new lead's split end to it, `join_end` needs nothing (a deleted lead removes itself from its junction). `__init__` calls the view's `reload_splits` when a loaded cable is split. Not run in the app. `ObjectBase.is_cable` is its type flag. **Step 4:** `can_roll()` / `set_roll(degrees)` (a ribbon, neither end split; writes `roll_deg` and redraws) and `can_reorder` is False for a ribbon (its conductors fan out in pin order). **Step 7:** `reload_looks()` (trunk and every lead redrawn from the conductor rows, after a colour edit or once the conductors exist), `refresh_browser()` (the object browser lists the conductors and leads again; called after a split, a join, the placement session finishing and, for every cable, at the end of the project load's sibling reconcile, when the leads are linked), `conductors_made()` (what the placement session calls). `conductor_object` now also binds the node to the row (`conductor.set_object(node)`), so the circuit listing and the browser find it from the row. **Peg board (step 8, 2026-11-06):** the facade has `objpegboard` (`objects_pegboard/cable.py`, built beside `obj3d`); `reload_looks` redraws it and the leads' board views. A cable placed before the board knew cables is seeded onto the board as the project loads (`needs_seed` / `seed_from_3d`). `split_end` also lays the split out FLAT on the board (`objpegboard.split_positions` / `fan_out_positions`): each conductor gets a board split point (`start_` / `stop_split_point_pegboard_id`) and its board end point, and the lead's board ends are those two; when the cable has no length on the board (`_board_ready` false) the board half is skipped and the lead keeps its points at the origin. `_sync_split_points`, `set_fan_order` and `join_end` keep the board points in step (`_move_board_ends`, `_move_board_split_points`; join deletes the board split points and leaves the conductors' board ends to be put in place at the next split). **A point's write-back to its row is a weak callback: a move only persists while something holds the row** (the lead's `db_obj` does, once asked for the point; the move code keeps the row in a local while it moves). **Split-end markers (2026-11-07):** `split_end` (and `__init__` for an already split cable) calls `_make_split_markers`, which draws a PSEUDO layout (`database/project_db/pseudo_wire_layout.py` `PseudoCableSplitLayout`, wrapped in the `WireLayout` facade the way snap probes are) at each conductor's split point, where its lead meets the trunk: one per conductor in 3D and one on the board where the split is laid out there. They are not rows (the split point is already stored), are not registered with the project, are sized and coloured as the conductor (`conductor.part.od_mm` / `color.ui`, never the stripe) and are not pickable (`_pick_priority = -1`). `join_end` and `delete` call `_drop_split_markers` (`mainframe.remove_object`). Not run in the app. **Drag (2026-11-07):** a left-down on the selected cable starts `drag_handlers/editor_*/cable.py`; after each step `follow_drag(view, before_start, before_stop)` lays the split points of a split end on the new split plane again (`_sync_split_points` for 3D, `_move_board_split_points` for the board) and `_carry_free_leads` moves the free end of each lead of that end by the distance the cable's end moved, except a lead with a terminal or splice on it (it stays; the lead stretches). An end that is not split needs nothing (the conductors' end points are children of it). A waypoint drag that turns the end segment re-lays the split plane but does not re-orient the fanned-out free ends. Dragging in one view does not change the other (the board is not re-seeded). `_sync_split_points` now keeps each split-point row referenced while it moves. Not run in the app.

#### cable_conductor.py

`CableConductor(ObjectBase)` (NEW 2026-11-06, 5b stage 3): the JUNCTION of one cable conductor's two leads, modelled on `wire_service_loop.py` (two ends, a wire on each). It is what `Wire.start_sibling` / `stop_sibling` return for the split end of a lead (the lead's stop point is the conductor's split point). It has NO view (`obj3d` / `objschematic` / `objpegboard` all None), no tree item and no registry entry: the trunk is drawn by the cable and the leads by their own wires, so it is only the sibling-graph node. `start_sibling` is the lead at the cable's start end, `stop_sibling` the one at its stop end (`None` while that end is not split); `wires`, `set_lead(start, wire)`, `replace_wire`, `remove_wire` (called by `Wire.delete` and `wire_topology`), `delete()` only lets go of the leads (its row goes with the cable). Made and owned by `Cable.conductor_object(row)` / `Cable.conductor_objects` (made the first time they are asked for); linked by `Cable.split_end` and, on a project load, by `Project._reconcile_wire_sibling_graph`. `ObjectBase.is_cable_conductor` is its type flag. Not run in the app. **Stage 4:** the row behind it is a circuit member and the junction the circuit walk crosses (see `database/project_db/MAP.md`, `pjt_circuit.py`); `Wire.trace_run` adds its trunk's length and resistance. **Step 7:** `set_selected` is overridden: the node has no view in any editor, and the canvases hold objects that do, so selecting it sets `mainframe._selected_obj`, tells the object browser and (a timer later, queued before whatever is selected next) the object editor, which then shows the wire control (a conductor is a wire row; its Part tab is the cable's catalog wire, with the Conductors tab). It is selected from the object browser (a conductor item under its cable) or from a circuit's Cable Conductors group; it cannot be picked in a 3D view. **Schematic (step 8, 2026-11-06):** `ConductorRun(ObjectBase)` is the conductor as the schematic draws it, ONE wire from the terminal/splice the start lead ends on to the one the stop lead ends on (`start_sibling` / `stop_sibling` are THOSE, not the leads; `is_connected`; `route_prefix`; `db_obj` the conductor row, whose 2D end points are the leads' own, so the line follows the terminals; `objschematic` is `objects_schematic/cable_conductor.py`). It is not a `Wire` (`is_wire` false), so the editors do not treat it as one, but it answers what `wire_routing` asks of a wire, so `on_wire_attached` / `reroute_wire` work on it unchanged. `CableConductor.refresh_schematic(route)` makes it when both leads end on a terminal or splice and drops it (`detach`: its waypoints, handles and view; the row stays) when they no longer do; asked by `reroute.on_wire_attached` (a lead attached: route), `Wire.set_sibling(None)` and `Wire.delete` (a lead cut free or deleted), and for every conductor at the end of `Project._reconcile_wire_sibling_graph` (a load: keep the stored path). `ConductorRun.delete()` only takes it out of the schematic. Not run in the app (`schematic_conductor_test.py` covers the node, the run and the hooks on stand-ins). **Gap review (2026-11-07):** the node's `objschematic` is its run's view (so code that finds a wire's object from its row, e.g. `objects_schematic/wire_layout.py`'s handle cleanup, reaches it); `Project.schematic_wires` = `wires` + the drawn runs (`Cable.drawn_conductor_objects`), read by `routing.py` (obstacles, batch skips), `reroute.sweep_for_overlaps`, `auto_arrange.py` and the lane alignment of `drag_handlers/editor_schematic/wire.py`, so a conductor is an obstacle and is rerouted like a wire. Other `project.wires` loops (splice placement, snapping) deliberately do not include it: a conductor cannot be split or snapped to.

#### cavity.py

Wrapper for a housing's cavities. See the Rigid-child positioning convention note below — a cavity's world position/angle must come from its *immediate* parent housing, never re-derived from further up the chain.

#### circuit.py

`Circuit(ObjectBase)` — the wrapper for a `pjt_circuits` row: a logical grouping, not a placed part. It has an inert placeholder view in every editor (`objects_3d/circuit.py`, `objects_schematic/circuit.py`, `objects_pegboard/circuit.py`; added 2026-10-25, built like a `Note` that was never placed there: no vbo/position/angle/scale/material, not visible, `obb` None). They exist so each canvas can hold the circuit as its one selected object: `MainFrame._set_selected` hands it to every canvas, and a click elsewhere deselects it through `MouseHandlerBase.on_left_up` -> `Circuit.set_selected(False)`, which clears the highlight. A circuit can NOT be picked with the mouse (`gl.object_picker` skips a view with no `obb`), `CanvasBase.add_object` and every `center_on_object` skip it (no position), so it is only ever selected from the circuit editor or the object browser. Before 2026-10-25 it had no views, and selecting one made `CanvasBase._draw_scene` dereference `None` and abort the process. `highlight(flag)` gives every wire, service loop, splice and terminal in the circuit the `materials.Circuit` material across all three editors (`identify()`, a material override: the members are NOT selected), or clears it with `identify(None)`, and `set_selected(flag)` calls it; `delete()` deselects first; `menu_ops.trace_circuit` uses the same method. `deselect_in_editor()` (2026-10-25) tells the circuit editor the circuit was deselected (`EditorCircuitPanel.deselect_circuit`); the circuit's three views call it from their `set_selected(False)`, and it is a no-op when the editor does not exist yet or its selected row is not this circuit's. `delete()` follows `Note.delete()` and detaches the circuit's members rather than deleting them (every member's `circuit_id` becomes NULL, which the four member tables allow; the circuit editor's right-click Delete Circuit calls it after a Yes/No). Create one with `Project.create_circuit()`, never by constructing it directly after load. The file's remaining ~600 lines are a commented-out `WireInfo` class (electrical/AWG logic), kept for a later port.

#### cover.py

One-file-per-part wrapper, same `ObjectBase(parent, db_obj)`-fanout shape as `boot.py`/`seal.py`/etc.

#### cpa_lock.py

One-file-per-part wrapper, same shape as `cover.py`/`tpa_lock.py`.

#### generic.py

Catch-all one-file-per-part wrapper shape, used for part types without a dedicated file of their own.

#### housing.py

The most heavily-loaded wrapper: owns cavities, tpa/cpa locks, seal, cover, and boot, across all three views. `Housing.__init__` constructs this housing's `Cavity` wrappers **synchronously** (not deferred via `CallLater`) — see MEMORY.md's 2026-09-04 fix entry for why a deferred construction raced against the 3D model's synchronous download-complete callback and left a freshly-added housing's cavities unselectable until project reload. **Circular import trap** (`harness_designer/objects/objects_3d/MAP.md` DESIGN NOTES, "Objects3D context menu architecture"): `objects/<type>.py` modules like this one import their `objects_3d/<type>.py` sibling at module level, `handlers` imports `objects`, and `ui` imports `handlers` — so `objects_3d` modules must import `handlers`, `ui.dialogs`, and sibling `objects` classes **lazily, inside callbacks**, never at module level. Importing `harness_designer.objects.housing` before `harness_designer.ui` also fails on a separate, pre-existing cycle via `objects_schematic` -> `ui.widgets`; the app always imports `ui` first.

#### note.py

One-file-per-part wrapper, same shape as `generic.py`.

#### object_base.py

`ObjectBase` — the base wrapper class every per-part wrapper derives from. Holds the view membership flags (`is_in_3dview`/`is_in_2dview`/`is_in_pegboardview`), selection state (fanned out to whichever views the object is in), angle-lock, delete/close, and the object-browser tree-item binding. `Base3D`/`BaseSchematic`/`BasePegboard`'s `.parent` points back to the owning `ObjectBase` — context menus receive the *view* object as `self.selected`, so `ObjectBase`-level ops (select, clone, rotate) must go through `.parent` (`harness_designer/objects/objects_3d/MAP.md` DESIGN NOTES, "Objects3D context menu architecture").

#### pegboard_table.py

`PegboardTable(ObjectBase)` — the wrapper for a floating wire table, still named for its DB table; the real peg-board-view rendering lives in `objects_pegboard/table.py`'s `Table`.

#### pegboard_section.py

`PegboardSection(ObjectBase)` (NEW 2026-10-25) -- the facade for a concentric section widget (one per `pjt_pegboard_sections` row, i.e. one per concentric); builds `objpegboard` (`objects_pegboard/section.py`, the real one) and the inert `obj3d` / `objschematic`, then `mainframe.add_object(self)`. `delete()` deletes the views, then the row. The classmethod `show(mainframe, concentric, anchor, obstacles)` is how a widget appears: it makes the row at the nearest free spot to `anchor` (`table_placement.find_free_position` returns a rectangle's CENTRE, and the widget is drawn from its LEFT edge, so the stored X is the centre minus half the width) or un-hides the user-closed one where it was, and builds the facade only if this session has none yet. Built by `Project.__init__` for every existing row (a function-local import there, to dodge the import cycle: it reaches the `ui` package); an owner that creates a row builds the facade the same way. `ObjectBase.is_pegboard_section` is the matching flag.

#### project.py

**Cables (2026-11-05):** the project holds `_cables` beside `_wires`: `add_cable` / `delete_cable` / `get_cable` / `cables`, loaded from `pjt_cables` right after the wires, torn down and deleted with them. `Project` — owns the whole in-memory scene graph for a loaded project; imports (and is imported by) every per-part wrapper module. Its loader deliberately loads every `PJTCavity` row before any `PJTHousing` row (comment at `project.py:310-321`) specifically to dodge a cavity-construction-ordering race — see the housing/cavity entries in MEMORY.md. Object creation = insert into `project.ptables.pjt_*_table`, wrap in the matching `objects/<type>.py` class, then `project.add_<type>(obj)`; deletion = `project.delete_<type>(db_id)` (pops the registry + deletes the db row) plus `mainframe.remove_object(parent)` — skipping either half leaves a dangling registry entry or a zombie render. Circuits follow the same trio (`add_circuit`/`delete_circuit`/`get_circuit`), are swept at the end of `Project.delete()` (after every member is gone), and also have `create_circuit()` (insert + wrap + register in one call) and `merge_circuits(keep_id, drop_id)` (moves the members, then deletes the emptied circuit's object, browser node and row). After the bundles and transitions are loaded it also builds a `PegboardSection` for every `pjt_pegboard_sections` row (not counted in the stored object count).

#### project_model.py

Wrapper for the project's own loaded 3D model (as opposed to a catalog part) — set via "Add/Edit Project Model" (`ui/dialogs/project_model_dialog.py`). Note it has no position/scale/angle columns of its own today; `objects_3d/project_model.py` hardcodes the model at the origin (this file's DESIGN NOTES, "Empty-space right-click menus" entry).

#### seal.py

One-file-per-part wrapper, same shape as `cover.py`/`boot.py`. Seal rendering for freshly-placed terminals participates in the Terminal delete/wire-detach/reconnect work described under `terminal.py` below.

#### splice.py

One-file-per-part wrapper, same shape as `generic.py`.

#### terminal.py

All three views; also imports `wire_routing/reroute.py` and `wire_layout.py`. Owns `detach_wires()` (deleting a terminal cuts every attached wire free in all three views) and the free-standing (cavity-less) terminal / reconnect machinery — both **built 2026-09-25 and NOT yet run in the GUI** (this file's DESIGN NOTES, "Terminal delete / wire detach / reconnect" and "Empty-space right-click menus + free-standing terminals"). Key facts carried from those entries: which wire point is the real attach point (`attach_position*`, 1/3 up from back) vs. an interior waypoint (`wire_position*`); the `free` flag (not `cavity is None`) is the discriminator for a genuinely free-standing terminal vs. a hidden placement preview about to be seated; known gaps include cut ends left behind if the housing moves after a delete, and an orphaned back-point row on the deleted terminal.

#### tpa_lock.py

One-file-per-part wrapper, same shape as `cpa_lock.py`.

#### transition.py

Wrapper for transitions. Model-building/rendering design (OCC boolean pipeline issues, the move to cylinder/sphere primitives, `offset`/`bulb_offset`/`angle` semantics) is in `TRANSITION_DESIGN.md`; placement/attaching stays in `BUNDLE_PLACEMENT.md`. Read `TRANSITION_DESIGN.md` in full before touching transition model-building code.

#### wire.py

`Wire.delete` releases the wire's `WireSlackHandler` first (2026-10-25; see `handlers/MAP.md`), so a deleted wire stops reacting to its points moving. All three views; imports `terminal.py`/`splice.py` (wire endpoints). `Point.db_id` is a string like `"1233d"`/`"1232d"` — strip the 2-char suffix to get the raw db id (MEMORY.md). `conductor_node` (2026-11-06): the `CableConductor` a lead's split end (stop) is attached to, else `None`; `set_sibling(None, ...)` and `delete` tell it (`refresh_schematic`) so a conductor with a lead cut free or deleted leaves the schematic.

#### wire_layout.py

Part of the wire family, all three views.

#### wire_marker.py

Part of the wire family, all three views.

#### wire_service_loop.py

Part of the wire family, all three views. `delete()` (2026-10-26) takes the loop out of its wire: it merges the two wires either side of it with `handlers.wire_topology.merge_wires_in_place` (ordered by which one ENDS at one of the loop's points, not by `start_sibling`/`stop_sibling`: `start_sibling` is the wire AFTER the loop, the one that starts at its START point, and `stop_sibling` the wire BEFORE it -- `Project._reconcile_wire_sibling_graph` sets them from the saved ids), deletes the two `WireLayout`s `split_wire_for_loop` put at the loop's points, then the loop. No point row is deleted. The old call passed `start_sibling` first to `merge_wires`, whose first argument must be the wire before, so the merged wire ran from the loop's start point to its stop point and lost both of the original wire's ends.

## FOLDERS

#### mixins/

Wrapper-level mixins shared across the view-agnostic `objects/<type>.py` modules (not the per-view renderables' own mixins). See `mixins/MAP.md`.

#### objects_3d/

The 3D renderable views. Named `objects3d` (no underscore) in CODEBASE_MAP.md — the real on-disk name is `objects_3d`. See `objects_3d/MAP.md`.

#### objects_pegboard/

The peg-board renderable views. See `objects_pegboard/MAP.md`.

#### objects_schematic/

The schematic (2D) renderable views. Named `objects2d` in CODEBASE_MAP.md — the real on-disk name is `objects_schematic`. See `objects_schematic/MAP.md`.

#### objectsvar/

`BaseVar`, the common ancestor of every per-view base class (`Base3D`, `BaseSchematic`, `BasePegboard`). See `objectsvar/MAP.md`.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Housing/cavity callback ordering bug (known, don't touch)
On a freshly added housing, `Housing2D.__init__` runs `_recompute()`/`_layout_children()` against zero cavities: `objects/housing.py`'s `Housing.__init__` builds `obj2d` first and cavity creation only happens later. No cavity/terminal gets a real `position2d`/`angle2d` from the housing's layout on first add, and `_bind_callbacks` binds to an empty list; reloading the project hides it. The user said he is building a "cavity added" callback himself, so do not fix this unless asked; if asked to work on 2D housing/cavity/terminal code, point to this note first. Possibly stale (2026-09-11): `update_cavities()` was rewritten that day, so re-verify against the current code. Its 3D sibling was fixed, see the next note.

#### Housing cavities and their 3D selection overlay (fixed 2026-09-04; rules)
- **Construct a housing's cavities synchronously in `objects/housing.py`'s `Housing.__init__`**, right after `self.objschematic` is assigned and strictly BEFORE `self.obj3d = _housing_3d.Housing(...)`, gated on `not project_load` (project load builds every `Cavity` earlier in its own pass, which deliberately loads all `PJTCavity` rows before any `PJTHousing`). Reason: `Model3D.load()` calls its callback synchronously when the model file is already on disk (the common case), so `_set_model` -> `match_cavity_surfaces()` ran before a deferred `CallLater` had built any `Cavity`, leaving `Housing3D.cavities` empty and the surface/marker maps built against zero cavities. `PJTHousingsTable.insert()` already batch-inserts the cavity rows before the facade exists and `cache_names()` (top of `__init__`) fills `_stored_cavities`, so the synchronous order is the intended design.
- **Do not reintroduce a deferred or "re-run `match_cavity_surfaces()` afterwards" shape.** Two such attempts broke click-to-drop placement because the add-housing handler constructs the facade the moment placement mode starts (a live drag preview), and re-entering the GL context (`with editor3d.context:`) from a `CallLater` mid-drag breaks it.
- **Cavity selection/overlay state lives on `Cavity3D`** (`objects/objects_3d/cavity.py`), derived from the generic `is_selected` / `render_selected_overlay()` path, not on `Housing3D`. `Cavity3D.render_selected_overlay` guards on `is_selected` only (its placeholder mesh is deliberately invisible, same reason `Wire`/`Bundle` override it); each `Cavity3D` owns its `_terminal_marker`/`_wire_marker` (`_CavityMarker`), and `Housing3D.match_cavity_surfaces()` assigns markers onto the cavity. The housing keeps only shared mesh primitives (`_picker`, `render_surface_overlay`, `render_marker_overlay(shaders, marker, color)` keyed by `id(marker)`, `_draw_overlay_faces`). `try_pick_cavity`/`on_surface_selected`/`_pick_marker` are pure lookups that resolve a ray to a `Cavity3D` (and set `_selected_is_wire_side` for `CavityMenu`'s "Add Wire" gating); selection goes through `set_selected`. A child selected by a ray test against a shared parent mesh should follow the same split.
- If a similar "works after reload, not on fresh add" report comes up for another housing-owned child (terminal, seal) with a one-shot mesh-analysis pass, check whether its rows are batch-inserted before its facade exists; if so construct the facade before the parent's `obj3d`.

#### Rigid-child positioning convention: offset @ parent.angle3d + parent.position3d
Any object positioned as a rigid child of another placed object (cavity-in-housing, terminal-in-cavity, anything relative to those) computes its world position from its IMMEDIATE parent's already-correct values:
```python
pos = local_offset
pos @= parent.angle3d
pos += parent.position3d
```
Never re-derive from further up the chain (grandparent position plus a catalog-local offset). Evidence: `PJTCavitiesTable.insert()` computes a cavity's `position3d` as `c_position3d @ h_angle3d; += h_position3d` (verified to 5 decimals against a real row), and `PJTHousing._update_angle3d/_update_position3d` move a terminal in the same rigid group as its cavity and set `terminal.angle3d` to mirror the cavity's exactly. `handlers/terminal_handler._male_terminal_position/_female_terminal_position` once re-derived from `pjt_cavity.part.position3d` and the housing, giving a silent, plausible-looking wrong position; they now use `pos @= pjt_cavity.angle3d; pos += pjt_cavity.position3d`. For any "plausible but wrong position" report, check this first.

#### Terminal delete / wire detach / reconnect (built 2026-09-25, NOT yet run in the GUI)
Deleting a terminal cuts every attached wire free in all three views (`objects/terminal.py` `Terminal.detach_wires`, called from `delete()`). Which wire point is which (`Terminal.add_wire`): `attach_position*` (crimp, 1/3 up from the back) is the wire's real start/stop; the terminal's `wire_position*` (back-face centre) and the cavity's `wire_position*` are interior waypoints, each with a `WireLayout`. Schematic has no waypoints: the wire's end is the terminal's `wire_position2d`.
- 3D/pegboard: trim back to the cavity's wire point if seated, else the terminal's own; the wire gets a NEW point row there as its free end; waypoints at/inside it lose their layouts; canonical rows are only untagged (`wire_id`/`idx` = None), never deleted (the cavity keeps its point); `parent_point_id` child rows are deleted. Which end = the wire's sibling graph, not proximity. Schematic: the wire keeps the stub-end location on its own new 2D point (the user wanted the cut at the shared point so a re-added terminal lands near it).
- `Terminal.reconnect_free_wires` (after every terminal placement) matches unattached wire ends within `_RECONNECT_TOLERANCE` (0.5, my guess) of the cavity's wire point or the terminal's back point, then `add_wire`s them and deletes the stale free-end rows. Free-end "Add Terminal" (3D + pegboard wire menus, `Terminal.add_at_wire_end`) places a cavity-less terminal with its back face on the wire end; `terminal_handler.reposition_from_model` has a cavity-None branch. The schematic menu is deliberately not done.
- Known gaps: moving the housing after a delete leaves cut ends behind; the deleted terminal's back-point row is orphaned; whether schematic terminal objects cope with `cavity is None` is unverified.
