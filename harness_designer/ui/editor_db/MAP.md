## FILES

#### __init__.py

Package init for the parts-database editor dock; no content beyond the standard package marker. This dock is a `QTabWidget` of one page per catalog part type, for editing rows directly in `global_db` (the shared parts catalog) — **not** project data. This is a deliberately separate path from the project-object creation flow: per CODEBASE_MAP.md's "Catalog editing" note, these files edit the `global_db` table directly and never touch `pjt_*` project tables or scene objects, in contrast with the normal "Creation flow" (`handlers/*_handler.py` → `part_search.py` → insert a `pjt_*` row → build the `objects/` wrapper → render) and "Project load flow" (iterate `pjt_*` rows on load) — catalog editing bypasses all of that. Don't confuse this editor's job with the per-project object editors (`editor_3d`, `editor_schematic`, `editor_pegboard`, `editor_obj`) — rows edited here are catalog definitions, never a specific project's placed parts.

#### accessory.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for accessories plus any type-specific column/icon logic, importing its matching `database.global_db.accessory` module only under `TYPE_CHECKING`.

#### base.py

The shared foundation every per-type page builds on (~1400 lines). `EditorDBConfig` (`metaclass=config.ConfigDB`) is the config schema for this editor. `ScrollTracker` tracks/restores table scroll position across refreshes. `EditorList(QtWidgets.QTableView)` is the shared table base class every per-type page (`WiresPage`, `HousingsPage`, etc. in the sibling files) subclasses — `GetLabel()`/`GetSelection()`/`Refresh()`/`Destroy()` plus the bulk of the generic row-editing/column plumbing. **Hidden values (2026-11-05):** a page can return values that are not columns from the SAME paged query: `_hidden_fields` (names of columns of the table, selected as they are) and `_hidden_subselects` (alias -> a scalar sub-select written with `paged.id`; it is put in the OUTER select, so it runs only for the rows of the requested page, not for every row of the table). A row from `get_row` is `(RowNum, the column_mapping columns, image_id if the page has images, the hidden fields, the hidden sub-selects)`; `hidden_index(name)` gives a hidden value's position. Not allowed together with `_has_model_3d` (that flag is read from the end of the row; `_build_query` raises). On the scratch catalog (147,808 wires) the wires page's hidden values add about 20 to 50 ms to a page query of about 690 ms.

#### boot.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for boots plus any type-specific column/icon logic, importing its matching `database.global_db.boot` module only under `TYPE_CHECKING`.

#### bundle_cover.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for bundle covers plus any type-specific column/icon logic, importing its matching `database.global_db.bundle_cover` module only under `TYPE_CHECKING`.

#### cover.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for covers plus any type-specific column/icon logic, importing its matching `database.global_db.cover` module only under `TYPE_CHECKING`.

#### cpa_lock.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for CPA locks plus any type-specific column/icon logic, importing its matching `database.global_db.cpa_lock` module only under `TYPE_CHECKING`.

#### edit_dialog.py

Defines `EditDialog(dialog_base.BaseDialog)` — the generic add/edit-one-row dialog opened from a page's table, built from a db_obj's own field set rather than being type-specific.

#### editordb.py

Defines `EditorDB(DockBase)` — the dock wrapper, and `EditorDBPanel(QtWidgets.QTabWidget)` — hosts one page per part type as a tab. `EditorDB.load_db(g_db)` loads a `global_db.GLBTables` connection into every page. Per-type pages are exposed as properties: `accessories`, `boots`, `bundle_covers`, `covers`, `cpa_locks`, `housings`, `seals`, `splices`, `terminals`, `tpa_locks`, `transitions`, `wires`, `wire_markers`.

#### housing.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for housings (e.g. `HousingsPage(base.EditorList)`) plus any type-specific column/icon logic, importing its matching `database.global_db.housing` module only under `TYPE_CHECKING`.

#### seal.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for seals plus any type-specific column/icon logic, importing its matching `database.global_db.seal` module only under `TYPE_CHECKING`.

#### splice.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for splices plus any type-specific column/icon logic, importing its matching `database.global_db.splice` module only under `TYPE_CHECKING`.

#### terminal.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for terminals plus any type-specific column/icon logic, importing its matching `database.global_db.terminal` module only under `TYPE_CHECKING`.

#### tpa_lock.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for TPA locks plus any type-specific column/icon logic, importing its matching `database.global_db.tpa_lock` module only under `TYPE_CHECKING`.

#### transition.py

One file per catalog part type pattern (see `wire.py` below for the representative shape): defines an `EditorList` subclass for transitions plus any type-specific column/icon logic, importing its matching `database.global_db.transition` module only under `TYPE_CHECKING`.

#### wire.py

Defines `WiresPage(base.EditorList)` plus wire-specific column/icon logic (e.g. `WiresPage._get_icon`, whose picture comes from `database/global_db/wire_image.py`, shared with the peg-board wire table, the BOM and the circuit editor), importing `database.global_db.wire` only under `TYPE_CHECKING`. **The picture is drawn from the list's own query, not from a `Wire` row** (a row object per line, plus its conductors, would slow the list): `_hidden_fields` = `color_id`, `stripe_color_id`, `core_material_id`, and the hidden sub-select `conductors` returns one `idx,hex(color),hex(stripe),hex(core)` text per conductor of the wire, joined with `;`. `WiresPage._image_row(row)` wraps those and the `wire_type_name`, `num_conductors`, `shielded` and `tpi` columns in a `wire_images.WireImageRow` (a NamedTuple with the same attribute names as `Wire`; `WireImageRow.from_query` / `parse_conductors` do the parsing) and `_get_icon` passes that to `wire_image.build_wire_icon`. If the picture needs another wire column, add it to `_hidden_fields` and to `WireImageRow` — the representative example of the one-file-per-catalog-part-type pattern shared by `accessory.py`, `boot.py`, `bundle_cover.py`, `cover.py`, `cpa_lock.py`, `housing.py`, `seal.py`, `splice.py`, `terminal.py`, `tpa_lock.py`, and `transition.py`. Note: this file was modified in the working tree as of the last git status check at the time this doc pass was written — check `git diff` before assuming its current content matches this summary if picking up related work.

#### wire_marker.py

One file per catalog part type pattern (see `wire.py` above for the representative shape): defines an `EditorList` subclass for wire markers plus any type-specific column/icon logic, importing its matching `database.global_db.wire_marker` module only under `TYPE_CHECKING`.
