# harness_designer/ui/editor_db/base.py

## `EditorList.get_rows` / `get_obj_id` - paged SELECT re-ranks the whole filtered table per fetch
The paged query is `SELECT * FROM (SELECT ROW_NUMBER() OVER (ORDER BY ...) ... WHERE ...) WHERE RowNum BETWEEN s AND e`. SQLite must sort or rank every matching row to hand back one window of `buffer_size` rows, so each fetch costs O(N log N) in the table size, not O(window). `get_row` triggers a fetch whenever a row is outside the cache, and the buffer is sized from scroll velocity, so fast scrolling issues many fetches. `get_obj_id` (called on activation) runs the same full ranking for a single row. Keyset paging (`WHERE id > last_id ORDER BY ... LIMIT n`) or an index on the active sort column would bound each fetch to the window.

## `EditorList.record_count` - COUNT(*) with LIKE predicates on every filter/sort change
`record_count` is a property that runs `COUNT(*)` through `_combined_where`. It is called from `__init__`, `set_filter`, `_apply_header_search` and the sort path. Header-search predicates are `LIKE '%text%'` (leading wildcard, no index use), so each change scans the table. This runs once per user change, not per keystroke, so it is acceptable for current table sizes.

## `EditorList.get_row` / `_get_cell_text` - cache hits are cheap, misses re-enter the DB
`data()` calls `_get_cell_text` once per visible cell, and each call goes through `get_row`. The dict lookup is O(1), so a warm cache costs nothing extra. A miss fetches a whole buffer, which is the expensive case above.

## `EditorList._get_icon` / `_update_progress` / `_load_icon` - icon cache only grows
`bitmap_indexes` and `downloading_images` are cleared only on filter and sort changes (`bitmap_indexes.clear()`). Icons are kept for every row ever scrolled into view, each a 64x64 `QIcon`, so memory grows with the total number of distinct rows visited in a session. Each icon costs one `QIcon(pixmap)` conversion in `_load_icon`. A bounded LRU keyed by `db_id` would cap it.

## `EditorList.prune_cache` - rebuilds the whole `rows` dict on every idle tick that needs it
`_on_idle` runs every 200 ms and calls `prune_cache` only when `needs_pruning` is set (after a fetch). `prune_cache` rebuilds the full dict with a comprehension, O(cache size). The cache is bounded by `buffer_size * 4`, so this is cheap in practice.

## `EditorList.mousePressEvent` / `mouseDoubleClickEvent` - timer restart per press
Each press on the selected row stops and restarts `_deselect_timer`, and `_record_double_click_gap` sorts at most five samples. Both are constant-size work per click and not a concern.

## `_EditorModel.headerData` - rebuilt on every header repaint
`headerData` scans `sort_columns` for every section on each repaint, and `_rebuild_sort_indicators` forces a full header repaint on each sort/filter change. Both are O(columns * sort depth), which is tiny.

## `ScrollTracker.get_buffer_size` - no cost concern
Arithmetic only, called once per uncached `get_row`.
