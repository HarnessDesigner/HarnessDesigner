## FILES

#### __init__.py

Package init for the scene-objects layer: one wrapper class per harness part type (`ObjectBase` subclasses), each owning a 3D, schematic, and/or peg-board renderable view object, plus any child wrappers (e.g. a housing owns its cavities, tpa/cpa locks, seal, cover, boot). This is the layer that sits between project-db rows (`database/project_db/pjt_*.py`) and the per-view renderable objects — see CODEBASE_MAP.md's "Same-name modules: layer relationships & loading order" section for the full pipeline (`create_database` -> `global_db` -> `project_db` -> `objects` wrapper -> per-view renderable). Note CODEBASE_MAP.md's naming drift: it calls the per-view sibling packages `objects3d`/`objects2d` (no underscore, "2d" not "schematic") — the real on-disk names are `objects_3d`/`objects_schematic`. It also describes an `angle`/`move` mixin pair under each of those packages' `mixins/` that doesn't exist on disk: `objects_3d/mixins/` has only `wire_type.py`, and `objects_schematic/mixins/` is empty (`__init__.py` only) — that logic was folded directly into `Base3D`/`BaseSchematic` themselves, which override `_update_angle`/`_update_position` directly rather than via a separate mixin. A further undocumented fact worth real weight: `Base3D`, `BaseSchematic`, and `BasePegboard` all share one common ancestor, `objectsvar.base_var.BaseVar` (confirmed via `dep_trace.py --overrides`) — CODEBASE_MAP.md mentions `objectsvar` only in passing as a `ShaderProgram` consumer, not as this shared foundation.

#### bom.py

Bill-of-materials support: `BomLineItem`, `HousingTreeNode`, `WireCutRow`, `BundleCutRow`, `resolve_wire_icon()`. Not a scene-object wrapper — shared data-shaping for BOM views built from the scene graph.

#### boot.py

One-file-per-part wrapper, same shape as `housing.py` — `ObjectBase` subclass fanning out to whichever of `objects_3d`/`objects_schematic`/`objects_pegboard` the part has a view in. Boot design (shape/geometry, whether/how it bends to follow the routed harness) lives in `BOOT_DESIGN.md` at the repo root — read it in full before touching boot code, and add new decisions there, not here.

#### bundle.py

Wrapper for bundles; 3D + peg-board only, no schematic view (MEMORY.md "Bundles: design lives in BUNDLE_DESIGN.md"). Placement/cross-view reaction rules are in `BUNDLE_PLACEMENT.md`; the rest of the bundle design (create-from-wire, extend, shared-waypoint, 1-to-1 layout spec) is in `BUNDLE_DESIGN.md` — read both before touching bundle code and add new decisions there.

#### bundle_layout.py

Companion to `bundle.py` — same 3D + peg-board-only scope and same `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md` design docs.

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

The most heavily-loaded wrapper: owns cavities, tpa/cpa locks, seal, cover, and boot, across all three views. `Housing.__init__` constructs this housing's `Cavity` wrappers **synchronously** (not deferred via `CallLater`) — see MEMORY.md's 2026-09-04 fix entry for why a deferred construction raced against the 3D model's synchronous download-complete callback and left a freshly-added housing's cavities unselectable until project reload. **Circular import trap** (MEMORY.md, "Objects3D context menu architecture"): `objects/<type>.py` modules like this one import their `objects_3d/<type>.py` sibling at module level, `handlers` imports `objects`, and `ui` imports `handlers` — so `objects_3d` modules must import `handlers`, `ui.dialogs`, and sibling `objects` classes **lazily, inside callbacks**, never at module level. Importing `harness_designer.objects.housing` before `harness_designer.ui` also fails on a separate, pre-existing cycle via `objects_schematic` -> `ui.widgets`; the app always imports `ui` first.

#### note.py

One-file-per-part wrapper, same shape as `generic.py`.

#### object_base.py

