## FILES

#### __init__.py

Package init for the peg-board views — same one-file-per-part layout as `objects_3d`/`objects_schematic`. Already named `objects_pegboard` (with the underscore) in CODEBASE_MAP.md, so no rename drift here, but CODEBASE_MAP.md's coverage of this directory is thin (two files called out by name — `table.py` and `wire_highlight.py` — plus a generic "same layout" line). See `objects/MAP.md` for the circular-import trap and the rigid-child positioning convention, both of which apply here too. The "Peg Board / project-switch" memory-leak audit (`harness_designer/objects/MAP.md` DESIGN NOTES, "Per-table control widgets are class-level singletons") found the one non-self-pruning cache in an otherwise-clean teardown path during peg-board project-switch work — not specific to this directory's own code, but relevant context if debugging a peg-board-related memory leak.

#### base_pegboard.py

`BasePegboard(BaseVar)` — the base peg-board object; see `objectsvar/MAP.md` for what's inherited vs. defined here. Adds peg-board-specific concerns: `touching_budgets`, the per-object floating-table lifecycle (`_table_row`, `_ensure_table_object`, `has_visible_table`, `show_table`, `_delete_table_overlay`), and `notify_table_wires_changed()` (module-level) for keeping a housing's/transition's/bundle's floating wire table in sync. Also (2026-10-25) the concentric-section pair behind the "Show Concentric Section" menu actions: `concentric_section_visible(concentric)` (a concentric, or `None`, whose widget row exists and is shown -- disables the action) and `show_concentric_section(concentric, anchor)` (gathers the obstacle footprints of the visible objects, calls `objects/pegboard_section.PegboardSection.show`, redraws). Unlike `show_table` the caller supplies the concentric and the anchor: a concentric belongs to a bundle or a transition BRANCH, not to the object being right-clicked.

#### boot.py

Peg-board support for boots was deferred at the DB layer (`pjt_boot`, per CODEBASE_MAP.md) — confirm whether this file is live rendering or a stub before assuming boots actually appear in the peg board.

#### bundle.py

2026-10-30: `_recalculate_geometry` now calls `_compute_obb()`/`_compute_aabb()` itself -- `_update_scale` is a no-op here, so the pick boxes used to stay at the bundle's creation-time shape (a bent/moved bundle was only clickable inside its original box).

Bundles are 3D + peg-board only (no schematic) — design in `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md`. `BundleMenu` has a "Show Concentric Section" action (2026-10-25): the concentric is the bundle's own, else that of a transition branch plugged into either end (`handlers/concentric_handler.find_concentric_for_bundle`), made only when the action is used; the widget is placed near the midpoint of the bundle's run. Disabled while the widget is showing, enabled (re-shows it) after the user closed it.

#### bundle_layout.py

Companion to `bundle.py`, same 3D + peg-board-only scope.

#### cable.py

`Cable(Wire)` (NEW 2026-11-06, step 8): the peg-board view of a placed cable, a subclass of the peg-board wire view like `objects_3d/cable.py` is of the 3D one. Drawn at `part.trunk_size` (a ribbon is its width by its thickness, lying flat), in the jacket colour (a twisted or ribbon cable has the "no color" jacket, so its first conductor's colour), no stripe, between the split planes only (`_segments` trims the end segments by `start_split_mm` / `stop_split_mm`; `reload_splits`). **A cable is placed in 3D and SEEDED onto the board, as a bundle is** (`seed_from_3d`, called by `add_handlers/editor_3d/cable.py` when the placement ends, and by the facade for a cable from before the board knew cables, `needs_seed`): the 3D route is unfolded into the board plane from the 3D start's X/Z, each 3D segment keeping its REAL length along its X/Z direction (a vertical one keeps the previous direction), one board waypoint (`pjt_cable_paths`, view `pegboard`) per interior 3D waypoint, so the cable is exactly as long on the board as in 3D and needs no slack or rope pull. The conductors' board layout is worked out FLAT here: `split_positions(start)` (the conductors side by side across the trunk at the split plane, `trunk width / count` apart, shield last) and `fan_out_positions(start)` (their ends across the cable's true end, spread by `FAN_SPREAD`, or side by side for a ribbon, in `start_order` / `stop_order`); both from `_end_frame`, the end segment's direction, with "across" on the same side at both ends. No slack handler (nothing attaches to a cable); `handle_interaction` does nothing, so a click only selects (dragging a placed cable is not built, in 3D either). `CableMenu` is the 3D menu without the roll. Not run in the app; the geometry, the seeding and the facade's board half were checked on stand-ins and a scratch SQLite (`pegboard_cable_test.py`).

