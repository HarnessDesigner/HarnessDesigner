## FILES

#### __init__.py

Re-exports `mainframe.MainFrame` only — the package's sole public entry point for the rest of the app.

#### dock_base.py

Defines `DockWidget(QtWidgets.QDockWidget)` (adds `Raise()`/`Show(flag)` convenience methods over the raw Qt widget) and `DockBase`, the shared base every editor dock wrapper (`Editor3D`, `EditorSchematic`, `EditorPegboard`, `EditorDB`, `EditorObj`, `EditorAssembly`, `EditorCircuit`, `ScriptEditor`, ...) subclasses. `DockBase.__init__` creates the `QDockWidget`, sets its object name/title/features, shows it, and registers it with `mainframe.addDockWidget`. Also exposes `IsShown()`, `Show(show)`, `Refresh()`, `Destroy()` as a uniform interface over whatever concrete panel widget (`self._ui_obj`) the subclass set before calling `super().__init__()`.

#### mainframe.py

`MainFrame(QtWidgets.QMainWindow)`, the app's single main window and the hub everything else plugs into. Is actually ~3500 lines, not the ~2000 CODEBASE_MAP.md estimates — the gap is almost entirely the deliberately-repeated `_on_*_3d`/`_on_*_2d`/`_on_*_pegboard` event-handler triples (one near-identical set of click/drag/key handlers per view), not unexpected growth elsewhere; the repetition itself is the explanation, not a doc error. `__init__` builds the splash-screen-driven startup sequence, constructs every dock (`editor_3d`, `editor_schematic`, `editor_pegboard`, `editor_db`, `editor_obj`, `editor_assembly`, `editor_ciruit`, plus `object_browser`) and every toolbar (`toolbar.GeneralToolbar`, `EditorToolbar`, `NoteToolbar`, `EditorObjectToolbar`, `Setting3DToolbar`, `PegBoardToolbar`) unconditionally up front — toolbars are a deliberate global convention, not per-editor-focus, so all of them exist regardless of which dock currently has focus; `system_menu/`'s menubar menus are wired up the same way (if a new editor-specific toolbar is ever added, follow this existing global-construction convention rather than gating it on focus). Signal fan-out connects each GL canvas's full `EVT_GL_*` signal set (object selected/unselected/activated, every mouse button's click/dclick/drag, key up/down, mouse move, capture-lost) for each of the 3D, schematic and peg-board canvases. `add_object`/`remove_object`/`set_selected`/`set_clone_obj` are the central fan-out point: a single call here is forwarded to every open editor dock (3D, schematic, peg board) uniformly, so callers (handlers, project load) never need to know which views are showing a given object; `load_project()` and `_open_project()` drive the same fan-out in bulk when a project opens. `show_scraper_browser()` and `show_script_editor()` create the Web Browser (`web_viewer/`) and Script Editor (`editor_script/`) docks lazily, on first use (not at startup like the other docks), and `_link_scraper_docks()` joins them together afterward; both are reached only from the General toolbar (no menu entry yet). `closeEvent()` runs a staged shutdown (`_do`/`_run` helpers) with progress reporting; `unload()` tears down the current project; `_save_position`/`_save_size`/`moveEvent`/`resizeEvent` persist window geometry.

## FOLDERS

#### datasheet_viewer/

Single-file viewer dock (not covered in detail by this documentation pass).

#### dialogs/

Standalone dialogs (About, part search, project dialogs, the multi-file `housing_editor/` sub-package, etc.) — not covered in detail by this documentation pass.

#### editor_3d/

The 3D editor dock — the main perspective view of the harness, showing real 3D part meshes and driving the 3D object-placement/drag handlers. See `editor_3d/MAP.md`.

#### editor_assembly/

The assembly editor dock. See `editor_assembly/MAP.md`.

#### editor_ciruit/

The circuit table editor dock (directory name has a genuine pre-existing typo, "ciruit", kept as-is per repo convention — not a doc error, don't "fix" it). See `editor_ciruit/MAP.md`.

#### editor_db/

The parts-database (global_db catalog) editor dock. See `editor_db/MAP.md`.

#### editor_obj/

The object property editor dock. See `editor_obj/MAP.md`.

#### editor_pegboard/

The Peg Board Editor dock. See `editor_pegboard/MAP.md`.

#### editor_schematic/

The schematic editor dock. This is the real, current directory for what CODEBASE_MAP.md still calls `editor_2d/editor2d.py` (`Editor2D`/`Editor2DPanel`) — same content, renamed; treat any CODEBASE_MAP.md reference to `editor_2d`/`editor2d.py` as describing this directory. See `editor_schematic/MAP.md`.

#### editor_script/

The scraper tool's Script Editor dock (Claude assistant, console, code editor). See `editor_script/MAP.md`.

#### log_viewer/

Single-file viewer dock (not covered in detail by this documentation pass).

#### object_browser/

`objectbrowser.py`, the scene-tree dock (not covered in detail by this documentation pass).

#### pegboard_table/

The peg-board wire table widget (`WireTable`, `column_defs.py`, `mdi_host.py`) — a sibling of `editor_pegboard/`, not part of it (not covered in detail by this documentation pass).

#### prop_ctrls/

Property-grid field controls, one file per value type: float, int, string, color, position2d/3d, angle3d, scale3d, model3d, image, path, enum, choice, combobox, array_* (not covered in detail by this documentation pass).

#### scraper_inspector/

The scraper's XHR/source inspector docks (not covered in detail by this documentation pass).

#### system_menu/

The menubar's file/edit/view/database/settings/window/help menus, wired up unconditionally alongside the toolbars in `mainframe.py` (not covered in detail by this documentation pass).

#### toolbar/

`toolbar.py`'s toolbar classes plus `float_spin_button.py`, `snap_angle_button.py`, `pegboard_snap_button.py` (not covered in detail by this documentation pass).

#### web_viewer/

The scraper's QtWebEngine-based Web Browser dock (not covered in detail by this documentation pass).

#### widgets/

Reusable low-level controls (`*_ctrl` wrappers, autocomplete combos, `code_editor_ctrl.py`'s `CodeEditorCtrl`, `empty_space_menus.py`, `wrap_label.py`'s `WrapLabel`) — not covered in detail by this documentation pass.
