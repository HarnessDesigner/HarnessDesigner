# harness_designer/database/db_connectors/sqlite_connector/connector.py

One connector for the whole app (catalog and project share the connection), WAL mode, one cursor per thread.

## Line 47-88 (`_enable_wal`) — already the right setup
WAL with `synchronous=NORMAL`: a commit is about 0.015-0.03 ms instead of about 3 ms in the default journal mode (the docstring's measurement). Nothing to change. Possible extra PRAGMAs, only worth adding with a measurement on the real file: `cache_size` (SQLite's default page cache is small against a 395 MB catalog; a larger one such as 64 MB would keep repeated part-search scans in memory at the cost of that much resident memory), `temp_store=MEMORY`, and `mmap_size` (reads skip a copy; it costs address space rather than resident memory). The catalog is read-mostly, so `cache_size` is the one that could speed up repeated filtered searches; given the memory priorities in MEMORY.md, leave it unless search latency is a complaint, and fix the missing indexes first (they are a much larger win for no resident memory).

## Line 126-143 (`_cursor`) — a thread-local lookup on every statement
`getattr(local, 'connection', None)` plus a property call per `execute`/`fetch*`. A fraction of a microsecond; the per-thread cursor is needed (a shared cursor broke concurrent statements, see its docstring). Not a cost to remove.

## Line 505-542 (`execute`), 606-635 (`executemany`) — broad `except` keeps the app alive
The `except Exception` branches log, report an error dialog and return `None` (MEMORY.md: never let exceptions propagate). `_report_sql_error` dedupes by statement text so a hot loop does not queue dialogs. Normal-path cost is one try/except frame plus the sqlite call. Fine.

## Line 231-277 (`reset_query_profile`, `dump_query_profile`)
The query profile dict is only filled when something records into it; `execute` does no timing, so there is no per-statement cost today.

## Line 158-228 (`get_part_counts`, `get_part_counts_by_manufacturer`) — a `COUNT(*)` per table and per manufacturer, in loops
Used by first-run / about screens, not on an interaction path. On the big tables `COUNT(*)` is 1-2 ms (1.6 ms on `housings`), so a pass over all part tables is tens of milliseconds.

## Line 313-502 (`connect`) — creates 4 x 256 folders and rewrites the settings on every connect
After updating the four `settings` rows it makes each of the model/image/cad/datasheet folders and the 256 subfolders (`00`..`ff`) of each, with an `os.path.exists` per entry: about 1,000 `exists` calls on every launch (and the `mkdir`s the first time). A few milliseconds when they exist, once per launch. Not worth caching.