#### cavity.py

Own `_update_angle_pegboard` mirrors the 3D version minus aabb/obb rotation (no peg-board mesh geometry) and minus the seal fallback.

#### chain_edges.py

`touching_edges()` — resolves which wire/bundle chain edges touch a given peg-board point, used by the drag-handler rope-pull/chain logic.

#### circuit.py

The peg-board editor's view of a circuit: an inert placeholder (`BasePegboard` built with no vbo/angle/position/scale/material, never visible, `obb` None), built like a `Note` that was never placed in this editor. A circuit has nothing to draw; the view exists so the canvas can hold the circuit as its one selected object (see `objects/circuit.py`). The mouse can not pick it. Added 2026-10-25. Its `set_selected` is overridden (2026-10-25): deselecting also calls `Circuit.deselect_in_editor()`, so the circuit editor stops showing the circuit's row as selected (it clears the row only when that row is the selected one, otherwise it does nothing).

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

#### section.py

`Section(BasePegboard)` (NEW 2026-10-25) -- the concentric section widget's peg-board view, modelled on `table.py`'s `Table`: owns a hidden `ui/concentric_section/section_host.py` `ConcentricSectionHost`, captures it to a GL texture and draws it on its own world-space quad through `shaders.texture` (`TextureProgram`). Same quad, anchoring (position = LEFT edge in X, vertical MIDDLE in Z), selection ring, rounded bottom corners, resize-through-the-ring, cursors and "interaction only reaches the widget while it is SELECTED" as the table -- the tuned constants are imported from `table.py` (`_BORDER_*`, `_RESIZE_*`, `_TABLE_HANDLER`) so the two stay alike, and `render()` bumps `Table._render_id_counter` so a section and a table stacked on each other are ranked by one counter (`gl/object_picker._render_id_of` accepts either). Differs from the table: no single anchor -- it belongs to a CONCENTRIC, shared by a bundle and a transition branch -- so it draws one connecting line (the table's black cylinder, constants imported from `table.py`) per owner: the bundle, and the transition of the branch (`_Connector`, `_connector_anchors`, `_recompute_connectors`, `_render_connectors`; follows each anchor's `position_pegboard`, `waypoints_pegboard` and `is_visible_pegboard`, and a line is skipped while its anchor is hidden); the synthetic mouse / wheel dispatch lives in the host, not here (it needs no GL); the wheel is consumed only over the information pane, so the camera still zooms elsewhere; `_delete` frees both GL textures and the hidden host (the table does not). Owner API for the layout / database adapter (`handlers/concentric_handler.build_section`): `widget`, `set_section(spec)`, `set_wire_details(details)`, `refresh()`. A row is made (or a closed one re-shown) by the "Show Concentric Section" action of the bundle and transition context menus (`objects/pegboard_section.PegboardSection.show`); rows saved in the project are restored by `Project.__init__`. It is also the DROP TARGET for a wire dragged out of a wire table (`wire_drop.py`): `wire_drop_contains`, `set_wire_drop_hover` (an ORANGE ring, drawn instead of the green selection ring), `accept_wire_drop` (`handlers/concentric_handler.add_wire`, then `reload()`), and `select_wire(wire_id)` (selects that wire's cable in the widget, or nothing when the section does not hold it; called by `WireHighlight` whenever a wire is selected / deselected in any wire table of the same editor) and the other direction, `_on_cable_selected` (a cable picked or clicked off in the widget -> `WireHighlight.show` / `clear_all` plus `WireTable.mirror_selection`; `_syncing_cable` stops `select_wire` from echoing back), and `reload()` itself, which `__init__` calls so a restored section shows what its concentric already holds (planning it first if two wires sit on the same spot). (2026-11-01) `_print_factor` (class default 1, same as `Table`) is the pixel multiple the texture is captured at; it is raised only while File > "Print Peg Board..." prints (`set_print_quality(factor)`, driven by `pegboard_print.renderer.sharp_tables`) and put back to 1 afterwards. `_regrab_texture` passes it to `grab_rgba`, divides the captured size by it so the mm footprint (and the DB size) never changes, and `render` multiplies `_BOTTOM_CORNER_RADIUS_PX` by it because the shader's pixel units are the texture's own.

#### splice.py

Per CODEBASE_MAP.md's `project_db/` notes, splice is excluded from the peg-board view entirely at the DB layer (`pjt_splice`) — confirm whether this file is live rendering or a stub before assuming splice actually appears in the peg board.

#### table.py

`Table(BasePegboard)` — the floating wire table (a GL texture of a hosted `WireTable`); same class name mirrored in `objects_3d`/`objects_schematic`'s own `table.py` (the facade wrapper is `objects/pegboard_table.py`, still named for its DB table) — not shared code, just this view's own implementation. Also has a private `_TableInteractionHandler` helper class for the table's own click/render handling. Since 2026-10-25 a press on a WIRE ROW that then moves `_WIRE_DRAG_THRESHOLD_PX` (6 px) becomes a drag of that wire: `_wire_at` reads the pressed row (the table selects it on the press; `GetSelection()`), `_begin_wire_drag` ends the table's own press at the spot it began (as the click it would have been), `_update_wire_drag` highlights the `wire_drop` target under the pointer and shows a copy / forbidden cursor, and the release hands the wire id to the target (`_finish_wire_drag`). A press on the header, a scroll bar or empty space, a plain click, and a column-picker-closing click never start one; CANCEL, deselecting and deleting end it cleanly (`_end_wire_drag`). Checked against a real `QTableView` with the hosting and canvas stubbed (scratch script), not in the app. (2026-11-01) `_print_factor` (class default 1) is the pixel multiple the texture is captured at; it is raised only while File > "Print Peg Board..." prints (`set_print_quality(factor)`, driven by `pegboard_print.renderer.sharp_tables`) and put back to 1 afterwards. `_regrab_texture` passes it to `grab_rgba`, divides the captured size by it so the mm footprint (and the DB size) never changes, and `render` multiplies `_BOTTOM_CORNER_RADIUS_PX` by it because the shader's pixel units are the texture's own.

#### table_placement.py

Free-position search for newly-shown floating tables — `find_free_position()` (plus helpers `_rect_overlaps`/`_table_rect`/`_is_free`) scans existing table rectangles (`obstacle_rects_from_objects()`) to place a new table where it doesn't overlap another.

#### terminal.py

Leaf peg-board positioning, same `PositionPegboardMixin`/`AnglePegboardMixin` pattern as `housing.py`.

#### tpa_lock.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### transition.py

Peg-board routing/branch rendering; model-building itself is 3D-side, design in `TRANSITION_DESIGN.md`. `TransitionMenu` has a "Show Concentric Section" entry (2026-10-25) that is per BRANCH, because a concentric belongs to a branch, not to the transition: one branch gives a plain action, several give a submenu `Branch <branch_id>` (sorted by `branch_id`, the same label the wire table's Branch column uses), none gives no entry. A branch whose bundle already has a concentric shows that one (the pair shares ONE widget); each entry is disabled while its widget is showing. The widget is placed near the transition's own position.

#### wire.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape; part of the wire family with `wire_layout.py`/`wire_marker.py`/`wire_service_loop.py`. **Hooks for the cable subclasses (2026-11-06):** `_trunk_size(part)` (width, thickness; the part's `od_mm` twice), `_jacket_color(part)` and `_uses_stripe`, read by `__init__`, and `_segment_transforms` scales by x and y separately (a ribbon is wider than it is thick); `reload_conductor_colors()` redraws a cable lead in its conductor's colour after a catalog edit (mirrors the 3D view's).

⚠ This wire's own interior waypoints (`waypoints_pegboard`, read via `WireTypeMixin._waypoints` in `objects_pegboard/mixins.py`) are a completely separate list from the SAME wire's 3D waypoints -- see `handlers/MAP.md`'s `wire_drag_base.py` entry for the full "why can I only drag by the ends in peg-board" explanation. A wire routed into a bundle via a 3D drag (`BUNDLE_PLACEMENT.md` section 12) can have zero peg-board waypoints of its own; dragging its body here before adding any will only ever move a true end (or nothing). `WireMenu.on_add_handle` (`Add Handle`, right-click) is how a peg-board-side interior waypoint gets created.

#### wire_drop.py

Finds the drop target for a wire dragged out of a peg-board wire table (NEW 2026-10-25). Both panels are GL textures drawn by canvas-level objects, not real widgets, so Qt's own drag and drop (which needs a real window for its loop) cannot carry the drag; `table.py`'s `Table` recognises the drag of a wire row itself and, while it lasts, asks `target_at(screen_pos)` which registered target is under the pointer (topmost by `render_id` wins). A target registers itself with `register` (a `WeakSet`) and needs `wire_drop_contains(screen_pos)`, `set_wire_drop_hover(flag)`, `accept_wire_drop(wire_id)` and `render_id`; today only `section.py`'s `Section`. Its own file because `table.py` and `section.py` share constants and so cannot import each other.

#### wire_highlight.py

`WireHighlight` — one per editor (`EditorPegboard.wire_highlight`). When a wire is selected in ANY wire table, lights up everything it touches in `Config.editor_pegboard.wire_highlight_color` via `identify()`: the wire itself (if visible in the peg board), its bundle(s), each transition BRANCH it's routed through (never the whole transition), and its end housings (or the terminal itself when not seated in a housing). Bundle/branch membership comes from `pjt_wire_paths` tags. It also selects the wire's cable in every concentric section widget of the editor (`_select_in_sections`, through `wire_drop.targets()`), and clears that selection with the highlight; `clear_all()` clears whoever made it. It also lights the wire's whole circuit in all three editors through `Circuit.highlight` (`_light_circuit`, applied before the blue so the blue wins; a circuit that is also selected keeps its highlight when this one is undone). Key methods: `show()`, `clear()`, `_light_wire_or_bundles()`, `_light_branches()`, `_light_ends()`.

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.

#### Peg board: one table per transition + selected-wire highlight (built 2026-09-29, NOT yet run in the GUI)
- **One table per transition, none per branch** (user's call): `PJTTransitionBranch` lost `TablePositionPegMixin`/`TableHiddenMixin`, its per-branch `pjt_pegboard_tables` row on insert, its `delete`/`name` overrides; `PJTPegboardTable.anchor` only looks at housing/bundle/transition. `PJTTransition.wires` is now de-duplicated (a wire entering one branch and leaving another is on two branches' lists but must be one row in the single table). The `table_point_peg_id`/`table_hidden` columns on `pjt_transition_branches` are left in the schema, unused (schema lives in two repos).
- **Branch column** (transition tables only): `COLUMN_DEFS[33]` `'Branch'`, `transition_only`; lists the `branch_id`s of THIS transition's branches the wire is routed through, from `pjt_wire_paths`. Transition tables default to `DEFAULT_VISIBLE_COLUMNS_TRANSITION`; a table whose column choice was already saved keeps it (add Branch via the header right-click picker).
- **Wire highlight**: selecting a wire row in ANY wire table (housing/bundle/transition) lights everything it touches blue -- see `CODEBASE_MAP.md` `objects_pegboard/wire_highlight.py`. Rules from the user: never the whole transition, only the branches the wire goes through; wire if visible in the peg board else its bundle; housing if the terminal is seated, else the terminal.
- **Source of truth for "which bundle/branch does a wire go through" is `pjt_wire_paths`** (`bundle_id`/`transition_branch_id` tags; user's decision 2026-09-29). **The code that WRITES those tags does not exist yet -- the user is writing it soon.** Until then `PJTTransitionBranch.wires`, the transition table's rows, the Branch column and the highlight's bundle/branch part are all empty; only the wire/housing/terminal part works. Don't "fix" this by falling back to the concentric tables (no fallback paths).

#### A synthetic press must always end in a release (`table.py`)
`Table._press_target` is the hidden widget that was sent a synthetic mouse press. Never just set it to `None` to end a press: the widget keeps thinking the button is down (a scroll bar's arrow / trough auto-repeat keeps running, so the table scrolls by itself). End a press the canvas will not release (grab broken by `CANCEL`, deselect while pressed) through `_abort_press()`, which sends the release first. `ui/concentric_section/section_host.py`'s `cancel_press()` does the same (it keeps `_press_local` for that), and `Section.set_selected(False)` calls it.
