# harness_designer/handlers/bundle_diameter.py

## Line 58-75 (`_wires_diameter`) — the `wires` property queries the database
`bundle_db_obj.wires` (line 70) runs a multi-table lookup each time it is read (see `PJTBundle.wires` in `database/project_db/pjt_bundle.py`). Each `wire.part` read is another lookup. The function reads the property once, so the cost is one lookup plus one per wire.

## Line 78-100 (`_attached_branches`) — two index lookups and a per-row fetch
Queries the transition-branches table by each end point, then fetches each matched row by id. Called from `wire_fits_bundle` and from `effective_diameter` (see below).

## Line 103-125 (`_wires_diameter_including`) — `wires` read again
Same property read as `_wires_diameter`, plus `part` per wire. Its docstring says it is a "would a new wire fit" check.

## Line 128-145 (`wire_fits_bundle`) — per drag candidate
This is the drag-and-drop eligibility check. The docstring points to a drop check on each candidate bundle. Each call runs `_attached_branches` (two queries) and `_wires_diameter_including` (one query plus one per wire). If it runs on every mouse move while a wire is dragged over a bundle, the query count per move is roughly `2 + 1 + wires`. The bundle's wire list could be read once per drag and reused.

## Line 159-200 (`effective_diameter`, `refresh_diameter`) — runs on each bundle change
`effective_diameter` reads each attached branch's `part.min_dia` and writes each branch's `diameter`. `refresh_diameter` is called when a bundle changes. Runs on edits, not per frame.
