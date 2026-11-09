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

`DebugSettingsDialog` (`_ColourPickerCtrl` helper) -- developer-facing debug toggles, developer-facing toggles for the faces / edges / normals / vertices passes and the other debug drawing options (the "Wire Benchmark" group and the GPU performance logging were removed 2026-11-08, together with the `gpu_single_wires` / `pooled_wires` / `batched_wires` check boxes).

#### dialog_base.py

`BaseDialog(QDialog)` -- the shared base every dialog in this directory (and its `housing_editor/`/`transition_editor/` subpackages) derives from, using `CustomizeWindowHint` plus a custom draggable `Header` widget (`header.py`) instead of the native OS title bar. **Dialogs intentionally have no native close (X) button and no Escape-to-close behavior** -- the only way to dismiss one is via the `QDialogButtonBox` buttons at the bottom. This is a deliberate choice for a clean, uniform interface, not an oversight: never add native window decorations, an X button, or Escape-close to a `BaseDialog` subclass. Any close-time cleanup must hook `finished`/`accepted`/`rejected` (the signals the bottom buttons always emit), not a window-close event. `properties_dialog.py`'s modeless-properties-dialog cleanup (`tab_widget.set_obj(None)` on close, so live position callbacks don't stay bound) follows this pattern, as does `transition_editor/dialog.py`'s `_release_control()` (see that subpackage's own MAP.md).

#### dimensions_dialog.py

`DimensionsDialog` -- prompts for a catalog part's length/width/height when the catalog leaves one or more at 0.0 (a 0.0 dimension collapses that axis in the placeholder VBO, making the object invisible); meant to be called from every `start_add` classmethod right after the user picks a part, before any project row is created.

#### error.py

`ErrorDialog` -- generic error dialog (`ErrorDialog.show_error(parent, message, title=..., details=...)`).

#### export_dialog.py

`ExportDialog` -- runs `exporter.exporter` on a background `QThread` (`_ExportWorker`), with per-format file pickers (`_FilePickerRow`).

#### fan_out_order.py

`FanOutOrderDialog` (NEW 2026-11-06) -- the order a split cable end's conductors fan out in: a list with Move Up / Move Down; `GetValue()` returns, for each new place, the index the conductor had in the list given. Opened from the 3D cable menu (`objects_3d/cable.py` `CableMenu.on_fan_out`), applied by `objects.cable.Cable.set_fan_order`.

#### header.py

`Header(QtWidgets.QWidget)` -- the custom draggable title-bar replacement every `BaseDialog` uses in place of the native OS title bar.

#### part_orientation.py

