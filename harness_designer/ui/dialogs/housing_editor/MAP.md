## FILES

#### __init__.py

Re-exports the module as `_housing_editor` only; no public symbols of its own.

#### accessory_obj.py

`HousingAccessory(ObjectBase)` + `HousingAccessory3D` -- this dialog's own accessory wrapper, paired with `housing_obj.py` the same way `cavity_obj.py` pairs with cavities.

#### accessory_panel.py

`AccessoryPanel(QTabWidget)` -- the per-accessory property tab.

#### analysis_panel.py

`AnalysisItem` (one detected/pending cavity) and `EditPanel` (the name/shape/radius/half-w/half-h/length editor for the cavity-preview tree's selected item).

#### cavity_obj.py

`Cavity(ObjectBase)` + `Cavity3D` -- this dialog's own cavity wrapper, paired with `housing_obj.py`.

#### cavity_panel.py

`CavityGeneral`, `CavityTab`, `CavityPanel(EditableTabCtrl)` -- the per-cavity property tabs.

#### config.py

`_Config` (also exported as `Config`, the name `housing_editor.py` imports) -- this dialog's own self-contained canvas/scene configuration, mirroring the pattern `ui/dialogs/part_orientation.py` and `ui/dialogs/transition_editor/dialog.py` each use for their own standalone preview scenes. Its `editor_3d` is a `ConfigDB` class (that is what the canvas's `config` is checked against), and the outer name keeps its leading underscore on purpose: `ConfigDB.__persisted__` then never stores it. Renaming it to `Config` would make its `editor_3d` share the real editor's `editor_3d` table and overwrite the user's settings at exit.

#### connector_analysis.py

Fit/clearance analysis logic, referenced by `tree_panels.py`'s hole-selection flow (see that file's own entry).

#### housing_editor.py

`HousingEditorDialog` -- dialog orchestration, 3D surface picking/overlay (`SurfaceOverlay`, `_SurfaceSelectFilter`), the toolbar, and the wire/terminal/cavity tree row + edit form <-> Cavities/Accessories notebook `QStackedWidget` swap. That swap is triggered by "Accept Cavities", which also one-time-gates the dialog's own OK button -- OK is unusable until the user has accepted at least one batch of detected cavities. Don't bypass this gate when touching the Cavities/Accessories swap logic.

#### housing_obj.py

`Housing(ObjectBase)` facade + `Housing3D`/`HousingPegboard`/`HousingSchematic` view-object triplet -- the dialog's own placed-housing wrapper, distinct from the real app's `objects.housing.Housing`. This directory's `Housing`/`Cavity`/`HousingAccessory` facades are look-alikes of the real app's `objects.housing.Housing`/`objects.cavity.Cavity` but are **not** the same classes -- they exist purely to drive this dialog's self-contained preview scene, following the same "parallel facade, not a subclass" shape as `ui/dialogs/part_orientation.py`'s `PartModel`/`PartModel3D` (contrast with `transition_editor/preview.py`, which subclasses the real object class instead -- see that directory's MAP.md for why the two dialogs made opposite choices here).

#### housing_panel.py

`HousingPanel(QTabWidget)` -- the housing-level property tab.

#### tree_panels.py

The three always-visible bottom-panel tree controls -- `_TreeControlBase` (shared caption/toolbar/tree/info-label shell, multi-select, Delete-key + auto-reselect-next-after-remove), `PlaneTreePanel` (wire-side and terminal-side surfaces, with Group-by-Plane/Group-by-Size views), `CavityTreePanel` (flat list of pending `AnalysisItem`s awaiting Accept Cavities). The terminal tree's right-click menu also has "Select Holes Instead of Surface" for housings whose cavities are holes cut through a face -- it swaps the plane for its holes (`connector_analysis.surface_holes`), analysed/committed as manual (synthetic-marker) cavities so they stay selectable in the 3D editor. These manual cavities are not surface-detected ones -- code elsewhere that assumes every cavity in this dialog came from automatic surface analysis will miss them.
