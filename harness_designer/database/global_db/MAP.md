## FILES

#### __init__.py

Package init for `global_db`; no real logic of its own. This is the shared parts catalog: one file per entity, table names singular (`housing`, `wire`, ...) — the middle layer of the "same-name modules" pipeline described in `database/MAP.md`, created/seeded by `create_database/` and referenced by a FK from the corresponding `project_db/pjt_*` row (a placed instance points at its catalog part via `part_id`).

#### accessory.py

`Accessory` row/table class for the `accessories` global-catalog table.

#### adhesive.py

`Adhesive` row/table class for the `adhesives` global-catalog table.

#### app_users.py

Unused.

#### bases.py

(~1300 lines) Table base classes — `EntryBase`/`TableBase`/`GLBTables`, plus `_EntrySingleton` (the per-row singleton metaclass) and `DefaultStoredValue`/`DefaultStoredValueType`. `TableBase._row_cache` is a per-row read/write-through cache (`db_id -> {column: value}`), NOT a per-table bulk load (see `WRITE_DESIGN.md` section 4.9 at the repo root for the full design) — populated once in `EntryBase.__init__` (every row is an `_EntrySingleton`, so this only runs once per row) and evicted by `_EntrySingleton`'s existing weakref cleanup once nothing references that row's wrapper anymore. `select()`/`update()`/`delete()`/`insert()` all read or write through it. **Pitfall:** a write made on another database connection (the image/model worker processes' `UPDATE ... SET uuid=...`) bypasses the cache, so `select()` keeps returning the old value for as long as that row's wrapper is alive -- resetting an entry's own `_stored_*` fields is not enough. Call `TableBase.reload_row(db_id)` first (what `Image.download_complete` and `Model3D.download_complete` do); without it a freshly downloaded image never appeared until the app restarted, and a freshly converted model's `uuid`, `file_type_id`, `vertex_count`, `aabb` and `obb` (the columns its worker's `UPDATE` writes, `model_process.py`) would be served stale from the row cache -- `aabb`/`obb` included, since `Model3D` re-reads those through `select()` instead of caching them on the instance. `GLBTables` also creates the `deratings` table (`deratings_table`) right after the wires table.

#### boot.py

`Boot` row/table class for the `boots` global-catalog table.

#### bundle_cover.py

`BundleCover` row/table class for the `bundle_covers` global-catalog table (heat-shrink tubing and similar bundle-wrap parts).

#### cad.py

`Cad` row/table class for the `cads` file/resource table.

#### cavity.py

`Cavity` row/table class for the `cavities` global-catalog table.

#### cavity_lock.py

`CavityLock` row/table class for the `cavity_locks` global-catalog table.

#### color.py

`Color` row/table class for the `colors` global lookup table.

#### cover.py

`Cover` row/table class for the `covers` global-catalog table.

#### cpa_lock.py

`CPALock` row/table class for the `cpa_locks` global-catalog table.

#### cpa_lock_type.py

`CPALockType` row/table class for the `cpa_lock_types` global lookup table.

#### datasheet.py

`Datasheet` row/table class for the `datasheets` file/resource table.

#### derating.py

`DeratingsTable` and `Derating` for the `deratings` table (NEW 2026-10-24; schema in `create_database/deratings.py`). `Derating` is a plain `NamedTuple` row (`id`, `idx`, the three part ids, `ambient_temp_c`, `conductor_count`, `max_amps`, `derating_factor`), not a cached row wrapper. THIS TABLE CLASS is the cache: `for_part(part_table_name, part_id)` reads a part's whole derating table in ONE query (`ORDER BY idx`) the first time and serves it from memory after (a part with no table is remembered as having none). The terminals, wires and splices tables call it, through `DeratingMixin.load_deratings()`, from their own `__getitem__` as they load a part, so the table is there before anything asks. `insert` (refuses a row that does not belong to exactly one part, or has neither `max_amps` nor `derating_factor`) and `forget` drop a part's entry; `__iter__`/`__getitem__` read straight from the database. The schema module is imported late (`_schema()`), like the other global tables' schema modules, because importing it at the top pulls `create_database.wires` into the import chain before an existing cycle there can resolve. Registered in `GLBTables` right after the wires table (its foreign keys point at terminals, wires and splices) as `deratings_table`.

#### wire_conductor.py

`WireConductor`, `ShieldConductor` and `WireConductorsTable` for the `wire_conductors` table (NEW 2026-11-03; schema in `create_database/wire_conductors.py`). **`WireConductor` is a catalog row class (2026-11-06, was a read-only `NamedTuple`)**: `EntryBase` + `ColorMixin` + `MaterialMixin`, one column per property with a setter that writes the catalog row (`_Column` for the plain ones; the three sizes are kept in step as `Wire` does), and it answers what a `Wire` does so that it can be a `part`: `color`, `stripe_color`, `material`, `core_material`, `conductor_dia_mm`, `size_mm2`, `size_awg`, `strands`, `od_mm`, `resistance_1km` (+ `_1kft` / `_m` / `_ft`), the weights (the cable's shared among its conductors and the shield), fixed answers (`num_conductors` 1, not twisted, not a cable, `cable_style` WIRE, no `conductors`), and `wire` (the cable's `Wire`), with anything else (manufacturer, part number, temperatures, derating ...) falling through to the cable by `__getattr__`. `od_mm` is the stored value or, when the catalog gave none (0), the size the conductor has in its cable's cross-section; `stored_od_mm` is the raw column (the cable's own size code must use it, `od_mm` asks the cable). An edit is global: every placed cable of the part changes. `ShieldConductor(wire)` stands in for a shield, which has no row (read-only, fixed values: "no color", a fraction of a conductor's size, no resistance). A conductor is the `part` of a placed cable's conductor row and of its leads (`PJTCableConductor.part`, `PJTWire.part`). THE TABLE CLASS caches a wire's conductors: `for_wire(wire_id)` reads the set once and remembers it (empty for a single-conductor wire); `WiresTable.__getitem__` calls `wire.load_conductors()` so they are already here when something asks `wire.conductors`. `insert(...)` adds one and drops that wire's cached set. The catalog itself is built by the sibling `harness_designer_database` repo. Registered in `bases.py` as `GLBTables.wire_conductors_table`, after `WiresTable`. Editing UI: the Conductors tab of `WireControl` (`wire.py`: `WireConductorsControl` / `WireConductorControl`).

#### direction.py

`Direction` row/table class for the `directions` global lookup table — converted to the NIL-id → `None` convention (see `housing.py`'s paragraph for the full convention: a `NOT NULL` lookup FK defaults to an all-zero NIL id when seed data had none, and the reference-mixin property returns `None` rather than crashing).

#### family.py

`Family` row/table class for the `families` global lookup table — converted to the NIL-id → `None` convention; the matching editor control is disabled when unset since family/series name choices are keyed off the manufacturer.

#### file_types.py

`FileType` row/table class for the `file_types` lookup table, used by the generic file/resource entities (`datasheet.py`, `image.py`, `cad.py`, `model3d.py`).

#### gender.py

`Gender` row/table class for the `genders` global lookup table — converted to the NIL-id → `None` convention.

#### housing.py

`Housing` row/table class for the `housings` global-catalog table, the largest/most-referenced catalog table. **NIL-id convention (added 2026-09-24):** its `NOT NULL` lookup FK columns (`direction_id`, `gender_id`, `family_id`, `series_id`, `cavity_lock_id`, `mfg_id`, `color_id`, ...) default to `X'00000000000000000000000000000000'` (`id_generator.NIL_UUID`) when the source seed data had no value, and the referenced lookup table has NO row for that id. Verified against the live `harness_designer.db`: e.g. 3,400 of 46,665 housings have a NIL `direction_id`, 65 a NIL `gender_id`, 8,466 a NIL `family_id`, 16,069 a NIL `series_id`, 40,712 a NIL `cavity_lock_id`. Building an entry for one of these and reading `.name` used to crash with `IndexError` in `NameMixin.name`. The reference-mixin property now returns `None` for a NIL id (`mixins/base.py`'s `NIL_ID`) and the matching `*Control.set_obj` shows blanks for `None`. Converted so far: direction, gender, cavity_lock, family, series, manufacturer, min_temp/max_temp. NOT yet converted (same pattern, just not hit yet): material, protection, color, and the `cpa_lock_type`/`ip_rating`/`stripe_color`-style references outside `mixins/`.

#### image.py

`Image` row/table class for the `images` file/resource table.

#### manufacturer.py

`Manufacturer` row/table class for the `manufacturers` global lookup table — converted to the NIL-id → `None` convention.

#### material.py

`Material` row/table class for the `materials` global lookup table — NOT yet converted to the NIL-id → `None` convention.

#### model3d.py

`Models3DTable`/`Model3D` — 3D model storage. `angle3d`/`quat3d` NULL on this table is meaningful (triggers the part-orientation dialog on first download) — don't default those away the way a position column would be. `Model3D.data_path` is `<model_path>/<uuid[:2]>/<uuid>.hdm`; a model saved before the `.hdm` format (`<uuid>.npy`) is upgraded in place there the first time it is asked for (see `utils/hdm.py`).

#### plating.py

`Plating` row/table class for the `platings` global lookup table.

#### protection.py

`Protection` row/table class for the `protections` global lookup table — NOT yet converted to the NIL-id → `None` convention.

#### resource_state.py

Tracks resource sync state.

#### seal.py

`Seal` row/table class for the `seals` global-catalog table.

#### seal_type.py

`SealType` row/table class for the `seal_types` global lookup table.

#### series.py

`Series` row/table class for the `series` global lookup table — converted to the NIL-id → `None` convention; same disabled-when-unset control behavior as `family.py`.

#### setting.py

Row/table class backing a settings entity (distinct from `database/config_db.py`'s app-config table).

#### shape.py

`Shape` row/table class for the `shapes` global lookup table.

#### splice.py

`Splice` row/table class for the `splices` global-catalog table. Has `DeratingMixin`; the table's `__getitem__` calls `load_deratings()` on the part it hands back, so the part's manufacturer derating table (`deratings`) is read with the part. `SplicesTable.__getitem__` by a string looks the splice up in a `name` column that the `splices` table does not have (found 2026-10-24, not fixed; terminals and wires use `part_number`).

#### splice_types.py

`SpliceType` row/table class for the `splice_types` global lookup table.

#### temperature.py

`Temperature` row/table class for the `temperatures` global lookup table — converted to the NIL-id → `None` convention (`min_temp`/`max_temp`).

#### terminal.py

`Terminal` row/table class for the `terminals` global-catalog table. Has `DeratingMixin`; the table's `__getitem__` calls `load_deratings()` on the part it hands back, so the part's manufacturer derating table (`deratings`) is read with the part.

#### tpa_lock.py

`TPALock` row/table class for the `tpa_locks` global-catalog table.

#### transition.py

`Transition` row/table class for the `transitions` global-catalog table (+ `transition_branch.py` for its branches). Has a confirmed `branches` off-by-one bug (see `TRANSITION_DESIGN.md`).

#### transition_branch.py

`TransitionBranch` row/table class for the `transition_branches` global-catalog table. `offset`/`bulb_offset`/`angle` are all literal world-space values per branch, not rotated with the branch (confirmed against `build123d.Plane.rotated()`'s real behavior) — see `TRANSITION_DESIGN.md`. 5 catalog rows have a stray `bulb_offset` on the wrong branch.

#### used_part.py

`used_parts` table — tracks which accessory parts (`tpa_lock`/`cpa_lock`/`cover`/`terminal`, all nullable FKs, `ON DELETE CASCADE`) have previously been used with a given housing (`housing_id`, not-null FK, `ON DELETE CASCADE`). A history table, not a placeable part type — no `project_db`/`objects`/`handlers` counterpart, mirrors `resource_state.py`'s shape. No UI surfaces this per-housing yet.

#### wire.py

`Wire` row/table class for the `wires` global-catalog table. Its `stripe_color` column is the precedent for the NIL-id → `None` convention used elsewhere (a reference "outside `mixins/`" that already returns `None` rather than crashing). Has `DeratingMixin`; the table's `__getitem__` calls `load_deratings()` on the part it hands back, so the part's manufacturer derating table (`deratings`) is read with the part. `Wire` also mixes in `WireConductorMixin` (`wire.conductors`); `Wire.stripe_color` returns `None` for the "no color" id (`id_generator.NO_COLOR_UUID`), NOT for the nil id, which is Black (2026-11-03). **Conductors tab (2026-11-06):** `WireControl` has a Conductors tab, shown only for a wire with `wire_conductors` rows: a notebook (`WireConductorsControl`) with one tab per conductor (`WireConductorControl`: colour, stripe, insulation, core, the three sizes, strands, outside diameter, resistance). It edits the catalog rows, so a change is global, and afterwards `Project.reload_cable_looks(wire_id)` redraws every placed cable of the part (and its leads). The object editor reaches it through the Part tab of a wire, a cable, a conductor or a lead.

#### wire_image.py

Only `build_wire_icon(row, size=64)` now (CHANGED 2026-11-05: the decision which picture a wire gets moved to `image/wire_images.build_image`, reached as `images.build_wire(row)`). It returns the list icon of that picture and shares ONE `QIcon` per (picture, size) in `_ICONS`, so rows of a list that look the same (colours, jacket, shield; the size and part number play no part) hold a reference to the same icon instead of one pixmap per part; it is what the wire editor and the peg-board wire table store in their `bitmap_indexes`. `row` is a catalog `Wire`, a project `PJTWire`, a project `PJTWireServiceLoop` or a `wire_images.WireImageRow` (what the parts editor's list passes, built from its own query). Returns `None` when the row cannot be drawn (the caller then shows `images.no_image`). GUI thread only. `objects/bom.py` (`resolve_wire_icon`) and `ui/editor_circuit/editor_widget.py` (`_wire_part_images`) call `images.build_wire(row)` directly.

#### wire_marker.py

`WireMarker` row/table class for the `wire_markers` global-catalog table.

#### wire_type.py

`wire_types` lookup table — "Wire" is the nil default row, plus "Coaxial"/"Ribbon"; `wires.wire_type_id` points at it.

## FOLDERS

#### ip/

IP rating tables — see `ip/MAP.md`.

#### mixins/

Column mixins shared across the part-entity classes above — see `mixins/MAP.md`. Check these before assuming a property/method is missing: DB classes here commonly inherit from `mixins/` (e.g. `DimensionMixin`, `NameMixin`, `CompatTerminalsMixin`) rather than defining a property directly — grep the mixin files before concluding something doesn't exist, and ask before substituting individual-column setters for a mixin-provided composite setter (e.g. don't replace `db_obj.size = (w, h, l)`, one UPDATE via `DimensionMixin.size`, with three individual column setters).

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### The app no longer self-seeds catalog/lookup tables: the downloaded DB arrives pre-built (2026-10-20)
`sqlite_connector/connector.py`'s `connect()` downloads one pre-built, pre-seeded `harness_designer.db` (the `harness_designer_database.zip` release asset) on first run, so rows already exist. The old per-table JSON seeding (`_add_table_to_db`'s `self._con.db_data.open(splash)` + `<module>.add_records(...)`, the `_load_database` overrides that only did that, `ConnectorBase.db_data`, and `db_connectors/db_data.py`'s `DBData`) was dead, broken code (`AttributeError: 'SQLConnector' object has no attribute 'db_data'`) and was removed. Do not reintroduce a `db_data`-style call or resurrect `db_data.py`. If a table needs real default/seed rows, that is a full-DB-release concern (the sibling `harness_designer_database` repo), not `_add_table_to_db`'s.
- **Kept on the user's instruction:** `<module>.table.add_to_db(self)` (table creation) and `_table_needs_update()`/`_update_table_in_db()` (adding missing columns) in every `_add_table_to_db`, so a table or column missing from an older downloaded DB is still created/migrated in place. `wire_types` therefore gets created empty on an old DB (its 3-row self-seed is gone).
- **`add_records` in `database/create_database/*.py`:** the user had every body replaced by `raise NotImplementedError` (2026-10-26, "actually unused"), keeping signature, `@_check_types.do` and docstring (32 files). Five were NOT gutted because `global_db/` still calls them from `_add_table_to_db`: `settings.add_records` (creates the model/image/cad/datasheet folders and inserts the four `*_path` setting rows: real first-run work) and `ip_fluids`/`ip_solids`/`ip_supps`/`ip_ratings.add_records` (via `global_db/ip/`). Gutting those is a pending question for the user. The other seeding helpers (`add_boots`, `add_housings`, `add_wire_type`, ...) are untouched.

#### Global-DB lookup references use an all-zero NIL id for "not set" (added 2026-09-24)
`NOT NULL` FK columns in `create_database/*` (`direction_id`, `gender_id`, `family_id`, `series_id`, `cavity_lock_id`, `mfg_id`, `color_id`, ...) default to `X'00000000000000000000000000000000'` (`id_generator.NIL_UUID`) when the source had no value, and (in older DBs) the lookup table has no row for it: e.g. 3,400 of 46,665 housings had a NIL `direction_id`, 8,466 a NIL `family_id`, 40,712 a NIL `cavity_lock_id`. Reading `.name` off such an entry used to crash with `IndexError` in `NameMixin.name`.
- **Convention:** the reference-mixin property returns `None` for a NIL id (`mixins/base.py` `NIL_ID`) and the matching `*Control.set_obj` shows blanks. Done for `direction`, `gender`, `cavity_lock`, `manufacturer`, `min_temp`/`max_temp`. Precedent: `global_db/wire.py` stripe_color.
- **Reversed for `family` and `series` (user, 2026-10-23: "series should not be returning None. neither should family"):** `FamilyMixin.family`/`SeriesMixin.series` return the real nil-id row ("No Family"/"No Series", which exist in the downloaded DB), so readers like the 3D terminal's `self._part.series.name.lower()` just work. `family_id`/`series_id` map a column that reads back `None` to `NIL_ID` ("None is different than NIL") and `family`/`series` read through them. Their controls test `== NIL_ID` instead of `is None` and stay disabled when unset, otherwise editing the name/description would rewrite the shared default row.
- Not yet converted (same pattern, not hit yet): `material`, `protection`, `color`, and the `cpa_lock_type`/`ip_rating`/`stripe_color`-style references outside `mixins/`.