`PartOrientationDialog` -- a self-contained 3D preview scene (own `Canvas3D` + own `bounds.Manager`, not a view into the mainframe's live editor3d) for previewing/orienting a catalog part before placement. `PartModel`/`PartModel3D` are a from-scratch `Base3D` facade pair built because this dialog previews every catalog part type generically -- contrast with `transition_editor/preview.py`, which subclasses a real object class because it only ever previews one type. Also has `AxisLabel`/`AxisLabel3D` and `MeshStatsOverlay`.

#### part_search.py

`SearchDialog` -- the part-search dialog, internally a full mini query-language engine: `SearchTerm`/`ColumnSearch`/`SearchParameters` (query model), `ParseProblem`/`ParseResult`/`ColumnInfo`/`TableSchema` (parsing/schema), `SearchTextEdit`/`_HistoryPopup` (the query text box + history popup), `_FilterPanelBase`/`FKFilterPanel`/`EnumFilterPanel`/`RangeFilterPanel` (filter-assist panels that write into the same query text), `_QueryWorker`/`QueryScope` (async query execution), `HelpDialog`. This is the from-scratch rewrite described in this file's DESIGN NOTES's "Part-search dialog rewrite" entry -- that entry names the file `ui/dialogs/new_part_search.py`, but the rewrite was committed directly into `part_search.py` (replacing the original `SearchDialog` in place) rather than landing as a separately-named file, so read `part_search.py` wherever MEMORY.md says `new_part_search.py`. Rationale for the rewrite: "what's shown is always exactly what's in the visible search-box text" (chasing a real bug where a terminal silently vanished from the dialog's results on its second placement, traced to a hidden IN-clause side-channel called `initial_results`, now gone). Confirmed (via `dep_trace.py --imported-by`, 2026-10-18) to now be imported by 7 call sites: `add_handlers/editor_3d/seal.py`, `handlers/seal_handler.py`, `handlers/wire_handler.py`, `objects/objects_3d/menu_ops.py`, `objects/objects_3d/terminal.py`, `objects/objects_schematic/terminal.py`, `ui/dialogs/transition_editor/dialog.py`. When wiring a new caller onto it, follow the `Terminal.start_add` pattern: build a `SearchParameters` instead of a raw part-number list, then construct `SearchDialog(mainframe, page_class, table, title, initial_params=...)`.

#### pegboard_print_dialog.py

`PegboardPrintDialog(BaseDialog)` (NEW 2026-10-31) -- File > "Print Peg Board...". Modal; the main window keeps one instance (`MainFrame.show_pegboard_print`, which calls `refresh()` to re-read the peg board's content bounds, then `exec()`). Controls: paper (read from a hidden `QPrinter`; "Page Setup..." changes size/orientation), Scale % (100 = mm for mm, "1:1" button) or "Fit to N x M pages" (derives the scale), margin (floored at the printer's unprintable margin), overlap (min 10 mm: the alignment marks live in it), space around the drawing, render quality (150/300/600 dpi). `_LayoutPreview` draws the sheet grid over the content. "Print..." opens `QPrintDialog` then re-reads the layout (the dialog can change paper); "Save as PDF..." writes through a PDF `QPrinter`. Both go through `_run`, which shows a `QProgressDialog` and pumps events only BETWEEN pages. Settings live only as long as the dialog (nothing is stored in `Config`). All the real work is in `harness_designer/pegboard_print/`.

#### project_dialog.py

`OpenProjectDialog` -- pick/open an existing project.

#### project_model_dialog.py

`ProjectModelDialog` -- pick/change the project's own 3D model file and color; reached from the 3D empty-space menu's Add/Edit Project Model entry. Limitation: `objects.project.set_project_model` only sets the project model's file and color -- there are no position/scale/angle columns on `projects`, so a project model placed this way always renders at the origin; placing it at the click point would need new schema columns (in both `harness_designer/database/create_database/` and the sibling `harness_designer_database` repo's builder) -- asked about, not yet done.

#### properties_dialog.py

`PropertiesDialog` -- opens a selected object's property control **modelessly** (`show()`, not `exec()`) with a fresh instance of the same control class the object-editor dock uses, so both can display different objects at once. Must call `tab_widget.set_obj(None)` on close, per the dialog design convention described under `dialog_base.py` below.

#### ray_tracing_dialog.py

`RayTracingDialog(BaseDialog)` -- ray tracing settings (an embedded `RenderSettingsPanel`) next to the image as it renders (`_PreviewView`, which scales to fit and coalesces repaints). Render snapshots the 3D editor -- `mainframe.editor3d.camera` and `editor3d.editor.bounds_manager.aabb.visible_objects()`, i.e. what was drawn in the last frame (and frames only the editor window's visible crop of the canvas, not the whole virtual surface), so off-screen casters are missing from shadows/reflections -- then runs `ray_tracing.Renderer` on a worker thread; the worker's callbacks become Qt signals tagged with a run id so a cancelled render's late results are ignored. The full-size pixel buffer is what Save writes; the preview shows a copy thinned (every n-th row/column, filled in per chunk) to about `PREVIEW_MAX_WIDTH` pixels, because scaling a 30000-pixel-wide image on every repaint froze the UI. Not modal; Close cancels any render and hides it, and `MainFrame.show_ray_tracing()` keeps the one instance. `ray_tracing` is imported when a render starts, so a missing `pyopencl` or uncompiled `bvh.pyx` shows an error instead of stopping the app. Reached from View > Ray Tracing and the General toolbar's camera button.

#### render_setings.py

`RenderSettingsPanel` (the controls: resolution, background, effects, ambient occlusion, lighting; `apply()` writes `Config.ray_trace`; a "Samples per pixel" spin box (`samples`, 1 to 1024) under the resolution; the Lighting group has a "Light at Camera" checkbox, `lighting.camera_light`; the Background group a "Match Viewport (background and floor)" checkbox, `match_viewport`), `RenderSettingsDialog` (a thin `BaseDialog` around the panel), `LightingPanel` (a `QTabWidget`, one tab per light labelled `Light 1`..`Light n`, with Add Light / Remove Light buttons; removing renumbers the remaining tabs) and `LightItem` (a tab's page: `FloatCtrl` spin+slider for X, Y and Z stacked vertically, then intensity with the colour button beside it). The old `LightsPanel` (a scroll list with click-to-select) is gone. Fixed in the 2026-10 ray tracing pass: OK used to save the ambient intensity to `Config.lighting.intensity` (a key nothing reads) instead of `ambient_intensity`, and "Add Light" made a black light. The filename (`render_setings.py`, missing a "t") is a long-standing typo, kept as-is deliberately -- a known, intentionally-unfixed oddity rather than something to silently rename, since renaming would need updating every import.

#### transition_routing.py

`TransitionRoutingDialog` -- re-routes wires between a transition's output branches via drag-and-drop (`_WireList`, `_BranchGroup`).

## FOLDERS

#### housing_editor/

The housing cavity/accessory editor subsystem -- lets a user author/correct a catalog housing's cavity surfaces and accessories by picking faces directly on its real 3D model. See `housing_editor/MAP.md`.

#### transition_editor/

The transition catalog-part editor, with a live 3D preview rendered through the real transition-rendering pipeline. **Previously undocumented in the root `CODEBASE_MAP.md`** -- only `housing_editor/` was listed there; this is its first real documentation. See `transition_editor/MAP.md`.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Part-search dialog rewrite (`ui/dialogs/new_part_search.py`, built 2026-09-03; the user likes it and finds it much faster)
A from-scratch `SearchDialog`, started from a real bug (a terminal vanishing from the default view the second time it was placed in a housing, traced to a hidden IN-clause side channel, `initial_results`). Principle: what is shown is always exactly what is in the visible search text.
- **Query language** typed in the search box (`gender: "Male" blade size: >=2.8`): column-scoped `label: ` clauses, quoted phrases vs bare words, comma = OR, space = AND, and 7 whitelisted operators (`== != ~= >= <= > <`; a closed set, no arithmetic or assignment tokens ever get meaning; values are always bound `?` params; identifiers only come from a schema whitelist, never raw text: the user's explicit security requirement). Filter-assist panels and the "did you mean" typo check write into that same text. Explicit Search button (not per-keystroke), red-span validation, zero-result diagnostic, `Config.part_search.history` per-table history (like `recent_projects`).
- **Results panel** is the same `EditorList`-based page-class widget (e.g. `TerminalsPage`) as the old dialog (the user's call, after a purpose-built `QTableView` attempt); `do_search()` builds a WHERE clause and hands it to `set_filter()`, so there is no async gap and no "Searching..." popup.
- **Migration status:** wired into ONE caller, `Terminal.start_add` in `objects/objects_3d/terminal.py` and `objects_schematic/terminal.py` (`_search_params_for_cavity`/`_search_params_for_housing` build a `SearchParameters` seed instead of the old blade-size-guessing part-number list). `part_search.py` and ~11 other callers (wire, cover, seal, cpa_lock, tpa_lock, boot via housing.py, `menu_ops.get_part_id`) are still on the old dialog, deliberately, as a rollback and the remaining targets. To migrate: build `SearchParameters` (compat list -> `part_number` phrase terms; fallback -> known attributes such as `gender_id`/`blade_size`), then `new_part_search.SearchDialog(mainframe, page_class, table, title, initial_params=...)`. Verification without a GUI harness: a real-PySide6 import test, the pure query-language core against an in-memory SQLite DB, and a round trip through the live `Config` DB.

#### Dialog design convention
All dialogs derive from `ui/dialogs/dialog_base.py` (`BaseDialog`), using `CustomizeWindowHint` plus a custom draggable `Header` widget instead of the native title bar. Dialogs intentionally have **no native close (X) button** — dismissible only via the QDialogButtonBox buttons at the bottom.

**Why:** Deliberate design choice for a clean, uniform interface.

**How to apply:** Never suggest or add native window decorations, an X button, or Escape-close behavior to these dialogs. Any close-time cleanup must hook `finished`/`accepted`/`rejected`, which the bottom buttons always emit. See objects3d context menu architecture above for the modeless properties-dialog cleanup pattern.
