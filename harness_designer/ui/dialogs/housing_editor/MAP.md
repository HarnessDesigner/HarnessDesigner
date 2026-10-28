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

#### cavity_paint_dialog.py

`CavityPaintDialog(QtWidgets.QDialog)` + its canvas widget `_PaintCanvas` -- a standalone 2-D "paint program" style editor for manually laying out circle/rectangle cavities on a flattened (local x/y millimetre) projection of a selected terminal plane, opened from `tree_panels.py`'s "Draw Cavities on Surface..." (toolbar button or right-click menu on a terminal plane_group). Pure Qt/dataclass math, no mesh/numpy dependency at all -- `housing_editor.py`'s `_on_draw_cavities_requested` does all the 3-D<->2-D conversion (projecting the plane's boundary loops into local (u, v) coordinates for the background outline, and converting the dialog's accepted shapes back into world-space `manual_cavities` params) before/after opening it. Shapes are drawn/dragged/selected on the canvas and can also be nudged by exact X/Y/size fields in a side panel; overlapping shapes (bounding-box test) are automatically grouped and committed as a single bounding-box rect cavity by `result_shapes()` -- the canvas still shows/edits each drawn shape individually, the merge only happens when the dialog is accepted. This replaced the old in-3D-viewport click-drag draw flow (which used to live directly in `housing_editor.py`'s `_SurfaceSelectFilter`) because that flow had no per-shape list, so the only way to undo one bad draw was "Remove All" on the whole terminal side.

#### cavity_panel.py

`CavityGeneral`, `CavityTab`, `CavityPanel(EditableTabCtrl)` -- the per-cavity property tabs.

#### config.py

`_Config` (also exported as `Config`, the name `housing_editor.py` imports) -- this dialog's own self-contained canvas/scene configuration, mirroring the pattern `ui/dialogs/part_orientation.py` and `ui/dialogs/transition_editor/dialog.py` each use for their own standalone preview scenes. Its `editor_3d` is a `ConfigDB` class (that is what the canvas's `config` is checked against), and the outer name keeps its leading underscore on purpose: `ConfigDB.__persisted__` then never stores it. Renaming it to `Config` would make its `editor_3d` share the real editor's `editor_3d` table and overwrite the user's settings at exit.

#### connector_analysis.py

Fit/clearance analysis logic, referenced by `tree_panels.py`'s hole-selection flow (see that file's own entry).

#### housing_editor.py

`HousingEditorDialog` -- dialog orchestration, 3D surface picking/overlay (`SurfaceOverlay`, `_SurfaceSelectFilter`), the toolbar, and the wire/terminal/cavity tree row + edit form <-> Cavities/Accessories notebook `QStackedWidget` swap. That swap is triggered by "Accept Cavities", which also one-time-gates the dialog's own OK button -- OK is unusable until the user has accepted at least one batch of detected cavities. Don't bypass this gate when touching the Cavities/Accessories swap logic. `_SurfaceSelectFilter` now only does 3-D surface pick/toggle clicks -- manually drawing a cavity shape no longer happens in the 3-D viewport at all; `_on_draw_cavities_requested` instead projects the selected terminal plane's boundary into local 2-D and opens `cavity_paint_dialog.CavityPaintDialog` (see that file's own entry), then converts the result back into `self.manual_cavities` world-space params. `_update_analyze_enabled` must stay true to "Analyze is possible whenever there's SOMETHING to analyze" -- it checks `manual_cavities`/`hole_cavities` too, not just `term_plane_groups`/`terminal_surf_idxs`, specifically so removing the terminal plane a cavity was drawn on doesn't strand already-drawn manual cavities with no way to run Analyze.

#### housing_obj.py

`Housing(ObjectBase)` facade + `Housing3D`/`HousingPegboard`/`HousingSchematic` view-object triplet -- the dialog's own placed-housing wrapper, distinct from the real app's `objects.housing.Housing`. This directory's `Housing`/`Cavity`/`HousingAccessory` facades are look-alikes of the real app's `objects.housing.Housing`/`objects.cavity.Cavity` but are **not** the same classes -- they exist purely to drive this dialog's self-contained preview scene, following the same "parallel facade, not a subclass" shape as `ui/dialogs/part_orientation.py`'s `PartModel`/`PartModel3D` (contrast with `transition_editor/preview.py`, which subclasses the real object class instead -- see that directory's MAP.md for why the two dialogs made opposite choices here).

#### housing_panel.py

`HousingPanel(QTabWidget)` -- the housing-level property tab.

#### tree_panels.py

The three always-visible bottom-panel tree controls -- `_TreeControlBase` (shared caption/toolbar/tree/info-label shell, multi-select, Delete-key + auto-reselect-next-after-remove), `PlaneTreePanel` (wire-side and terminal-side surfaces, with Group-by-Plane/Group-by-Size views), `CavityTreePanel` (flat list of pending `AnalysisItem`s awaiting Accept Cavities). The terminal tree's right-click menu also has "Select Holes Instead of Surface" for housings whose cavities are holes cut through a face -- it swaps the plane for its holes (`connector_analysis.surface_holes`), analysed/committed as manual (synthetic-marker) cavities so they stay selectable in the 3D editor. These manual cavities are not surface-detected ones -- code elsewhere that assumes every cavity in this dialog came from automatic surface analysis will miss them.

`PlaneTreePanel`'s terminal instance also shows a "Manually Drawn Cavities" section (built by `_build_manual_cavity_tree`, from the `manual_cavities` list `load()` is now passed) below its plane groups, one leaf row per entry from `cavity_paint_dialog.CavityPaintDialog` -- each individually selectable/removable (Delete key, Remove button, or right-click), not just via the whole-side "Remove All" (`clearTerminalsRequested`). `_flatten_item`/`_perform_removal` encode a manual-cavity row's index as a *negative* int (`-(payload + 1)`) so it can travel through the same `list[int]` `removeRequested` plumbing as real (always >= 0) surface indices without colliding with one; `_perform_removal` splits the mixed list back into `removeRequested` (surfaces) and the new `removeManualRequested` (manual cavity indices) emits. "Add Circle/Rectangle Cavity" on a plane_group's right-click menu (and the old toolbar buttons of the same name) are gone -- replaced by a single "Draw Cavities on Surface..." action/button (`drawCavitiesRequested(group_idx)`) that opens the paint dialog; see `housing_editor.py`'s `_on_draw_cavities_requested` and `cavity_paint_dialog.py`'s own entry for why.
