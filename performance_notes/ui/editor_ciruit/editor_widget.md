# harness_designer/ui/editor_ciruit/editor_widget.py

## `_find_obj` - linear scan of the whole project per lookup
`_find_obj` walks `project.circuits` or `project.wires` from the start for each call. `_on_row_selected` calls it once for the circuit and then once per wire in the row (`for wid in row.wire_db_ids`), so selecting one row costs O(wires_in_row x total_wires). Building a `{db_id: obj}` dict once per selection, or reading the dict the project already keeps, would make each lookup constant time.

## `_build_row` - one row per circuit, with per-terminal reads through the DB
Each circuit row reads its start terminal, its load terminals and their cavities and housings, and each wire and its part. That is a fixed number of attribute reads per object, so it is linear in the circuit's size. Each attribute read on a PJT object goes through the table accessor, so a row costs a few database reads per object. Nothing here is quadratic. `_build_row` previously also called `_bundles_for_circuit` for every row; that now returns `[]` immediately (see README bug 1), so the per-row scan over all bundles and their wires is gone for now.

## `_build_row` - housing pixmap loaded per connector, per row, before it returns None
`_load_housing_pixmap` now returns None without touching the housing. Once bug 2 is fixed, each connector image will be loaded and scaled per row, and the same housing will be reloaded for every row that uses it. A per-housing cache would avoid that.

## `_cell_text` - builds a 13-entry dict on every call
`CircuitTableModel.data()` calls `_cell_text(row, col)` for each visible cell on every paint. `_cell_text` builds a dict with all 13 column values, formatting each one (including `_gauge(row)` and the bundle join) before picking the one it needs. Each cell therefore pays for all 13 formats. Branching on `col` (or building the strings once per row in `_build_row`) would cut that to the single value used.

## `CircuitTableModel.data` - status and display roles per cell
`data()` returns the status icon or cell text for `DisplayRole`/`EditRole`. Qt asks for these once per visible cell, so the cost is about 13 formats per visible row per paint (see above). `ToolTipRole` (`_cell_tooltip`) is only requested on hover, so it is not on the paint path.

## `WireDelegate.paint` - steady state is a dict hit, misses cost one pixmap render
`paint` calls `_bitmaps.cached_wire_pixmap(...)`, which returns from `WIRE_PIXMAP_CACHE` after the first render. The key includes the cell width, so resizing a column creates a new entry for every distinct width. `EditorCircuitPanel.refresh()` clears the cache on each reload, which bounds it between reloads only (see `bitmaps.md`).

## `ConnectorImageDelegate` - `_pixmaps_and_name` runs twice per cell, and the text branch builds a QFont on every paint
`paint` and `sizeHint` each call `_pixmaps_and_name`, which fetches the row through `index.data(UserRole + 1)`. Because connector images never load (README bug 2), `paint` always takes the text branch and creates a new `QtGui.QFont("monospace", 9)` for every cell it draws. The font could be created once on the delegate.

## `_BuildWorker.run` - full rebuild on each reload, all rows on one worker thread
`run` builds every circuit row in sequence, then runs `run_drt`, `generate_suggestions` and `worst_severity` for each row. The cost is O(circuits x (terminals + wires)) per reload, plus the DRT and suggestion passes. It emits progress per circuit, so the UI stays responsive, but nothing is incremental: changing one circuit rebuilds all rows.

## `EditorCircuitPanel.refresh` - clears the pixmap cache on every reload
`refresh()` clears `WIRE_PIXMAP_CACHE` before starting a rebuild. That is correct for correctness, since cached pixmaps may hold stale colours, and it means the next paint re-renders every visible wire once.

## `CircuitDetailPanel.show_row` - one 320-px pixmap per selection
`show_row` fetches one wire pixmap at width 320 through the same cache, so selection changes after the first are cheap. The totals and DRT text are rebuilt from scratch on each selection. This is small work and not a concern.
