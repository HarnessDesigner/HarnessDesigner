# harness_designer/database/project_db/pjt_point3d.py

## Line 482-674 (`is_referenced`) and 677-696 (`delete`) — about a dozen `OR` selects, each a full scan of a table, on every point delete
`delete()` calls `is_referenced()` first and does nothing if the point is still used. `is_referenced` checks, in a fixed order, notes, boots, covers, CPA locks, TPA locks, seals, housings, cavities, terminals, wire paths, bundle paths, wires, bundles, cable paths, cables and cable conductors, returning at the first table that references the point. Most of those selects use `OR=True` over two to seven point columns (14 call sites, lines 554-669), and an `OR` select cannot use the index (`TableData._candidates` returns every row), so each is O(rows of that table) at about 0.4 us per row. A point that is NOT referenced, which is exactly the point that will be deleted, goes through every table, so the delete path always pays the full cost: for a project with a few hundred rows per table that is 1-2 ms per delete, growing with the project. If a code path deletes points often (placeholder points while placing wires), this adds up. Fix: let `TableData` answer `OR` as a union of per-column index hits (see `table_data.md`). The cost is one index per column asked, about 100-150 bytes per row per column, a few hundred KB at most for these tables. Ordering the checks so the largest tables come last does not help the unreferenced case.

## Line 290-335 (`_update_point`), 381-426 (`point`)
`_update_point` writes x, y, z in one `update` call (one statement); `point` builds the shared `Point` once (cached by `db_id`). Fine.

## Line 52-99 (`PJTPoints3DTable.__iter__`, `__getitem__`, `insert`)
Cache-backed; `__iter__` creates one wrapper per row. Not on a hot path.
