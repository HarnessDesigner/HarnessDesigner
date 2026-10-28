## FILES

#### __init__.py

Package init for the peg-board views — same one-file-per-part layout as `objects_3d`/`objects_schematic`. Already named `objects_pegboard` (with the underscore) in CODEBASE_MAP.md, so no rename drift here, but CODEBASE_MAP.md's coverage of this directory is thin (two files called out by name — `table.py` and `wire_highlight.py` — plus a generic "same layout" line). See `objects/MAP.md` for the circular-import trap and the rigid-child positioning convention, both of which apply here too. The "Peg Board / project-switch" memory-leak audit (MEMORY.md, "Per-table control widgets are class-level singletons") found the one non-self-pruning cache in an otherwise-clean teardown path during peg-board project-switch work — not specific to this directory's own code, but relevant context if debugging a peg-board-related memory leak.

#### base_pegboard.py

`BasePegboard(BaseVar)` — the base peg-board object; see `objectsvar/MAP.md` for what's inherited vs. defined here. Adds peg-board-specific concerns: `touching_budgets`, the per-object floating-table lifecycle (`_table_row`, `_ensure_table_object`, `has_visible_table`, `show_table`, `_delete_table_overlay`), and `notify_table_wires_changed()` (module-level) for keeping a housing's/transition's/bundle's floating wire table in sync. Also (2026-10-25) the concentric-section pair behind the "Show Concentric Section" menu actions: `concentric_section_visible(concentric)` (a concentric, or `None`, whose widget row exists and is shown -- disables the action) and `show_concentric_section(concentric, anchor)` (gathers the obstacle footprints of the visible objects, calls `objects/pegboard_section.PegboardSection.show`, redraws). Unlike `show_table` the caller supplies the concentric and the anchor: a concentric belongs to a bundle or a transition BRANCH, not to the object being right-clicked.

#### boot.py

Peg-board support for boots was deferred at the DB layer (`pjt_boot`, per CODEBASE_MAP.md) — confirm whether this file is live rendering or a stub before assuming boots actually appear in the peg board.

#### bundle.py

Bundles are 3D + peg-board only (no schematic) — design in `BUNDLE_DESIGN.md`/`BUNDLE_PLACEMENT.md`. `BundleMenu` has a "Show Concentric Section" action (2026-10-25): the concentric is the bundle's own, else that of a transition branch plugged into either end (`handlers/concentric_handler.find_concentric_for_bundle`), made only when the action is used; the widget is placed near the midpoint of the bundle's run. Disabled while the widget is showing, enabled (re-shows it) after the user closed it.

#### bundle_layout.py

Companion to `bundle.py`, same 3D + peg-board-only scope.

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

`Section(BasePegboard)` (NEW 2026-10-25) -- the concentric section widget's peg-board view, modelled on `table.py`'s `Table`: owns a hidden `ui/concentric_section/section_host.py` `ConcentricSectionHost`, captures it to a GL texture and draws it on its own world-space quad through `shaders.texture` (`TextureProgram`). Same quad, anchoring (position = LEFT edge in X, vertical MIDDLE in Z), selection ring, rounded bottom corners, resize-through-the-ring, cursors and "interaction only reaches the widget while it is SELECTED" as the table -- the tuned constants are imported from `table.py` (`_BORDER_*`, `_RESIZE_*`, `_TABLE_HANDLER`) so the two stay alike, and `render()` bumps `Table._render_id_counter` so a section and a table stacked on each other are ranked by one counter (`gl/object_picker._render_id_of` accepts either). Differs from the table: no anchor, so no connecting line and no anchor visibility to follow (it belongs to a CONCENTRIC, shared by a bundle and a transition branch); the synthetic mouse / wheel dispatch lives in the host, not here (it needs no GL); the wheel is consumed only over the information pane, so the camera still zooms elsewhere; `_delete` frees both GL textures and the hidden host (the table does not). Owner API for the layout / database adapter (`handlers/concentric_handler.build_section`): `widget`, `set_section(spec)`, `set_wire_details(details)`, `refresh()`. A row is made (or a closed one re-shown) by the "Show Concentric Section" action of the bundle and transition context menus (`objects/pegboard_section.PegboardSection.show`); rows saved in the project are restored by `Project.__init__`. It is also the DROP TARGET for a wire dragged out of a wire table (`wire_drop.py`): `wire_drop_contains`, `set_wire_drop_hover` (an ORANGE ring, drawn instead of the green selection ring), `accept_wire_drop` (`handlers/concentric_handler.add_wire`, then `reload()`), and `reload()` itself, which `__init__` calls so a restored section shows what its concentric already holds (planning it first if two wires sit on the same spot).

#### splice.py

