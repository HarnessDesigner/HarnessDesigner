# harness_designer/database/utils.py

## Line 56-160 (`enumerate_alpha`, `_enumerate_ids`, `get_cavity_ids`)
String parsing that expands cavity-name ranges ("A1-A12"). Called when a catalog row is created or imported, not per frame. Nested loops over the range length, which is small (tens of cavities).

## Line 164-232 (`purge_stale_files`) — walks the resource folders and queries the database per file
`_get_files_to_prune` runs queries in a loop over the files found and `_remove_files` logs per file. It is a maintenance sweep, not an interaction path. If it ever becomes slow on a large resource folder, collect the referenced ids with one query per table into a set and test membership in Python instead of one query per file.
