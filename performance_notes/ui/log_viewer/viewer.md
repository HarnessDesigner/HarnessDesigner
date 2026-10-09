# harness_designer/ui/log_viewer/viewer.py

## `_LogModel.append_data` - copies the whole log on every appended batch
`append_data` does `pd.concat([self._data, df], ignore_index=True)`. That allocates a new frame and copies every existing row each time new lines arrive. The live tail appends in small batches, so over a long session the total copy work grows with the square of the log length.

Candidate fix: keep the appended frames in a list and concatenate lazily, or concatenate only when the model is read (a `_materialise()` step run from `rowCount` or `data` when a dirty flag is set). The per-row read path (`data`) then sees one consolidated frame, and the append path becomes O(batch size). Measure a long-running log before adopting it.

## `_get_dates_in_log` / `_get_hours_in_date` - full file read per tree expansion
Each date or hour node that the tree builds calls `_read_log_file`, which reads and parses the whole log through `read_log`. Expanding a log file reads it once for the dates. Expanding a date reads it again for the hours. The same file can be read several times in a single session, and the archive variants read whole archives.

Candidate fix: read each log once per load and derive the date and hour lists from that one frame, or cache the parsed frame keyed on the file path and its modification time. Either change keeps the tree behaviour the same.

## `_LogMessageDelegate.paint` - row height changed during paint
For the message column, `paint` calls `_ensure_row_height_for_index`, which may call `setRowHeight` while Qt is painting. The `_height_update_guard` flag stops the recursion, and the height is cached per row, so the cost is paid once per row. The change does force a relayout during paint, which is worth knowing about if the view ever shows a flicker on first scroll. The cache has no size limit, but it is bounded by the number of rows in the log.

## `_LogModel.data` - one pandas scalar read per visible cell
`data` uses `iat`, which is the cheapest scalar accessor pandas offers, and it runs once per visible cell per repaint. This is already the intended fast path. No change.
