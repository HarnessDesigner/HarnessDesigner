# harness_designer/ui/dialogs/bom_dialog.py

## `BomDialog.__init__` / `_reload_all` - four full report builds on open
`_reload_all` calls all four `build_*` functions in `objects/bom.py` (flat list, housing tree, wire cut sheet, bundle cut sheet) and loads all four views, even though the stacked widget shows only one of them. Each builder walks the project and reads part and catalog rows, so the dialog pays for three reports the user has not looked at.

Candidate fix: build a view when its page is first shown (for example from the `viewChanged` slot or `QStackedWidget.currentChanged`), and keep a flag per view so a later excess change only marks the stale views.

## `_on_wire_excess_changed` / `_on_bundle_excess_changed` - synchronous rebuilds on every step
The excess spin boxes emit `value_changed` on each step. Each emit runs synchronously:
- `_on_wire_excess_changed` rebuilds the flat list (which depends on both excess values) and the wire cut sheet.
- `_on_bundle_excess_changed` rebuilds the flat list and the bundle cut sheet.

Both handlers rebuild the flat list, which is called with both excess values, so each step rebuilds it even though only one excess changed. (Whether the flat list uses both values is not checked here; `build_flat_list` in `objects/bom.py` is the function to read.) When the user holds a spin-box arrow this runs many times a second, and each run hits the database through the builders. Two options to consider:
- Debounce the excess signals with a single-shot `QTimer`, the same way `transition_editor/dialog.py` debounces its preview timer.
- Rebuild only the view that is visible, and mark the others stale (see the section above).

The first option is the smaller change, and it keeps the displayed values in step with the controls.

## `_FlatListTree.load` and the other `load` methods - no change needed
Each tree clears and repopulates its items in one pass. `QTreeWidgetItem` construction is the dominant cost, and the row counts are the number of BOM lines, which is small. Nothing to change here.
