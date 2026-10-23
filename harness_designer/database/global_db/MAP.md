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

(~1300 lines) Table base classes — `EntryBase`/`TableBase`/`GLBTables`, plus `_EntrySingleton` (the per-row singleton metaclass) and `DefaultStoredValue`/`DefaultStoredValueType`. `TableBase._row_cache` is a per-row read/write-through cache (`db_id -> {column: value}`), NOT a per-table bulk load (see `WRITE_DESIGN.md` section 4.9 at the repo root for the full design) — populated once in `EntryBase.__init__` (every row is an `_EntrySingleton`, so this only runs once per row) and evicted by `_EntrySingleton`'s existing weakref cleanup once nothing references that row's wrapper anymore. `select()`/`update()`/`delete()`/`insert()` all read or write through it. **Pitfall:** a write made on another database connection (the image/model worker processes' `UPDATE ... SET uuid=...`) bypasses the cache, so `select()` keeps returning the old value for as long as that row's wrapper is alive -- resetting an entry's own `_stored_*` fields is not enough. Call `TableBase.reload_row(db_id)` first (what `Image.download_complete` and `Model3D.download_complete` do); without it a freshly downloaded image never appeared until the app restarted, and a freshly converted model's `uuid`, `file_type_id`, `vertex_count`, `aabb` and `obb` (the columns its worker's `UPDATE` writes, `model_process.py`) would be served stale from the row cache -- `aabb`/`obb` included, since `Model3D` re-reads those through `select()` instead of caching them on the instance.

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

`Models3DTable`/`Model3D` — 3D model storage. `angle3d`/`quat3d` NULL on this table is meaningful (triggers the part-orientation dialog on first download) — don't default those away the way a position column would be.

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

`Splice` row/table class for the `splices` global-catalog table.

#### splice_types.py

`SpliceType` row/table class for the `splice_types` global lookup table.

#### temperature.py

`Temperature` row/table class for the `temperatures` global lookup table — converted to the NIL-id → `None` convention (`min_temp`/`max_temp`).

#### terminal.py

`Terminal` row/table class for the `terminals` global-catalog table.

#### tpa_lock.py

`TPALock` row/table class for the `tpa_locks` global-catalog table.

#### transition.py

`Transition` row/table class for the `transitions` global-catalog table (+ `transition_branch.py` for its branches). Has a confirmed `branches` off-by-one bug (see `TRANSITION_DESIGN.md`).

#### transition_branch.py

`TransitionBranch` row/table class for the `transition_branches` global-catalog table. `offset`/`bulb_offset`/`angle` are all literal world-space values per branch, not rotated with the branch (confirmed against `build123d.Plane.rotated()`'s real behavior) — see `TRANSITION_DESIGN.md`. 5 catalog rows have a stray `bulb_offset` on the wrong branch.

#### used_part.py

`used_parts` table — tracks which accessory parts (`tpa_lock`/`cpa_lock`/`cover`/`terminal`, all nullable FKs, `ON DELETE CASCADE`) have previously been used with a given housing (`housing_id`, not-null FK, `ON DELETE CASCADE`). A history table, not a placeable part type — no `project_db`/`objects`/`handlers` counterpart, mirrors `resource_state.py`'s shape. No UI surfaces this per-housing yet.

#### wire.py

`Wire` row/table class for the `wires` global-catalog table. Its `stripe_color` column is the precedent for the NIL-id → `None` convention used elsewhere (a reference "outside `mixins/`" that already returns `None` rather than crashing).

#### wire_marker.py

`WireMarker` row/table class for the `wire_markers` global-catalog table.

#### wire_type.py

`wire_types` lookup table — "Wire" is the nil default row, plus "Coaxial"/"Ribbon"; `wires.wire_type_id` points at it.

## FOLDERS

#### ip/

IP rating tables — see `ip/MAP.md`.

#### mixins/

Column mixins shared across the part-entity classes above — see `mixins/MAP.md`. Check these before assuming a property/method is missing: DB classes here commonly inherit from `mixins/` (e.g. `DimensionMixin`, `NameMixin`, `CompatTerminalsMixin`) rather than defining a property directly — grep the mixin files before concluding something doesn't exist, and ask before substituting individual-column setters for a mixin-provided composite setter (e.g. don't replace `db_obj.size = (w, h, l)`, one UPDATE via `DimensionMixin.size`, with three individual column setters).
