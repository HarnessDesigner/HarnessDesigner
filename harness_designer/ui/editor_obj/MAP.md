## FILES

#### __init__.py

Package init for the object property editor dock; no content beyond the standard package marker.

#### editorobj.py

Defines `EditorObj(DockBase)` — the dock wrapper, and `EditorObjPanel(QtWidgets.QWidget)` — the panel. Shows/edits the properties of whatever object is currently selected in any of the 3D/schematic/peg-board views, via a generic property grid. `EditorObj.set_selected(obj)` forwards to the panel, which swaps in the property controls for the newly selected object (or clears them for `None`); `_on_visibility_changed` reacts to the dock being shown/hidden.

#### prop_grid.py

Defines `PropertyGrid(QtWidgets.QTabWidget)` — a minimal tab-per-category container with `Clear()`/`Append(item)`. The actual per-type field widgets it hosts (float/int/string/color/position/angle/scale/model3d/image/path/enum/choice/combobox controls) live in the sibling `ui/prop_ctrls/` package, not here — this directory only hosts the dock shell and the tab container, the real per-value-type editing widgets are not duplicated here.
