# harness_designer/ui/editor_circuit/editor_widget.py

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

## `WireDelegate.paint` and `sizeHint` - a few drawPixmap calls per cell, and the row height comes from `sizeHint`
`paint` draws each distinct wire's 100x25 `QPixmap` (already converted by `_on_loaded`, so no conversion on the paint path), stacked and centred. `sizeHint` sums the picture heights, so the vertical header is `ResizeToContents`: on a load, a sort or a filter the view asks every row's cells for a size hint (O(rows x columns), each hint cheap), where fixed rows asked nothing. That is fine for hundreds of circuits. Fixed heights set per row would be cheaper but would not follow a sort, because a row's height belongs to its position, not to its circuit.

## `ConnectorImageDelegate` - `_pixmaps_and_name` runs twice per cell, and the text branch builds a QFont on every paint
`paint` and `sizeHint` each call `_pixmaps_and_name`, which fetches the row through `index.data(UserRole + 1)`. Because connector images never load (README bug 2), `paint` always takes the text branch and creates a new `QtGui.QFont("monospace", 9)` for every cell it draws. The font could be created once on the delegate.

## `_BuildWorker.run` - full rebuild on each reload, all rows on one worker thread
`run` builds every circuit row in sequence, then runs `run_drt`, `generate_suggestions` and `worst_severity` for each row. The cost is O(circuits x (terminals + wires)) per reload, plus the DRT and suggestion passes. It emits progress per circuit, so the UI stays responsive, but nothing is incremental: changing one circuit rebuilds all rows.

## `EditorCircuitPanel.refresh` - clears the wire picture cache on every reload
`refresh()` clears `_WIRE_IMAGES` (the 100x25 and 200x50 `QImage`s kept per colour combination) before starting a rebuild. The generator keeps its own full-size image per colour combination, so the next rebuild only resizes again.

## `CircuitDetailPanel.show_row` - builds one card per distinct wire on each selection
`_show_wires` removes the previous cards (detached at once, deleted later) and builds a card (a frame, a picture label and a text label) per distinct wire: a handful of widgets for a typical circuit, one per distinct wire part for an unusual one. The 200x50 `QPixmap` is converted from the cached `QImage` the first time it is shown. The totals and DRT text are rebuilt from scratch on each selection; that is small work.

## `_guarded` - one try/except around every Qt-facing method
`@_guarded(fallback)` wraps the model, proxy, delegate and panel methods Qt calls. A call that does not raise costs one extra Python call and a `try`; that is small next to the work `data()` and `paint()` already do, but it is on the per-cell paint path. On an exception it logs once per (method, error) (a repeating paint failure would otherwise flood the log) and returns the fallback (a callable fallback is called, for a `QSize`/`QMimeData`). Added 2026-10-24 after this PySide6 build aborted the whole process on an exception escaping a Qt slot (see README, crash).

## `_wire_part_images` - once per distinct colour combination, on the worker thread
For each distinct wire part of each circuit the worker calls `images.build_wire` (PIL: recolour three layers and composite them; the generator caches the 400x100 result by colour names) and `_qimage` resizes it twice (100x25 and 200x50) and decodes the PNG into a `QImage`. `_WIRE_IMAGES` makes that once per colour combination per reload, however many parts and circuits share it. A harness has few wire colours, so this is a handful of builds per reload.

## `_wire_infos` - one pass over a circuit's wires and wire service loops
Linear in the circuit's wires and loops, with a dict keyed by part id; each member's length, resistance and weight are read once (they were already read for the totals), so the per-wire entries add the part reads (once per distinct part) and one dict lookup per member.
