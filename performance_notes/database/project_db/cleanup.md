# harness_designer/database/project_db/cleanup.py

## Line 141-219 (`ProjectCleanup._process_batch`, `_delete_batch`)
Finds unreferenced points with `find_unreferenced_point3d_ids` / `find_unreferenced_point2d_ids` (SQL CTE queries against the database, one per table in the chain, see `pjt_bases.md`) in chunks (`process_chunk`, line 114), then deletes the orphans in batches. The chunking is what keeps it off the UI's critical path: it is meant to run in small slices. Cost is O(candidates x tables) per chunk in the database. Because the queries read the database and not the in-memory store, run it only when no gesture is open (a gesture's pending changes are invisible to it).
