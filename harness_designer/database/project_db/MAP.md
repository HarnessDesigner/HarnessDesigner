## FILES

#### __init__.py

Package init for `project_db`; no real logic of its own. Per-project tables, all prefixed `pjt_` — the placed-instance layer of the "same-name modules" pipeline (`create_database` → `global_db` → `project_db` → `objects/`, see `database/MAP.md`): a `pjt_*` row holds position/angle/scale plus a `part_id` FK into the matching `global_db` catalog part, and holds a weakref to its live scene object (`get_object()`/`set_object()`).

#### cleanup.py

Project-close cleanup sweep. Orphaned-point batch cleanup (removing peg-board points left behind after an object delete) is planned but not yet implemented here (see `TODO.md`).

#### pjt_bases.py

(~1100-1900 lines) Base classes for every `pjt_*` row/table: `PJTEntryBase`/`PJTTableBase`/`PJTTables`, mixing in `common_db.callback.CallbackMixin`. `PJTTables` exposes one `pjt_*_table` accessor per project table (e.g. `pjt_concentrics_table`, `pjt_pegboard_tables_table`). Row ids come from `database/id_generator.py` (SQLite, client-side) or the MySQL server's `next_project_row_id` (see MEMORY.md's "Project row-id collision safety" note). Also owns `_schema_dependency_order()` — a topological sort of every `create_database` module's own SQL table name, computed once and cached, derived from each table's `SQLField.references` metadata, so a batched multi-table insert can always visit a parent table before a child that holds a foreign key into it. This is deliberately NOT the same as `PJTTables._ordered_project_tables`'s own hand-picked list (which exists only for `load()`'s plain reads, where ordering doesn't matter) — that list has a known gap (`pjt_bundles` references `pjt_points3d` but is visited before it there), which is exactly why the real dependency-ordered version exists for actual cross-table inserts.

#### pjt_boot.py

