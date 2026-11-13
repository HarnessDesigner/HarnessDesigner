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

**Empty cavity marker (2026-11-12, user):** a cavity with no terminal is drawn with the wire stub and the "(" a seated terminal has (from the same `CavityGeometry`: `bracket_position`, `cylinder_start`, `cylinder_stop`) and a RED X at the end of the stub, meaning nothing can be connected there. `_render_label` calls `_render_empty_marker` while `_empty` (set in `__init__`, kept by `_on_terminal_changed`, which the terminal's `cavity_id` setter fires through the synthetic `terminal_id` tag); `_marker_pieces` works the world places out again only when the housing's position / angle changed, `_marker_world` uses `point_at_180` at exactly 180 degrees (a closing bracket instead of the opening one there, as `Terminal` does); the glyphs (`_glyph`) are shared by every empty cavity. A seated terminal draws its own, so the marker goes while one is seated. Stand-in test `twist/empty_cavity_test.py` (the geometry only); NOT seen in the app.

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

**`refresh_size()` (2026-11-11):** the rectangle's size and the corner label are read from `db_obj.stack_geometry` once, in `__init__`; a housing placed before its part had cavities was a very thin rectangle for good. `PJTHousing._after_cavities_created` calls this after `update_cavities` filled the cavities in: the scale (a bound point, so the OBB / AABB follow) and the label position are set again. NOT run in the app.

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

**Shield ring (2026-11-12, user's design; replaces the dot and the wire-fitted ellipse):** a solder sleeve is drawn as a DASHED ELLIPSE ACROSS the shielded wires (`SHIELD_DASH_THICKNESS` 0.3 of a wire: thin) and nothing else: NO dot. Its state is stored on the sleeve's row (`wire_routing/shield_ring.py`): the connected narrow end is the splice's own `point2d` (where the black shield wire, the pigtail, ends), `ring_dir`, `ring_size`, `ring_hard`; `reload_ring()` re-reads it and redoes the view's bounds (the ring's box, which the router reads as an obstacle, so other wires route around it). Picking: `hit_test_step2/3` hit only the two narrow ends (`_tip_at`, `HANDLE_FACTOR` splice diameters), so wires inside the box are not hidden. The user cannot move the ring as a whole; a press on the CONNECTED narrow end of a selected ring drags it (`_RingDrag` index 0 -> `shield_ring.move_ring`: hard set there, the shield wire is routed to it, the cable's wires are routed through it), a press on the FAR end sizes it (index 1 -> `resize_ring`: longer is wider, long : short = 3 : 1, also hard set). The ring goes AROUND the wires (user, 2026-11-12): `_pieces` raises the dashes of the half on the far side of the wires from the housing (`shield_ring.beyond_sign`) clear above the wires (`SHIELD_OVER_GAP`, drawn on top: the canvas is top-down with depth testing) and leaves the other half on the wires' plane, where they cover it. NOT seen in the app.

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

**Shield wire (2026-11-12, user):** the pigtail of a solder sleeve that finishes a cable's shield (`_shield_terminal_at_start`: one end is a view with `is_shield`) is drawn by `_shield_draws` as a 45 degree TAPER (`shapes/taper.py`) at its terminal, from the full wire size down to the thickness of the ring's dashes, then thin (`taper.END_RATIO` of a wire) all the way to the ring; no stripe pass. Picking and bounds still use the full size. **The round dots (user, 2026-11-12):** every bend of a wire has a `WireLayout` (a sphere of the wire's own size, rendered by the default `render`), which is hidden inside a normal wire; on the thin shield wire they showed as dots, coming and going as the route changed. `wire.THIN_POINTS` holds the `id` of every bend/end Point of a shield wire (set in `Wire.render`, cleared in `_bind_waypoints` / `_delete`) and `WireLayout.render` draws those handles as thin as the wire. Stand-in test `twist/taper_test.py`; not seen in the app and `twist/thin_handle_test.py`; not seen in the app.

#### wire_layout.py

Part of the wire family.

**Thin handles (2026-11-12):** `render` draws the handle of a bend of a shield wire (`wire.THIN_POINTS`) as thin as that wire (`taper.END_RATIO`), see `wire.py`.

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
