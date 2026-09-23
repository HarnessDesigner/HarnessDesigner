# harness_designer/objects/project.py

## Line 49-114 (`_reconcile_wire_sibling_graph`) — O(wires x (terminals + splices + loops)) scan at every project load
For every wire (line 65 `for wire in project.wires`), this scans *every*
terminal (line 73), *every* splice (line 80), and *every* wire service loop
(line 101) in the project, comparing point ids to find the sibling that
attaches at each end. For a harness with, say, 2000 wires and 2000
terminals this is 4,000,000 point-id comparisons, all on the project-load
path (`Project.__init__` at line 416) that already shows up in the
`Project Load Time` log line at 440-443. Since `start_position3d_id`/
`stop_position3d_id`/`attach_position3d_id_raw` are already point ids
(bytes), building one dict up front -- `{point_id: terminal}`,
`{point_id: (splice, role)}`, `{point_id: (loop, role)}` -- and doing three
dict lookups per wire instead of three full-collection scans would turn
this into O(wires + terminals + splices + loops), a large win on big
projects. The function's own docstring (46-64) explains *why* this rebuild
has to happen every load (nothing here is a persisted DB column), but not
why it has to be an O(n x m) scan rather than an indexed lookup.

## Line 147-174 (`_reconcile_bundle_sibling_graph`) — same O(bundles x transitions x 6) pattern, same fix
Mirrors the wire version above at smaller scale (bundles/transitions/
branches are typically far fewer than wires/terminals in a harness, and the
branch loop at 162 is fixed to 6 iterations), so the absolute cost is much
lower -- but it's the identical fixable shape: build a
`{point_id: (transition, branch_id)}` dict once from every transition's 6
branches, then do one dict lookup per bundle end instead of a nested scan
over every transition's every branch for every bundle.

## Line 300-322 (`_load_objects`) — one `mainframe.set_progress` call per object, every load
Every single row loaded (every note, cavity, housing, terminal, wire, ...)
triggers a `mainframe.set_progress(cur_count, f'Loading {label}...')` call
(line 311-315) -- for a project with tens of thousands of rows across all
tables, that's tens of thousands of progress-bar/UI updates (and
`f'Loading {label}...'` string formatting) during a single load, all on
the same thread as the load itself. Batching this (e.g. only calling
`set_progress` every N objects, or once per `_load_objects` call plus a
final one) would cut UI update volume by orders of magnitude on large
projects without changing what the user sees (a progress bar doesn't need
per-row granularity).
