## FILES

#### __init__.py

Package init for the schematic (2D) renderable views — same one-file-per-part layout as `objects_3d`, minus the wire-type mixin (no `mixins/wire_type.py` equivalent here) and minus `circuit.py` (circuit has no schematic view, only a peg-board one, confirmed via the real file listing). This directory is named `objects2d` in CODEBASE_MAP.md — the real on-disk name is `objects_schematic`; see `objects/MAP.md` for the full rename note. See `objects/MAP.md` for the circular-import trap and the rigid-child positioning convention, both of which apply here too (`objects_schematic` -> `ui.widgets` is part of the pre-existing import cycle that forces the app to import `ui` before `objects.housing`).

#### auto_arrange.py

Force-directed auto-layout for the schematic view — `_force_layout`, `_edge_weights`, `_min_separation`, `_snap_and_resolve`, sizing helpers (`_footprint_half_extent`, `_node_center`, `_average_od_mm`) that space housings/terminals apart based on wire bundle thickness between them. Not part of the base-class hierarchy — a standalone layout pass over `Project`.

#### base_schematic.py

`BaseSchematic(BaseVar)` — the base schematic object; see `objectsvar/MAP.md` for what's inherited vs. defined here (`drag`, `handle_interaction`, `_handle_rotation_interaction`, `render_handler`, `is_visible`, `_selected_color`). Also holds module-level helpers `box_hit_test`, `_quat_about_y`, `_rotate_about_y` for the schematic plane's 2D-rotation-about-Y conventions.

#### boot.py

One file per harness part, a `BaseSchematic` subclass taking `(parent, db_obj)` — same shape across this whole directory.

#### bundle.py

Present here per the one-file-per-part layout, but bundles are 3D + peg-board only per `BUNDLE_DESIGN.md` — confirm current scope before assuming schematic bundle rendering is real.

#### bundle_layout.py

Companion to `bundle.py`, same caveat about actual schematic scope.

#### cable.py

`Cable(BaseSchematic)` (NEW 2026-11-08): an inert placeholder, built like `circuit.py` (no VBO, angle, position, scale or material, not visible), never drawn or picked. A cable is not in the schematic (each conductor is, see `cable_conductor.py`), but it can be the selected object while the schematic editor shows (object browser, or a selection made in the 3D editor), and every canvas must hold its selected object: without a view the canvas logged "the selected Cable has no view in the editor2d canvas".

#### cable_conductor.py

`CableConductor(Wire)` (NEW 2026-11-06, step 8): the schematic view of a cable conductor. A cable is never in the schematic, and neither are its leads (`is_visible2d` false, never added to the canvas): a conductor is ONE ordinary schematic wire from the terminal or splice its start lead ends on to the one its stop lead ends on, with the ordinary single list of 2D waypoints (the row's `pjt_wire_paths` rows, view `2d`), so this is the schematic wire view as it is. Its parent is the conductor's `objects/cable_conductor.py` `ConductorRun`, not a `Wire` facade. Own menu (`ConductorMenu`: Select, Properties): a conductor cannot be split, branched or deleted from the schematic. Interior waypoint handles (`WireLayout`) are made by the router as for any wire; dragging one is untested (a handle finds its wire through `project.get_wire`, which does not know a conductor).

#### cavity.py

Per MEMORY.md ("schematic cavity names all rendered at the housing's own position"), a cavity's schematic name-label position historically collapsed to the housing's own position for cavities created via `PJTHousing.update_cavities()`'s older per-cavity insert path (now fixed — see MEMORY.md for the full root cause/fix). Also: don't read 2D position off `Position2DMixin.position2d`'s `.y` and expect the real "y" axis — that was a pre-2026-09-24 trap, since fixed at the schema level (`pjt_points2d` now has a real `z` column); see MEMORY.md for history if old code/comments still reference the `.y`->`.z` remap.

#### circuit.py

The 2D schematic editor's view of a circuit: an inert placeholder (`BaseSchematic` built with no vbo/angle/position/scale/material, never visible, `obb` None), built like a `Note` that was never placed in this editor. A circuit has nothing to draw; the view exists so the canvas can hold the circuit as its one selected object (see `objects/circuit.py`). The mouse can not pick it. Added 2026-10-25. Its `set_selected` is overridden (2026-10-25): deselecting also calls `Circuit.deselect_in_editor()`, so the circuit editor stops showing the circuit's row as selected (it clears the row only when that row is the selected one, otherwise it does nothing).

#### cover.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### cpa_lock.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### generic.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### housing.py

Schematic housing rendering, same `BaseSchematic(parent, db_obj)` shape as the rest of this directory.

#### note.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### project_model.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### seal.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### section.py

Inert placeholder for the concentric section widget (NEW 2026-10-25) -- it has no schematic presence; same shape as this directory's `table.py`.

#### splice.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### table.py

`Table(BaseSchematic)` — the floating wire table's schematic-view rendering; same class name as the 3D/peg-board `Table`, not shared code.

#### terminal.py

Explicitly built to cope with `cavity is None` — hosts the free-standing (cavity-less) terminal rendering as a shared flat ring VBO, not a separate view class (`harness_designer/ui/widgets/MAP.md` DESIGN NOTES "Empty-space right-click menus"); **NOT yet run in the GUI**.

#### tpa_lock.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### transition.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### wire.py

Wire family; schematic has no waypoints — a wire's end is simply the terminal's `wire_position2d`.

#### wire_layout.py

Part of the wire family.

**Deleting a cable (2026-11-09):** `_reconnect_wires` refreshes the route registration only if the wire row has a view of this kind (`view is not None`): deleting a cable deletes its conductors' layouts, and a conductor row's object has no such view (it raised `'NoneType' object has no attribute 'refresh_waypoints'`).

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.

## FOLDERS

#### mixins/

Empty package (`__init__.py` only) — see `mixins/MAP.md` for why.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.

#### 2D schematic scope
Mechanical housing accessories — boot, cover, cpa_lock, tpa_lock, seal — never get a 2D schematic representation. Confirmed 2026-07-25: "those are not going to have any visuals as they are mechanical accessories and should not be displayed in a wiring schematic."

**Why:** A wiring schematic shows electrical/logical connectivity, not physical hardware.

**How to apply:** `objects/objects2d/boot.py`, `cover.py`, `cpa_lock.py`, `tpa_lock.py`, `seal.py` stay on the inert legacy contract (`Base2D.__init__(..., None, None, None, None, None)`) permanently — not a "not yet done" gap.

Still genuinely open (not yet decided): whether `transition.py`, `bundle.py`, `bundle_layout.py`, `wire_service_loop.py` (routing/grouping, not accessories) and `note.py` (already has real position/angle wired up, needs a VBO — `objects3d/note.py` is a ready-made reference) get real 2D visuals. Ask before building those.
