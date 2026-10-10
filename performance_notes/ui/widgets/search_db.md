# harness_designer/ui/widgets/search_db.py

## `_ResultCtrl.SetValues` / `_load_remaining` - loads every result row on the UI thread
`SetValues` appends the first row, then `_load_remaining(count)` fetches every remaining row from the open cursor and calls `_append_row` for each one. `_append_row` creates a `QTreeWidgetItem` and sets its `UserRole` data. The loop is synchronous, so a search with thousands of matches blocks the UI for the time it takes to fetch and build all the items. The inline comment says this is for correctness, since Qt's tree is not truly virtual. Pulling rows in chunks as the user scrolls (for example, on the vertical scrollbar's `valueChanged`), or using a model-backed view, would bound the work to what is on screen.

## `_append_row` - builds the display strings for every column of every row
`str(col)` is called for each column of each row when the row is appended, including columns the user never sees. The cost is linear in result size times column count, and it is paid during the synchronous load above.

## `SearchPanelField.__init__` - one DISTINCT query per search field at construction
`parent.db_table.get_unique(*params)` runs one query per field each time the search panel is built. The panel is built once per editor, so this is a fixed, small cost.

## `SearchPanel.search` - one WITH-query per search, executed on the UI thread
`TableBase.search` builds a `WITH results AS (...)` query, executes it, and fetches the count row. The count and the first page come from one statement, so this is not a double query. The execution itself is still on the UI thread, which is the same concern as the eager load above.

## `_ResultCtrl.GetValue` / `SearchPanel.GetValue` - trivial
Return a stored value or a child's stored value.
