## FILES

#### __init__.py

No imports found -- a plain empty package marker, no re-exports.

#### about_dialog.py

`AboutDialog` -- app info, an update check against the GitHub releases API (`_UpdateCheckWorker`, a `QThread`), and a package-credits/license viewer (`_PackageInfo`) built from `importlib.metadata` over installed dist-info dirs, including Python itself.

#### add_note.py

`AddNoteDialog` -- create/edit a project note.

#### add_project.py

`AddProjectDialog` -- new-project creation (name, location, color).

#### bom_dialog.py

`BomDialog` -- the BOM Builder: parts list, housing tree (`_HousingTree`), wire cut sheet (`_WireCutSheetTree`), bundle cut sheet (`_BundleCutSheetTree`), with live wire/bundle fabrication-excess controls (`_BomToolbarRow`).

#### bundle_wires_dialog.py

`BundleWiresDialog` -- read-only listing of the wires contained within a bundle.

#### closing_dialog.py

`ClosingDialog` -- borderless, button-less progress dialog shown while the app shuts down (deliberately has no buttons at all, since there's nothing to confirm/cancel during shutdown).

#### database_error_dialog.py

`DatabaseErrorDialog` -- shows a database error with its full context (table, row id, SQL and params) and traceback. OK is the only way out (no Escape, no native close, per the dialog design convention described under `dialog_base.py` below); the caller logs the error, this dialog only displays it.

#### debug_settings.py

`DebugSettingsDialog` (`_ColourPickerCtrl` helper) -- developer-facing debug toggles.

#### dialog_base.py

`BaseDialog(QDialog)` -- the shared base every dialog in this directory (and its `housing_editor/`/`transition_editor/` subpackages) derives from, using `CustomizeWindowHint` plus a custom draggable `Header` widget (`header.py`) instead of the native OS title bar. **Dialogs intentionally have no native close (X) button and no Escape-to-close behavior** -- the only way to dismiss one is via the `QDialogButtonBox` buttons at the bottom. This is a deliberate choice for a clean, uniform interface, not an oversight: never add native window decorations, an X button, or Escape-close to a `BaseDialog` subclass. Any close-time cleanup must hook `finished`/`accepted`/`rejected` (the signals the bottom buttons always emit), not a window-close event. `properties_dialog.py`'s modeless-properties-dialog cleanup (`tab_widget.set_obj(None)` on close, so live position callbacks don't stay bound) follows this pattern, as does `transition_editor/dialog.py`'s `_release_control()` (see that subpackage's own MAP.md).

#### dimensions_dialog.py

`DimensionsDialog` -- prompts for a catalog part's length/width/height when the catalog leaves one or more at 0.0 (a 0.0 dimension collapses that axis in the placeholder VBO, making the object invisible); meant to be called from every `start_add` classmethod right after the user picks a part, before any project row is created.

#### error.py

`ErrorDialog` -- generic error dialog (`ErrorDialog.show_error(parent, message, title=..., details=...)`).

#### export_dialog.py

`ExportDialog` -- runs `exporter.exporter` on a background `QThread` (`_ExportWorker`), with per-format file pickers (`_FilePickerRow`).

#### header.py

`Header(QtWidgets.QWidget)` -- the custom draggable title-bar replacement every `BaseDialog` uses in place of the native OS title bar.

#### part_orientation.py

`PartOrientationDialog` -- a self-contained 3D preview scene (own `Canvas3D` + own `bounds.Manager`, not a view into the mainframe's live editor3d) for previewing/orienting a catalog part before placement. `PartModel`/`PartModel3D` are a from-scratch `Base3D` facade pair built because this dialog previews every catalog part type generically -- contrast with `transition_editor/preview.py`, which subclasses a real object class because it only ever previews one type. Also has `AxisLabel`/`AxisLabel3D` and `MeshStatsOverlay`.

#### part_search.py

`SearchDialog` -- the part-search dialog, internally a full mini query-language engine: `SearchTerm`/`ColumnSearch`/`SearchParameters` (query model), `ParseProblem`/`ParseResult`/`ColumnInfo`/`TableSchema` (parsing/schema), `SearchTextEdit`/`_HistoryPopup` (the query text box + history popup), `_FilterPanelBase`/`FKFilterPanel`/`EnumFilterPanel`/`RangeFilterPanel` (filter-assist panels that write into the same query text), `_QueryWorker`/`QueryScope` (async query execution), `HelpDialog`. This is the from-scratch rewrite described in MEMORY.md's "Part-search dialog rewrite" entry -- that entry names the file `ui/dialogs/new_part_search.py`, but the rewrite was committed directly into `part_search.py` (replacing the original `SearchDialog` in place) rather than landing as a separately-named file, so read `part_search.py` wherever MEMORY.md says `new_part_search.py`. Rationale for the rewrite: "what's shown is always exactly what's in the visible search-box text" (chasing a real bug where a terminal silently vanished from the dialog's results on its second placement, traced to a hidden IN-clause side-channel called `initial_results`, now gone). Confirmed (via `dep_trace.py --imported-by`, 2026-10-18) to now be imported by 7 call sites: `add_handlers/editor_3d/seal.py`, `handlers/seal_handler.py`, `handlers/wire_handler.py`, `objects/objects_3d/menu_ops.py`, `objects/objects_3d/terminal.py`, `objects/objects_schematic/terminal.py`, `ui/dialogs/transition_editor/dialog.py`. When wiring a new caller onto it, follow the `Terminal.start_add` pattern: build a `SearchParameters` instead of a raw part-number list, then construct `SearchDialog(mainframe, page_class, table, title, initial_params=...)`.

#### project_dialog.py

`OpenProjectDialog` -- pick/open an existing project.

#### project_model_dialog.py

`ProjectModelDialog` -- pick/change the project's own 3D model file and color; reached from the 3D empty-space menu's Add/Edit Project Model entry. Limitation: `objects.project.set_project_model` only sets the project model's file and color -- there are no position/scale/angle columns on `projects`, so a project model placed this way always renders at the origin; placing it at the click point would need new schema columns (in both `harness_designer/database/create_database/` and the sibling `harness_designer_database` repo's builder) -- asked about, not yet done.

#### properties_dialog.py

`PropertiesDialog` -- opens a selected object's property control **modelessly** (`show()`, not `exec()`) with a fresh instance of the same control class the object-editor dock uses, so both can display different objects at once. Must call `tab_widget.set_obj(None)` on close, per the dialog design convention described under `dialog_base.py` below.

#### render_setings.py

`RenderSettingsDialog`, `LightingPanel`, `LightsPanel`, `LightItem` -- ray-trace render/lighting settings. The filename (`render_setings.py`, missing a "t") is a long-standing typo, kept as-is deliberately -- a known, intentionally-unfixed oddity rather than something to silently rename, since renaming would need updating every import.

#### transition_routing.py

`TransitionRoutingDialog` -- re-routes wires between a transition's output branches via drag-and-drop (`_WireList`, `_BranchGroup`).

## FOLDERS

#### housing_editor/

The housing cavity/accessory editor subsystem -- lets a user author/correct a catalog housing's cavity surfaces and accessories by picking faces directly on its real 3D model. See `housing_editor/MAP.md`.

#### transition_editor/

The transition catalog-part editor, with a live 3D preview rendered through the real transition-rendering pipeline. **Previously undocumented in the root `CODEBASE_MAP.md`** -- only `housing_editor/` was listed there; this is its first real documentation. See `transition_editor/MAP.md`.
