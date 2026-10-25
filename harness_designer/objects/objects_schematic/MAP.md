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

#### splice.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### table.py

`Table(BaseSchematic)` — the floating wire table's schematic-view rendering; same class name as the 3D/peg-board `Table`, not shared code.

#### terminal.py

Explicitly built to cope with `cavity is None` — hosts the free-standing (cavity-less) terminal rendering as a shared flat ring VBO, not a separate view class (MEMORY.md "Empty-space right-click menus"); **NOT yet run in the GUI**.

#### tpa_lock.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### transition.py

One file per harness part, same `BaseSchematic(parent, db_obj)` shape.

#### wire.py

Wire family; schematic has no waypoints — a wire's end is simply the terminal's `wire_position2d`.

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.

## FOLDERS

#### mixins/

Empty package (`__init__.py` only) — see `mixins/MAP.md` for why.
