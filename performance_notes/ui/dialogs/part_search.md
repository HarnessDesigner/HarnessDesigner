# harness_designer/ui/dialogs/part_search.py

The part-search dialog (a query-text language, filter panels, async execution). Measured on a copy of the real 395 MB database (2026-11-13); see `database/README.md`.

## Line 903-1001 (`_QueryWorker`, `QueryScope`) — queries run on a worker thread with a generation counter
Searches run off the UI thread and `QueryScope` drops stale results through a generation counter, which is the right design for a type-as-you-search box: a slow query never blocks typing and an old result never overwrites a newer one. Keep it.

## Line 2191-2259 (`_populate_filters`) and the filter panels — one query per filter value list
The FK filter panels load their choice lists with queries on the lookup tables (manufacturers, families, series, ...). These tables are small and cached per wrapper, so it is cheap; it runs when the dialog opens.

## Line 2351-2393 (`_zero_result_message`) — up to one `COUNT(*)` per column on the UI thread
When a search returns nothing it runs `SELECT COUNT(*) ... WHERE <query without column c>` once per column in the query, synchronously, to suggest the single removal that would match the most. On the big catalog tables these are full scans (a `COUNT(*)` with a filter on an unindexed FK column took about 35 ms on `housings` with 81,093 rows, 1.6 ms with no filter), so a zero-result search with five columns freezes the dialog for about 150 ms. Two fixes: run the diagnostic through the existing `QueryScope` worker, or add indexes on the FK filter columns (`database/README.md`, finding 4), which brings each count to well under a millisecond.

## The query itself — `to_sql` (line 804-839) and the table scan
The generated `WHERE` clauses hit unindexed FK columns on tables of up to 81k (housings) and 148k (wires) rows, so each filtered search is a scan (35 ms) plus joins for the displayed columns (69 ms for three joins and one filter; 276 ms unfiltered). That is the dominant latency of this dialog, not the Python in this file. The Python parts (`parse`, `to_sql`, `build_schema`) are string and loop work over a handful of tokens and columns.

## Line 1099-1624 (`SearchTextEdit` colour handling)
`QColor` objects are created inside loops while underlining or colouring terms (lines 1455, 1460, 1515, 1517). A few per keystroke; cheap, but could be module constants.
