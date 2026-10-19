## FILES

#### __init__.py

Re-exports the module as `_toolbar` only; no public symbols of its own.

#### float_spin_button.py

`FloatSpinButton(QtWidgets.QToolButton)` -- a toolbar button pairing a labeled float spin box with an icon; `__init__(self, parent, label, icon, min_val, max_val, step=0.1, decimals=2, suffix='')`.

#### pegboard_drag_mode_button.py

`PegboardDragModeButton(QtWidgets.QToolButton)` -- toggles the Peg Board Editor's drag-repositioning interaction mode; registered on `toolbar.PegBoardToolbar` alongside `pegboard_snap_button.py`'s button.

#### pegboard_snap_button.py

`PegboardSnapButton(QtWidgets.QToolButton)` -- Peg Board grid-snap toggle, same left/right-click shape as `snap_angle_button.py`'s `SnapAngleButton`: left click enables/disables with a checkbox icon overlay (icon `icons.mip_mapping`, the only checkerboard/grid-like icon asset available -- no dedicated grid icon exists), right click opens a popup with an "Auto" `QCheckBox` + `QDoubleSpinBox` (no enumerable fixed-value set like snap angle has, so no `AutoCompleteComboBox` here). Writes `Config.editor_pegboard.grid.snap` / `.manual_snap_spacing` (`None` = Auto, float = fixed override); registered via `toolbar.PegBoardToolbar` since none of the other toolbars share this button's theme (`EditorObjectToolbar` is 3D transforms, `Setting3DToolbar` is 3D viewport display toggles, `GeneralToolbar` is app-level dialogs). `gl/canvas_pegboard/canvas.py`'s `Canvas.snap_to_grid()` checks `config.grid.manual_snap_spacing` first, falling back to `self._grid.grid_spacing` (the live LOD tier) when it's `None`.

#### snap_angle_button.py

`SnapAngleButton(QtWidgets.QToolButton)` -- rotation-snap toggle: left click enables/disables with a checkbox icon overlay, right click opens an `AutoCompleteComboBox` (from `ui/widgets/autocomplete_combobox.py`) popup of the 71 valid snap angles. Writes `Config.editor3d.rotation_rings`. The same left/right-click shape was reused by `pegboard_snap_button.py`'s `PegboardSnapButton`, minus the `AutoCompleteComboBox` (grid spacing has no fixed enumerable value set).

#### toolbar.py

Defines every toolbar class, all constructed unconditionally in `mainframe.py` regardless of which editor dock has focus -- an existing convention: toolbars are global, not per-editor-focus. `EditorToolbar` -- editor-mode switch (3D/schematic/pegboard, etc.). `NoteToolbar` -- note-placement tool. `EditorObjectToolbar` -- 3D transform tools. `Setting3DToolbar` -- 3D viewport display toggles. `PegBoardToolbar` -- hosts `pegboard_snap_button.PegboardSnapButton` and `pegboard_drag_mode_button.PegboardDragModeButton`; exists as its own toolbar class because neither button's grid-snap/drag-mode theme fits any of the other toolbars. `GeneralToolbar` -- app-level dialogs and tools: the Internet button opens the scraper Web Browser dock (`MainFrame.show_scraper_browser()`), the Script Editor button (icon `note_pen`) opens the script editor dock (`show_script_editor()`); both docks are created lazily on first click rather than at startup.
