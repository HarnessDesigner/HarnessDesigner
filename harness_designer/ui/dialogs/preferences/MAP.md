## FILES

#### __init__.py

Re-exports `PreferencesDialog` only (the dialog module is deleted from the namespace afterward, like the other dialog packages).

#### dialog.py

`PreferencesDialog(BaseDialog)` -- Settings > Preferences (NEW 2026-11-14; OK / Cancel / Apply). A `QTreeWidget` of topics on the left, a `QStackedWidget` of panels on the right, in a splitter. The tree is the `_TREE` list of `_Node(title, key, tab, children)`; `_FACTORIES` maps a key to the callable that builds that panel. Panels are built lazily, in full, the first time a tree item that shows them is selected, and cached by key; several items share one panel (the three children of Mouse, and of Keyboard, all show the one notebook and bring their own tab forward through `TabbedPanel.set_tab`), so clicking a child without ever clicking its parent still has every tab built. A heading with no panel of its own (General, Editors) opens and selects its first child. `SetValues()` (OK and Apply) calls `apply()` on the panels that were opened only and, if any changed setting needs a restart, shows one message box listing them. Nothing is written to `Config` before that. The Settings menu calls it (`ui/system_menu/settings.py`). The 4 tree items with children are General, Mouse, Keyboard and Editors.

#### editor_pages.py

The 3D Editor, Pegboard Editor and Schematic Editor pages: groups of `fields` for the editor's colours, lighting, floor (and, in 3D only, grid and reflections), smooth shading per object kind, rotation gizmo, and the pegboard's rope pull and wire table / the schematic's layout and object sizes. Only settings that are actually stored are offered: in the Pegboard and Schematic editors `floor.reflections` (and their unused `input.*` actions) are plain placeholder classes in `config.py`, not `ConfigDB` classes, so writing them would not be saved and the pages leave them out. Not offered: `drag_handler.mode`, `manual_snap_spacing`, the grid's `secondary_line_pattern` (a stipple bit pattern) and `axis_overlay` size/position (internal state).

#### fields.py

The building blocks: `Field` and its subclasses (`BoolField`, `IntField`, `FloatField`, `VectorField`, `ColorField`, `ChoiceField`, `TextField`, `PathField`), made through the short builders `boolean`/`integer`/`real`/`vector`/`color`/`choice`/`text`/`folder`/`file`, plus `ColorButton` and `section(path)`. A field names its `Config` class by dotted path (`'editor_3d.floor.grid'`) and the setting by name, reads it through `Config`'s item access when its widget is built, and `apply()` writes it back **only if the widget's value differs from what the widget showed when it was built**: a spin box that shows 0.204 over a stored 0.2039, or a `QColor` round trip of a stored colour, must not rewrite settings the user never touched (`ColorButton` keeps the stored float list until a new colour is picked). Lists stay lists and tuples stay tuples. A `ChoiceField` whose stored value is not among its choices adds it as its own entry instead of replacing it. `restart=True` marks a setting that is only read at startup (its label gets a `*`).

#### general_pages.py

The pages that are not tied to one editor: `GraphicsPage` (VSync, MSAA samples -- only the levels `gl.info` `Max Samples` allows --, buffering, texture format, sRGB, and the three editors' virtual canvas size, which applies at once through each editor's `set_virtual_size`; the other Graphics settings are restart-only), `AppearancePage` (theme, applied at once with `themes.load_theme`; dock tab position and shape, applied with `MainFrame.setTabPosition`/`setTabShape`), `RayTracingPage` (hosts `render_setings.RenderSettingsPanel`, the same panel View > Ray Tracing uses), and plain field pages: Project, Logging, Models and Resources, Database (the SQLite path; the MySQL connection has its own dialog), Bundles, Placement Colors.

#### input_pages.py

The Mouse and Keyboard notebooks: `build_mouse_panel`/`build_keyboard_panel` give a `TabbedPanel` with a tab for each of `EDITORS` (3D, Pegboard, Schematic, in that order). `MouseActionGroup` edits one action's `mouse` bit mask (one check box per button, plus Reverse X / Reverse Y / Swap X-Y; bits it has no box for are kept) and its `sensitivity`/`speed`; `KeyActionGroup`/`KeyButton` edit its keys (click, press the new key; Escape cancels, Backspace/Delete unbinds). `KeyboardTab` also edits the key movement speed (`keyboard_settings`) and shows a red warning, without blocking, when one key is bound twice. Stored key form: `None`, the lower case `ord` of a printable key, or the `Qt.Key` value of any other key -- the two forms `gl/canvas_base/key_handler.py` `_process_key_event` matches, so `_to_config_key` writes exactly those. The 3D tab has all seven actions (rotate, pan/tilt, truck/pedestal, walk, dolly, zoom, reset); the Pegboard and Schematic tabs only the three they store (truck/pedestal, zoom, reset). The mouse and key handlers read `canvas.config.input` live, so a change applies without a restart.

#### page_base.py

`FieldGroup` (a group box of labelled rows, one per field), `PreferencesPage` (a scrollable column of items that each have `apply() -> list[str]`; call `finish()` last) and `TabbedPanel` (a notebook of pages with `set_tab`). Every `apply()` returns the labels of the changed settings that need a restart.

## FOLDERS

None.

## DESIGN NOTES

#### Where each Config section is shown

General: `mainframe` (theme, dock tabs), `project.model_dir`, `logging`, `resources` + `model_processing`, `database` (SQLite path, monitor duration, point batch size). Graphics: `graphics`, the three `*.virtual_canvas`. Mouse/Keyboard: the three `*.input.*` and `*.keyboard_settings`. Editors: the rest of `editor_3d`/`editor_pegboard`/`editor_schematic`. Placement Colors: `colors.add_object`. Bundles: `bundle`. Ray Tracing: `ray_trace` (through the existing panel). Left out on purpose: window geometry and dock layout (`mainframe.position/size/ui_perspective`), `project.last_project`, `part_search.history`, `colors.custom_colors`, `database.connector` and the MySQL settings (own dialog), `editor_pegboard.rope_pull.trace` (a debug switch), and everything under `debug` (Debug Settings dialog).

#### Adding a setting

Add a `_fields.<builder>('section.path', 'name', 'Label', ...)` line to the page. The first two arguments must be the real section path and setting name: a wrong one fails when the page is built (the whole panel does not appear), so open every page once after editing. If the setting is only read at startup pass `restart=True`.