Per CODEBASE_MAP.md's `project_db/` notes, splice is excluded from the peg-board view entirely at the DB layer (`pjt_splice`) — confirm whether this file is live rendering or a stub before assuming splice actually appears in the peg board.

#### table.py

`Table(BasePegboard)` — the floating wire table (a GL texture of a hosted `WireTable`); same class name mirrored in `objects_3d`/`objects_schematic`'s own `table.py` (the facade wrapper is `objects/pegboard_table.py`, still named for its DB table) — not shared code, just this view's own implementation. Also has a private `_TableInteractionHandler` helper class for the table's own click/render handling. Since 2026-10-25 a press on a WIRE ROW that then moves `_WIRE_DRAG_THRESHOLD_PX` (6 px) becomes a drag of that wire: `_wire_at` reads the pressed row (the table selects it on the press; `GetSelection()`), `_begin_wire_drag` ends the table's own press at the spot it began (as the click it would have been), `_update_wire_drag` highlights the `wire_drop` target under the pointer and shows a copy / forbidden cursor, and the release hands the wire id to the target (`_finish_wire_drag`). A press on the header, a scroll bar or empty space, a plain click, and a column-picker-closing click never start one; CANCEL, deselecting and deleting end it cleanly (`_end_wire_drag`). Checked against a real `QTableView` with the hosting and canvas stubbed (scratch script), not in the app.

#### table_placement.py

Free-position search for newly-shown floating tables — `find_free_position()` (plus helpers `_rect_overlaps`/`_table_rect`/`_is_free`) scans existing table rectangles (`obstacle_rects_from_objects()`) to place a new table where it doesn't overlap another.

#### terminal.py

Leaf peg-board positioning, same `PositionPegboardMixin`/`AnglePegboardMixin` pattern as `housing.py`.

#### tpa_lock.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape.

#### transition.py

Peg-board routing/branch rendering; model-building itself is 3D-side, design in `TRANSITION_DESIGN.md`. `TransitionMenu` has a "Show Concentric Section" entry (2026-10-25) that is per BRANCH, because a concentric belongs to a branch, not to the transition: one branch gives a plain action, several give a submenu `Branch <branch_id>` (sorted by `branch_id`, the same label the wire table's Branch column uses), none gives no entry. A branch whose bundle already has a concentric shows that one (the pair shares ONE widget); each entry is disabled while its widget is showing. The widget is placed near the transition's own position.

#### wire.py

One file per harness part, same `BasePegboard(parent, db_obj)` shape; part of the wire family with `wire_layout.py`/`wire_marker.py`/`wire_service_loop.py`.

⚠ This wire's own interior waypoints (`waypoints_pegboard`, read via `WireTypeMixin._waypoints` in `objects_pegboard/mixins.py`) are a completely separate list from the SAME wire's 3D waypoints -- see `handlers/MAP.md`'s `wire_drag_base.py` entry for the full "why can I only drag by the ends in peg-board" explanation. A wire routed into a bundle via a 3D drag (`BUNDLE_PLACEMENT.md` section 12) can have zero peg-board waypoints of its own; dragging its body here before adding any will only ever move a true end (or nothing). `WireMenu.on_add_handle` (`Add Handle`, right-click) is how a peg-board-side interior waypoint gets created.

#### wire_drop.py

Finds the drop target for a wire dragged out of a peg-board wire table (NEW 2026-10-25). Both panels are GL textures drawn by canvas-level objects, not real widgets, so Qt's own drag and drop (which needs a real window for its loop) cannot carry the drag; `table.py`'s `Table` recognises the drag of a wire row itself and, while it lasts, asks `target_at(screen_pos)` which registered target is under the pointer (topmost by `render_id` wins). A target registers itself with `register` (a `WeakSet`) and needs `wire_drop_contains(screen_pos)`, `set_wire_drop_hover(flag)`, `accept_wire_drop(wire_id)` and `render_id`; today only `section.py`'s `Section`. Its own file because `table.py` and `section.py` share constants and so cannot import each other.

#### wire_highlight.py

`WireHighlight` — one per editor (`EditorPegboard.wire_highlight`). When a wire is selected in ANY wire table, lights up everything it touches in `Config.editor_pegboard.wire_highlight_color` via `identify()`: the wire itself (if visible in the peg board), its bundle(s), each transition BRANCH it's routed through (never the whole transition), and its end housings (or the terminal itself when not seated in a housing). Bundle/branch membership comes from `pjt_wire_paths` tags. Key methods: `show()`, `clear()`, `_light_wire_or_bundles()`, `_light_branches()`, `_light_ends()`.

#### wire_layout.py

Part of the wire family.

#### wire_marker.py

Part of the wire family.

#### wire_service_loop.py

Part of the wire family.