`ObjectBase` — the base wrapper class every per-part wrapper derives from. Holds the view membership flags (`is_in_3dview`/`is_in_2dview`/`is_in_pegboardview`), selection state (fanned out to whichever views the object is in), angle-lock, delete/close, and the object-browser tree-item binding. `Base3D`/`BaseSchematic`/`BasePegboard`'s `.parent` points back to the owning `ObjectBase` — context menus receive the *view* object as `self.selected`, so `ObjectBase`-level ops (select, clone, rotate) must go through `.parent` (MEMORY.md, "Objects3D context menu architecture").

#### pegboard_table.py

`PegboardTable(ObjectBase)` — the wrapper for a floating wire table, still named for its DB table; the real peg-board-view rendering lives in `objects_pegboard/table.py`'s `Table`.

#### project.py

`Project` — owns the whole in-memory scene graph for a loaded project; imports (and is imported by) every per-part wrapper module. Its loader deliberately loads every `PJTCavity` row before any `PJTHousing` row (comment at `project.py:310-321`) specifically to dodge a cavity-construction-ordering race — see the housing/cavity entries in MEMORY.md. Object creation = insert into `project.ptables.pjt_*_table`, wrap in the matching `objects/<type>.py` class, then `project.add_<type>(obj)`; deletion = `project.delete_<type>(db_id)` (pops the registry + deletes the db row) plus `mainframe.remove_object(parent)` — skipping either half leaves a dangling registry entry or a zombie render. Circuits follow the same trio (`add_circuit`/`delete_circuit`/`get_circuit`), are swept at the end of `Project.delete()` (after every member is gone), and also have `create_circuit()` (insert + wrap + register in one call) and `merge_circuits(keep_id, drop_id)` (moves the members, then deletes the emptied circuit's object, browser node and row).

#### project_model.py

Wrapper for the project's own loaded 3D model (as opposed to a catalog part) — set via "Add/Edit Project Model" (`ui/dialogs/project_model_dialog.py`). Note it has no position/scale/angle columns of its own today; `objects_3d/project_model.py` hardcodes the model at the origin (MEMORY.md, "Empty-space right-click menus" entry).

#### seal.py

One-file-per-part wrapper, same shape as `cover.py`/`boot.py`. Seal rendering for freshly-placed terminals participates in the Terminal delete/wire-detach/reconnect work described under `terminal.py` below.

#### splice.py

One-file-per-part wrapper, same shape as `generic.py`.

#### terminal.py

All three views; also imports `wire_routing/reroute.py` and `wire_layout.py`. Owns `detach_wires()` (deleting a terminal cuts every attached wire free in all three views) and the free-standing (cavity-less) terminal / reconnect machinery — both **built 2026-09-25 and NOT yet run in the GUI** (MEMORY.md, "Terminal delete / wire detach / reconnect" and "Empty-space right-click menus + free-standing terminals"). Key facts carried from those entries: which wire point is the real attach point (`attach_position*`, 1/3 up from back) vs. an interior waypoint (`wire_position*`); the `free` flag (not `cavity is None`) is the discriminator for a genuinely free-standing terminal vs. a hidden placement preview about to be seated; known gaps include cut ends left behind if the housing moves after a delete, and an orphaned back-point row on the deleted terminal.

#### tpa_lock.py

One-file-per-part wrapper, same shape as `cpa_lock.py`.

#### transition.py

Wrapper for transitions. Model-building/rendering design (OCC boolean pipeline issues, the move to cylinder/sphere primitives, `offset`/`bulb_offset`/`angle` semantics) is in `TRANSITION_DESIGN.md`; placement/attaching stays in `BUNDLE_PLACEMENT.md`. Read `TRANSITION_DESIGN.md` in full before touching transition model-building code.

#### wire.py

`Wire.delete` releases the wire's `WireSlackHandler` first (2026-10-25; see `handlers/MAP.md`), so a deleted wire stops reacting to its points moving. All three views; imports `terminal.py`/`splice.py` (wire endpoints). `Point.db_id` is a string like `"1233d"`/`"1232d"` — strip the 2-char suffix to get the raw db id (MEMORY.md).

#### wire_layout.py

Part of the wire family, all three views.

#### wire_marker.py

Part of the wire family, all three views.

#### wire_service_loop.py

Part of the wire family, all three views.

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
