## FILES

#### __init__.py

Package init for the peg-board views — same one-file-per-part layout as `objects_3d`/`objects_schematic`. Already named `objects_pegboard` (with the underscore) in CODEBASE_MAP.md, so no rename drift here, but CODEBASE_MAP.md's coverage of this directory is thin (two files called out by name — `table.py` and `wire_highlight.py` — plus a generic "same layout" line). See `objects/MAP.md` for the circular-import trap and the rigid-child positioning convention, both of which apply here too. The "Peg Board / project-switch" memory-leak audit (MEMORY.md, "Per-table control widgets are class-level singletons") found the one non-self-pruning cache in an otherwise-clean teardown path during peg-board project-switch work — not specific to this directory's own code, but relevant context if debugging a peg-board-related memory leak.

#### base_pegboard.py

`BasePegboard(BaseVar)` — the base peg-board object; see `objectsvar/MAP.md` for what's inherited vs. defined here. Adds peg-board-specific concerns: `touching_budgets`, the per-object floating-table lifecycle (`_table_row`, `_ensure_table_object`, `has_visible_table`, `show_table`, `_delete_table_overlay`), and `notify_table_wires_changed()` (module-level) for keeping a housing's/transition's/bundle's floating wire table in sync.

#### boot.py

Peg-board support for boots was deferred at the DB layer (`pjt_boot`, per CODEBASE_MAP.md) — confirm whether this file is live rendering or a stub before assuming boots actually appear in the peg board.

#### bundle.py

Bundles are 3D + peg-board only (no schematic) — design in `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md`.

#### bundle_layout.py

Companion to `bundle.py`, same 3D + peg-board-only scope.

#### cavity.py

Own `_update_angle_pegboard` mirrors the 3D version minus aabb/obb rotation (no peg-board mesh geometry) and minus the seal fallback.

#### chain_edges.py

`touching_edges()` — resolves which wire/bundle chain edges touch a given peg-board point, used by the drag-handler rope-pull/chain logic.

#### circuit.py

Peg-board-only part type (no 3D or schematic view).

#### cover.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### cpa_lock.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### generic.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### housing.py

Leaf peg-board positioning (`PositionPegboardMixin`/`AnglePegboardMixin` at the DB layer — see CODEBASE_MAP.md's `project_db/` section); a housing's peg-board move/rotate batch-cascades to its cavities/terminals the same way its 3D move/rotate does, minus the housing-accessory groups not viewable in peg-board (cover/seal/boot/tpa/cpa).

#### mixins.py

**A single file, not a package** (unlike `objects/mixins/` and `objects_3d/mixins/`, both real subpackages) — holds this view's `WireTypeMixin` override (`_waypoints`, `_live_waypoint_points`, `_live_waypoint_ids`, `_segments`, `_closest_point_on_segment_xz`, `_point_on_wire`), specialized for the peg-board's flat XZ plane. Don't go looking for `objects_pegboard/mixins/wire_type.py` — everything lives directly in this one module.

#### note.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### project_model.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### seal.py

Seal has no peg-board DB support (not viewable there, per the `cavity.py` note above) — same stub-vs-live caveat as `boot.py`.

#### splice.py

Per CODEBASE_MAP.md's `project_db/` notes, splice is excluded from the peg-board view entirely at the DB layer (`pjt_splice`) — confirm whether this file is live rendering or a stub before assuming splice actually appears in the peg board.

#### table.py

`Table(BasePegboard)` — the floating wire table (a GL texture of a hosted `WireTable`); same class name mirrored in `objects_3d`/`objects_schematic`'s own `table.py` (the facade wrapper is `objects/pegboard_table.py`, still named for its DB table) — not shared code, just this view's own implementation. Also has a private `_TableInteractionHandler` helper class for the table's own click/render handling.

#### table_placement.py

Free-position search for newly-shown floating tables — `find_free_position()` (plus helpers `_rect_overlaps`/`_table_rect`/`_is_free`) scans existing table rectangles (`obstacle_rects_from_objects()`) to place a new table where it doesn't overlap another.

#### terminal.py

Leaf peg-board positioning, same `PositionPegboardMixin`/`AnglePegboardMixin` pattern as `housing.py`.

#### tpa_lock.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### transition.py

Peg-board routing/branch rendering; model-building itself is 3D-side, design in `TRANSITION_DESIGN.md`.

#### wire.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape; part of the wire family with `wire_layout.py`/`wire_marker.py`/`wire_service_loop.py`.

#### wire_highlight.py

`WireHighlight` — one per editor (`EditorPegboard.wire_highlight`). When a wire is selected in ANY wire table, lights up everything it touches in `Config.editor_pegboard.wire_highlight_color` via `identify()`: the wire itself (if visible in the peg board), its bundle(s), each transition BRANCH it's routed through (never the whole transition), and its end housings (or the terminal itself when not seated in a housing). Bundle/branch membership comes from `pjt_wire_paths` tags. Key methods: `show()`, `clear()`, `_light_wire_or_bundles()`, `_light_branches()`, `_light_ends()`.

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.
