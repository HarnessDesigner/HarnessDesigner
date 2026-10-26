## FILES

#### __init__.py

Package init for `create_database`; no real logic of its own. This package is the DDL/seed layer: one file per table, plural names (mirroring `global_db`'s singular / `project_db`'s `pjt_`-prefixed names for the same entity — see `database/MAP.md`'s "same-name modules" note). Each module defines its table's schema as a module-level `SQLTable` object (e.g. `pjt_table = _con.SQLTable(...)` in a `pjt_*`-backed module) built from `db_connectors`' `SQLField`/`SQLTable` helpers, plus `is_ok()`/`add_to_db()`/`update_fields()`-style functions that the owning table class's `_table_needs_update`/`_add_table_to_db`/`_update_table_in_db` call, and (for `global_db`-backed tables) `add_<entity>`/`add_<entity>s`/`add_records` seeding functions.

#### accessories.py

DDL/seed for the `accessories` global-catalog table (connector accessories not covered by a dedicated table of their own). Extended for the Molex scraper import with `add_json_records`, called from `build_database.py` in the sibling `harness_designer_database` repo.

#### adhesives.py

DDL/seed for the `adhesives` global-catalog table.

#### app_users.py

DDL/seed for the `app_users` table; unused (mirrors `global_db/app_users.py`, also unused).

#### boots.py

DDL/seed for the `boots` global-catalog table.

#### bundle_cover_layouts.py

DDL/seed for `pjt_bundle_cover_layouts`, the per-project placement rows for a bundle cover.

#### bundle_covers.py

DDL/seed for the `bundle_covers` global-catalog table (heat-shrink tubing and similar bundle-wrap parts).

#### bundle_paths.py

Schema for `pjt_bundle_paths` — one row per interior waypoint per bundle (`bundle_id`, `idx`, exactly one of `point3d_id`/`point_pegboard_id`, no schematic equivalent since bundles are never shown in schematic). NEW 2026-09-26, untested. NOT yet mirrored in the sibling `harness_designer_database` repo's `builder/create_database/`, which has already drifted (missing this file entirely, along with `wire_layouts.py`/`points_pegboard.py`).

#### cads.py

DDL/seed for the `cads` file/resource table (CAD file attachments for catalog parts).

#### cavities.py

DDL/seed for the `cavities` global-catalog table. Its position column defaults to `'"[0.0, 0.0, 0.0]"'` (a world-origin default, never NULL) — the intended pattern for a column that can never legitimately be `None`; contrast `models3d.py`'s `point3d` column, which defaults to `'NULL'`.

#### cavity_locks.py

DDL/seed for the `cavity_locks` global-catalog table.

#### circuits.py

DDL/seed for `pjt_circuits`, per-project circuit records. `return_type` (int, default 0) holds `circuit_solver.ReturnType`: 0 = chassis return (not modelled), 1 = mirrored.

#### colors.py

DDL/seed for the `colors` global lookup table.

#### concentric_layers.py

DDL/seed for `pjt_concentric_layers`, per-project concentric-cable layer rows.

#### concentric_wires.py

DDL/seed for `pjt_concentric_wires`, per-project concentric-cable wire-membership rows.

#### concentrics.py

DDL/seed for `pjt_concentrics`, per-project concentric-cable group rows. A row is attached to a bundle, to a transition branch, or -- when a bundle and a transition branch are connected -- to BOTH (they share the one row and the one `pjt_pegboard_sections` widget), so `bundle_id` and `transition_branch_id` are both nullable (`bundle_id` was NOT NULL until 2026-10-25, which made `handlers.transition_handler._create_branch_concentric`'s `insert(None, branch_id)` impossible); that at least one of them is set is not enforced in SQL or in `PJTConcentricsTable.insert`. PITFALL: `SQLTable.update_fields` only ADDS missing columns, so a project database created before the 2026-10-25 change keeps `bundle_id NOT NULL` until it is re-created. Concentric design: `CONCENTRIC_TWIST_DESIGN.md` (repo root).

#### covers.py

DDL/seed for the `covers` global-catalog table.

#### cpa_lock_types.py

DDL/seed for the `cpa_lock_types` global lookup table.

#### cpa_locks.py

DDL/seed for the `cpa_locks` global-catalog table.

#### datasheets.py

DDL/seed for the `datasheets` file/resource table.

#### deratings.py

DDL for the `deratings` global-catalog table (NEW 2026-10-24): a manufacturer's derating table for one terminal, wire or splice, one row per row of that table. Exactly one of `terminal_id`/`wire_id`/`splice_id` is set (enforced in `DeratingsTable.insert`, not in SQL), `idx` is the row's place in its part's table, and the rest are the table's own columns, each NULL when unused: `ambient_temp_c`, `conductor_count` (a bundling row), `max_amps`, `derating_factor` (a row needs one of the last two). `add_indexes(table)` indexes the three part columns on SQLite (a foreign key is not indexed there; MySQL's is); it is safe to run on every start and quiet on a database that cannot be written to. The COLUMNS ARE A PROPOSAL the user has not confirmed. Mirrored 2026-10-24 in the sibling `harness_designer_database` repo (`builder/create_database/deratings.py`, in `TABLE_MODULES` of `builder/build_database.py`, with its own `add_indexes(con)`); keep the two aligned. Nothing populates the table (there is no source data), so a built database has it empty, and a database built before this has no such table until the app creates it at start. Importing this module imports the schema of terminals, wires and splices, and `transitions`/`transition_branches` here only import cleanly when `transition_branches` goes first (an existing cycle), so import it late, after the part tables exist, the way `global_db/derating.py` does.

#### directions.py

DDL/seed for the `directions` global lookup table — one of the `NOT NULL` lookup-FK targets that gets referenced by an all-zero NIL id when the source seed data had none (see `housings.py` for the full convention).

#### families.py

DDL/seed for the `families` global lookup table — same NIL-id caveat as `directions.py`; a part's family/series choices are keyed off its manufacturer, so the corresponding editor controls are disabled when unset rather than showing an empty picker.

#### file_types.py

DDL/seed for the `file_types` lookup table, used by the generic file/resource tables (`datasheets.py`, `images.py`, `cads.py`, `models3d.py`).

#### genders.py

DDL/seed for the `genders` global lookup table — same NIL-id caveat as `directions.py`.

#### housings.py

DDL/seed for the `housings` global-catalog table, the largest/most-referenced catalog table. Its `NOT NULL` lookup FK columns (`direction_id`, `gender_id`, `family_id`, `series_id`, `cavity_lock_id`, `mfg_id`, `color_id`, ...) default to the all-zero NIL UUID (`id_generator.NIL_UUID`) when the source seed data had no value, and the referenced lookup table has no row for it. Verified against the live `harness_designer.db`: e.g. 3,400 of 46,665 housings have a NIL `direction_id`, 65 a NIL `gender_id`, 8,466 a NIL `family_id`, 16,069 a NIL `series_id`, 40,712 a NIL `cavity_lock_id`. The matching reference-mixin property returns `None` for a NIL id instead of crashing (`global_db/mixins/base.py`'s `NIL_ID`; it used to raise `IndexError` in `NameMixin.name`), and the matching `*Control.set_obj` shows blanks for `None`. Converted so far: direction, gender, cavity_lock, family, series, manufacturer, min_temp/max_temp. NOT yet converted: material, protection, color, and the `cpa_lock_type`/`ip_rating`/`stripe_color`-style references that live outside `global_db/mixins/`.

#### images.py

DDL/seed for the `images` file/resource table.

#### ip_fluids.py

DDL/seed for the `ip_fluids` table — one of the four IP (ingress protection) rating tables; an IP rating is composed of separate fluid/solid/supplementary sub-ratings rather than one flat lookup (see `global_db/ip/MAP.md`).

#### ip_ratings.py

DDL/seed for the `ip_ratings` table, the composite row referencing `ip_fluids`/`ip_solids`/`ip_supps`.

#### ip_solids.py

DDL/seed for the `ip_solids` table — the solid-ingress sub-rating (see `ip_fluids.py`).

#### ip_supps.py

DDL/seed for the `ip_supps` table — the supplementary sub-rating (see `ip_fluids.py`).

#### manufacturers.py

DDL/seed for the `manufacturers` global lookup table — converted to the NIL-id → `None` convention (see `housings.py`).

#### materials.py

DDL/seed for the `materials` global lookup table — NOT yet converted to the NIL-id → `None` convention (see `housings.py`).

#### models3d.py

DDL/seed for the `models3d` file/resource table (3D model storage). Its `point3d` column defaults to `'NULL'` — unlike `cavities.py`'s position column, this is the one accepted exception: `angle3d`/`quat3d` NULL on this table is meaningful (it triggers the part-orientation dialog on first download), so these should not be defaulted away the way an ordinary position column would be.

#### notes.py

DDL/seed for `pjt_notes`, per-project free-floating note rows.

#### pegboard_sections.py

DDL for `pjt_pegboard_sections` (NEW 2026-10-25): the placement of a concentric-twist cross-section widget (`ui/concentric_section/`) on the Peg Board, drawn into a buffer and shown as a GL texture the same way the floating wire tables are. Columns: `concentric_id` (UNIQUE, NOT NULL -- exactly ONE widget per concentric, so a connected bundle and transition branch, which share one concentric, share one widget), `point_pegboard_id` (the widget's CENTER; unlike `pegboard_tables.py` this row OWNS its own `pjt_points_pegboard` row rather than sharing an anchor's), `size` (`str((width, height))` in world mm, same convention as `pegboard_tables.size`) and `is_visible_pegboard`. What the widget is attached to is not stored here -- it is whatever the concentric's `bundle_id` / `transition_branch_id` point at. No facade object or GL code reads this table yet.

#### pegboard_tables.py

DDL/seed for `pjt_pegboard_tables`, the Excel-like data-table-overlay rows for the Peg Board Editor (one row per anchor — housing, bundle, or transition — that has a floating wire table). The row's own `position_pegboard` point is deliberately the SAME `pjt_points_pegboard` row as the owning anchor's own `table_point_peg_id` (see `project_db/mixins/table_position_peg.py`), not a fresh point of its own, so the table and its anchor can be found from each other by equality lookup without a forward FK on either side.

#### platings.py

DDL/seed for the `platings` global lookup table.

#### points2d.py

Schema for `pjt_points2d`. As of 2026-09-24 has a real `z` column; `x`/`y`/`z` map 1:1 to `Point`'s own axes (the schematic plane is X/Z, so a schematic point's `y` is always `0.0`). Before that date the table's "y" column actually held what callers treated as the Z axis, and reading `.y` off a 2D `Point` silently zeroed it — fixed by adding the real `z` column plus a one-time in-place migration in `PJTPoints2DTable._update_table_in_db` (adds `z` with default 0.0, then backfills `z = y, y = 0.0`, only when `z` was missing) so old rows read back the same position. The mirror schema in the sibling `harness_designer_database` repo got the same column.

#### points3d.py

Schema for `pjt_points3d`, the real 3D waypoint/anchor-position table — same singleton/attach/clone/self-heal lifecycle as `points_pegboard.py`'s `pjt_points_pegboard`, distinguished by a 2-byte `b'3d'` `Point.db_id` clone-detection suffix.

#### points_pegboard.py

Schema for `pjt_points_pegboard` — same x/y/z + `parent_point_id` shape as `points3d.py`/`points2d.py`, distinguished by an 8-byte `b'pegboard'` `Point.db_id` clone-detection suffix (vs. `points3d.py`'s 2-byte `b'3d'`). Its `wire_id`/`bundle_id`/`idx` waypoint-tag columns were REMOVED 2026-09-26 (a point is now pure geometry; waypoint order/ownership moved to `pjt_wire_paths`/`pjt_bundle_paths`) — existing project databases still carry those old, now-unused columns from before the migration.

#### projects.py

DDL/seed for the `projects` table (project-row/app-wide metadata, one row per project).

#### protections.py

DDL/seed for the `protections` global lookup table — NOT yet converted to the NIL-id → `None` convention (see `housings.py`).

#### resource_state.py

DDL/seed for the `resource_state` global table; the app creates it itself on first run if missing, and it starts empty.

#### seal_types.py

DDL/seed for the `seal_types` global lookup table.

#### seals.py

DDL/seed for the `seals` global-catalog table.

#### series.py

DDL/seed for the `series` global lookup table — same NIL-id caveat as `families.py` (converted, control disabled when unset).

#### settings.py

DDL/seed for the `settings` project-row/app-wide table.

#### shapes.py

DDL/seed for the `shapes` global lookup table.

#### splice_types.py

DDL/seed for the `splice_types` global lookup table.

#### splices.py

DDL/seed for the `splices` global-catalog table. Its project table `pjt_splices` has a nullable `operating_temp` (degrees Celsius, NULL = not set), added 2026-10-24 on the project side only: the global parts database is built by the sibling repo, so nothing global changed.

#### temperatures.py

DDL/seed for the `temperatures` global lookup table — converted to the NIL-id → `None` convention (`min_temp`/`max_temp`, see `housings.py`).

#### terminals.py

DDL/seed for the `terminals` global-catalog table. Its project table `pjt_terminals` has a nullable `operating_temp` (degrees Celsius, NULL = not set), added 2026-10-24 on the project side only: the global parts database is built by the sibling repo, so nothing global changed. It also has `load_type` (int, default 0 = resistive).

#### tpa_locks.py

DDL/seed for the `tpa_locks` global-catalog table.

#### transition_branches.py

DDL/seed for the `transition_branches` global-catalog table. Has a confirmed `branches` off-by-one data bug (`global_db/transition.py`; see `TRANSITION_DESIGN.md`) and 5 catalog rows with a stray `bulb_offset` on the wrong branch.

#### transition_series.py

DDL/seed for the `transition_series` global lookup table.

#### transitions.py

DDL/seed for the `transitions` global-catalog table. Has 9 confirmed blank catalog rows (see `TRANSITION_DESIGN.md`).

#### used_parts.py

DDL/seed for the `used_parts` history table — tracks which accessory parts (cover/terminal/tpa_lock/cpa_lock, all nullable FKs, `ON DELETE CASCADE`) have previously been used with a given housing (`housing_id`, not-null FK, `ON DELETE CASCADE`). A history table, not a placeable part type.

#### wire_layouts.py

Schema for `pjt_wire_layouts`, the per-view wire-waypoint placement rows backing `objects/wire_layout.py`'s `WireLayout`.

#### wire_markers.py

DDL/seed for the `wire_markers` global-catalog table.

#### wire_paths.py

Schema for `pjt_wire_paths` — one row per interior waypoint per wire per view (`wire_id`, `idx`, exactly one of `point3d_id`/`point_pegboard_id`/`point2d_id`, plus optional `bundle_id`/`concentric_id`/`transition_id`/`transition_branch_id` tags; a wire's start/stop stay columns on `pjt_wires` itself). NEW 2026-09-26, untested. NOT yet mirrored in the sibling `harness_designer_database` repo's `builder/create_database/`, same drift warning as `bundle_paths.py`.

#### wire_service_loops.py

DDL/seed for the `wire_service_loops` global-catalog table. Its project table `pjt_wire_service_loops` has a nullable `operating_temp` (degrees Celsius, NULL = not set), added 2026-10-24 on the project side only: the global parts database is built by the sibling repo, so nothing global changed.

#### wire_types.py

Schema, default rows ("Wire" is the nil-UUID default row, plus "Coaxial"/"Ribbon") and `get_wire_type_id()` for the `wire_types` lookup table; `wires.py` has the matching `wire_type_id` column and `add_wire(wire_type=...)`. Mirrored in the sibling `harness_designer_database` repo (`builder/create_database/wire_types.py`, seeded from `Universal/wire_types.json`) — unlike `wire_paths.py`/`bundle_paths.py` above, this one IS kept in sync there.

#### wires.py

DDL/seed for the `wires` global-catalog table; has the `wire_type_id` column matching `wire_types.py` and `add_wire(wire_type=...)`. Its project table `pjt_wires` has a nullable `operating_temp` (degrees Celsius, NULL = not set), added 2026-10-24 on the project side only: the global parts database is built by the sibling repo, so nothing global changed.