`PJTBoot` — a placed boot instance (`Angle3DMixin`, `Position3DMixin`, `Scale3DMixin`, `HousingMixin`, `Visible3DMixin`, `NameMixin`, `NotesMixin`, `SmoothMixin`). Peg-board support is deferred — not yet added (the user has prep work to do first; see MEMORY.md's Peg Board Editor database-layer entry).

#### pjt_bundle.py

`PJTBundle` — a placed bundle instance. `length_mm`/`length_m` properties (mirrors `pjt_wire`'s, via `geometry.line.Line.length()`). `StartStopPositionPegboardMixin`/`VisiblePegboardMixin`; `waypoints_pegboard` property (no schematic equivalent — bundles are never shown in schematic). Also `TablePositionPegMixin`/`TableHiddenMixin` — a bundle can own a floating peg-board data table (see `pjt_pegboard_table.py`). `delete()`'s 3D-branch `BundleLayout` cleanup has a known pre-existing bug querying a nonexistent `position3d_id` column (real column is `point3d_id`) — flagged, not fixed, in `TODO.md`.

#### pjt_bundle_layout.py

`PJTBundleLayout` — same hand-written exclusive-position pattern as `pjt_wire_layout.py`, but only `position3d`/`position_pegboard` (no schematic variant, since bundles aren't shown there). Deliberately does NOT use `Position3DMixin`/`PositionPegboardMixin` — those mixins' shared blind "auto-create a default point if NULL" getter is wrong here, where exactly one of the two columns must be non-NULL; both properties are hand-written, each setter explicitly clearing the other to NULL. `VisiblePegboardMixin` added. `attached_bundles()` had to be rewritten when this exclusivity was introduced — it used to assume `position3d_id` was always non-None and now branches across whichever view is actually populated.

#### pjt_bundle_path.py

`PJTBundlePathsTable`/`PJTBundlePath` for `pjt_bundle_paths` (NEW 2026-09-26, untested) — one row per interior waypoint per bundle (`bundle_id`, `idx`, exactly one of `point3d_id`/`point_pegboard_id`, no schematic). Rows reference SHARED point rows, so `idx` lives here, not on the point. The source of truth for a bundle's waypoint order: everything writes through `add`/`append`/`remove`/`set_route` (which renumber in one `batch_update`), and `PJTBundle.waypoints3d`/`waypoints_pegboard` read from it.

#### pjt_cavity.py

`PJTCavity` — a placed cavity instance (within a housing). `PositionPegboardMixin`/`AnglePegboardMixin`/`VisiblePegboardMixin`. Its own `_update_angle_pegboard` mirrors `_update_angle3d` minus aabb/obb rotation (no peg-board mesh geometry to align against) and minus the `or self.seal` fallback (a seal isn't viewable in the peg-board view).

#### pjt_circuit.py

`PJTCircuit` — a per-project circuit record (`pjt_circuits`).

#### pjt_concentric.py

`PJTConcentricsTable`/`PJTConcentric(PJTEntryBase, NotesMixin)` — a concentric-cable group row (`pjt_concentrics`).

#### pjt_concentric_layer.py

`PJTConcentricLayersTable`/`PJTConcentricLayer(PJTEntryBase, NotesMixin)` — one layer within a concentric-cable group (`pjt_concentric_layers`).

#### pjt_concentric_wire.py

`PJTConcentricWiresTable`/`PJTConcentricWire(PJTEntryBase, NotesMixin, Position2DMixin)` — a wire's membership row within a concentric-cable layer (`pjt_concentric_wires`).

#### pjt_cover.py

`PJTCover` — a placed housing-cover accessory instance (`Angle3DMixin`, `Position3DMixin`, `Scale3DMixin`, `HousingMixin`, `Visible3DMixin`, `NameMixin`, `NotesMixin`, `SmoothMixin`). Housing-level accessories (cover/seal/boot-lock/tpa-lock/cpa-lock) are not in the peg-board object list, so this has no `position_pegboard`/`angle_pegboard` — this is why `PJTHousing`'s peg-board cascade set is smaller than its 3D cascade set.

#### pjt_cpa_lock.py

`PJTCPALock` — a placed CPA-lock accessory instance, same shape and same peg-board exclusion as `pjt_cover.py`.

#### pjt_housing.py

`PJTHousing` — has `position_pegboard`/`angle_pegboard` (`PositionPegboardMixin`/`AnglePegboardMixin`, own property overrides binding `_update_position_pegboard`/`_update_angle_pegboard`) — batch-cascades to every cavity's/terminal's peg-board position/angle (+ clones via `parent_point_id`), mirroring `_update_position3d`/`_update_angle3d` minus the housing-accessory (cover/seal/boot/tpa-lock/cpa-lock) groups, which aren't viewable in the peg-board editor. Y axis is always honored/stored at the DB layer here — Y-locking to 0.0 is deliberately an object-layer concern (`objects/objects_pegboard/base_pegboard.py`), not a DB-layer one, since that's where a response to an out-of-bounds value can be logged and where the offending control can be identified. Also `TablePositionPegMixin`/`TableHiddenMixin` (can own a floating peg-board data table, see `pjt_pegboard_table.py`) and `ScalePegboardMixin`.

#### pjt_note.py

`PJTNote` — a free-floating project note (`pjt_notes`). The only `project_db` class using `Angle3DLockMixin` — a lock flag gating whether its `angle3d` participates in whatever would otherwise update it, alongside the full position/angle/visibility/scale mixin set (2D, 3D, and peg-board).

#### pjt_pegboard_table.py

`PJTPegboardTablesTable`/`PJTPegboardTable(PJTEntryBase, PositionPegboardMixin, VisiblePegboardMixin)` — the CURRENT, real Excel-like data-table-overlay row (`pjt_pegboard_tables`), one row per anchor (housing/bundle/transition — a transition gets exactly ONE table for all its branches, not one per branch) that has a floating peg-board wire table. Its own `position_pegboard` is deliberately the SAME `pjt_points_pegboard` row as the owning anchor's own `table_point_peg_id` (`mixins/table_position_peg.py`'s `TablePositionPegMixin`, mixed into every anchor type that can own one of these), not a fresh point of its own — sharing that one point is what lets `PJTPegboardTable.anchor` and `PJTPegboardTablesTable.get_from_point_pegboard_id` find one row from the other by plain equality lookup, in either direction, with no forward FK on either side. Created at a fixed, deliberately elevated `Y` (`TABLE_DEPTH_Y = 50.0`, peg-board X/Z are the screen's two axes under a top-down camera, Y is depth/render order) so a table always renders on top of ordinary anchors/wires/bundles beneath it, and at a naive default size (`DEFAULT_TABLE_WIDTH`/`HEIGHT` = 100.0/50.0 world mm) since insert-time has no live view/AABB data to run an obstacle-avoiding placement search — a user can resize it afterward via its own MDI sub-window edges. This is a separate, surviving concept from the OLD isolated `pjt_pegboard_points`/`pjt_pegboard_waypoints`/`pjt_pegboard_tables`-as-overlay design referenced in old planning notes, which has been fully superseded by the mixin-based peg-board DB layer (see `mixins/MAP.md` and MEMORY.md's Peg Board Editor entries) — don't confuse the two; this file IS the current, real table.

#### pjt_point2d.py

`PJTPoint2D`/`PJTPoints2DTable` — real `x`/`y`/`z` columns/properties, 1:1 with `Point`'s own axes (schematic plane is X/Z, so `y` is always `0.0`); `insert(x, y, z, wire_id=None, idx=None)`. Uses a 2-byte `b'2d'` `Point.db_id` suffix for clone-detection.

#### pjt_point3d.py

`PJTPoint3D`/`PJTPoints3DTable` — the real 3D waypoint/anchor-position table; singleton/attach/clone/self-heal lifecycle, `parent_point_id` column, `_skip_db_write` batch flag. Uses a 2-byte `b'3d'` `Point.db_id` suffix for clone-detection.

#### pjt_point_pegboard.py

`PJTPointPegboard`/`PJTPointsPegboardTable` — structurally identical to `pjt_point3d.py`'s `PJTPoint3D` (same singleton/attach/clone/self-heal lifecycle, same `parent_point_id` column, same `_skip_db_write` batch flag) against `pjt_points_pegboard` instead of `pjt_points3d` — uses an 8-byte `b'pegboard'` `Point.db_id` suffix for clone-detection (vs. the 2-byte `b'3d'`/`b'2d'` suffixes of the other two point tables).

#### pjt_seal.py

`PJTSeal` — a placed wire-seal/housing-seal accessory instance (`Angle3DMixin`, `Position3DMixin`, `PositionPegboardMixin`, `AnglePegboardMixin`, `VisiblePegboardMixin`, `Scale3DMixin`, `ScalePegboardMixin`, `HousingMixin`, `Visible3DMixin`, `NameMixin`, `NotesMixin`, `SmoothMixin`).

#### pjt_splice.py

`PJTSplice` — a placed splice instance. Excluded from the peg-board VIEW entirely ("splices are not in the pegboard view at all") even though it still carries `PositionPegboardMixin`/`AnglePegboardMixin`-family columns from a mechanical rename-breakage fix (`PositionPegMixin`/`AnglePegMixin` → `...Pegboard...`) — no new peg-board capability was added, it just isn't broken by the rename. Has `TablePositionPegMixin` (can anchor a data table) and `StartStopPositionPegboardMixin`/`Position2DMixin`.

#### pjt_terminal.py

`PJTTerminal` — a placed terminal instance. `PositionPegboardMixin`/`AnglePegboardMixin`/`VisiblePegboardMixin`; leaf (no cascade of its own, matches the 3D view). `sync_free_wire_points(view)` re-derives its crimp/back-face points (+ `parent_point_id` children) from position/angle for a cavity-less (free-standing) terminal — a no-op for seated terminals (cached `self.cavity` guard keeps the seated path free of SQL). `_create_free` (shared by `add_at_wire_end`/`add_free`) builds one; a 3D-placed free terminal gets a pegboard `(x, 0, z)` position and vice versa, like housings.

#### pjt_tpa_lock.py

`PJTTPALock` — a placed TPA-lock accessory instance, same shape and same peg-board exclusion as `pjt_cover.py`.

#### pjt_transition.py

`PJTTransition` — a placed transition instance. `PositionPegboardMixin`/`AnglePegboardMixin`/`VisiblePegboardMixin` (leaf, no cascade) and owns ONE peg-board wire table (`wires` = the de-duplicated union of its branches' wires, since a wire entering one branch and leaving another must be one row, not two). Has `TablePositionPegMixin` but NOT `TableHiddenMixin` (unlike `pjt_housing.py`/`pjt_bundle.py`). The source of truth for "which bundle/branch a wire goes through" is `pjt_wire_paths`' `bundle_id`/`transition_branch_id` tags — as of 2026-09-29 the code that WRITES those tags doesn't exist yet, so the transition table's rows and its Branch column stay empty until that lands; don't "fix" this with a fallback to the concentric tables.

#### pjt_transition_branch.py

`PJTTransitionBranch` — `PositionPegboardMixin` only (no angle, matching its 3D shape) + `VisiblePegboardMixin`, and NO table of its own (lost `TablePositionPegMixin`/`TableHiddenMixin` in the 2026-09-29 "one table per transition, not per branch" change — its `table_point_peg_id`/`table_hidden` schema columns are left unused). `offset`/`bulb_offset`/`angle` are literal world-space values, not rotated with the branch.

#### pjt_wire.py

`PJTWire` — `StartStopPositionPegboardMixin`/`VisiblePegboardMixin`. `waypoints3d`/`waypoints2d`/`waypoints_pegboard` properties each read from the corresponding point table's own `for_wire()` via `pjt_wire_path.py`'s path table — counts genuinely differ per view (e.g. 30 in 3D, 2 in peg-board, 0 in schematic) since a waypoint is a plain row in that view's own points table tagged via the path table, not a shared column. `length_mm`/`length_m` mirrored onto `pjt_bundle.py`.

#### pjt_wire_layout.py

`PJTWireLayout` — hand-written (NOT mixin-based) exclusive position handling: exactly one of `position3d`/`position2d`/`position_pegboard` (`point3d_id`/`point2d_id`/`point_pegboard_id` columns) is ever non-NULL per row, each setter clearing the other two. Deliberately doesn't use `Position3DMixin`/`Position2DMixin`/`PositionPegboardMixin` — their shared blind auto-create-on-NULL getter is wrong here. `VisiblePegboardMixin` added. `attached_wires()` had to be rewritten for the same reason as `pjt_bundle_layout.py`'s `attached_bundles()` — it used to assume `position3d_id` was always non-None.

#### pjt_wire_marker.py

`PJTWireMarker` — a placed wire-marker instance (project-side counterpart of `global_db/wire_marker.py`'s catalog part).

#### pjt_wire_path.py

`PJTWirePathsTable`/`PJTWirePath` for `pjt_wire_paths` (NEW 2026-09-26, untested) — one row per INTERIOR waypoint per wire per view (`wire_id`, `idx`, exactly one of `point3d_id`/`point_pegboard_id`/`point2d_id`, plus optional `bundle_id`/`concentric_id`/`transition_id`/`transition_branch_id` tags; a wire's start/stop stay columns on `pjt_wires`). Rows reference SHARED point rows, so `idx` lives here, not on the point. THE source of truth for every wire waypoint index: everything writes through `add`/`append`/`remove`/`set_route` (which renumber in one `batch_update`), and `PJTWire.waypoints3d`/`waypoints2d`/`waypoints_pegboard` read from it. Also the (not-yet-written-to) source of truth for which bundle/transition-branch a wire runs through, via its `bundle_id`/`transition_branch_id` tags — see `pjt_transition.py`.

#### pjt_wire_service_loop.py

`PJTWireServiceLoop` — a placed wire-service-loop instance. `AnglePegboardMixin`/`StartStopPositionPegboardMixin`/`VisiblePegboardMixin`, leaf.

#### project.py

`Project` — the project table itself (one row, project-wide metadata: `model_id`/`color_id` for the optional project model, no position/scale/angle columns of its own — "Add/Edit Project Model" sets file + color but the model stays at the origin).

#### pseudo_bundle_layout.py

`PseudoPJTBundleLayout(PJTBundleLayout)` — an in-memory-only stand-in for a `PJTBundleLayout` row, used while a peg-board drag needs a waypoint that doesn't have a real row yet. Constructed directly with `table=None` and a throwaway `db_id`, never through `PJTBundleLayoutsTable`; every database-backed property is overridden to return in-memory state set by `configure()`, and setters are no-ops, so nothing is written back to the database — the real rows are written only when the drag releases. Mirrors `pseudo_wire_layout.py`'s `PseudoPJTWireLayout`, but unlike that one, visibility IS configurable here (a drag waypoint is meant to be seen, whereas a wire-snap probe must stay hidden).

#### pseudo_wire_layout.py

`PseudoPJTWireLayout(PJTWireLayout)` — an in-memory-only stand-in backing an invisible wire-snap probe. Wire snapping (onto a terminal's attach point, a splice's branch point, or another wire's dangling end) used to only work when the pick ray happened to intersect the target's exact mesh geometry; the fix reuses `objects.wire_layout.WireLayout` itself as the pickable hit-test target (it already renders as a sphere sized to the wire's own `od_mm` and is already recognized by every hover/click branch), so `handlers.wire_snap.SnapProbeSet` builds one of these at every snap-allowed location. This module supplies the one piece both consumers (`handlers.wire_handler.AddWireHandler`, `gl.canvas3d.dragging.EndpointDragObject`) needed: something satisfying `PJTWireLayout`'s type contract while never touching a real database row.

#### table_data.py

`TableData` — one project table's cache (`WRITE_DESIGN.md` section 4). One load per project, reads from memory, changes recorded per row and column, inserts and deletes cancelled or queued, and the flush's `DELETE`/`INSERT`/`UPDATE` statements built from the cache. `RowDeletedError` is raised on a read or change to a deleted row. `RAW_DELETE_IMMEDIATE` selects the immediate or deferred delete path. Project tables only; not yet wired into `PJTTables` for the general case. Distinct from the still-planned, NOT-yet-built per-gesture write manager described in MEMORY.md ("Write manager for drag/rotate persistence") — that one is a `with`-scoped deferral of every mouse-move's DB write to one batched transaction at gesture end, a different mechanism from this row-cache-and-flush design.

## FOLDERS

#### mixins/

Column mixins for the `pjt_*` row classes above (position/angle/scale/visibility per view, plus name/notes/part/housing/smooth/table-overlay mixins) — see `mixins/MAP.md`. This codebase leans heavily on mixins here, so a method actually used by a class may not be defined on that class at all — check mixins before concluding something is missing or before adding an override.
