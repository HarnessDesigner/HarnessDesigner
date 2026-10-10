# harness_designer/add_handlers/editor_3d/terminal.py

## `snap_pool` property - rebuilt on every hover, and expensive per item
For every project cavity it calls `_male_terminal_position` or `_female_terminal_position` (geometry per cavity) and builds a new `SnapPool`. This is the most expensive `snap_pool` of the editor-3d handlers, because the position function runs for every cavity on every move.
Candidate: cache the pool once per session, since cavity geometry does not move while a terminal is being placed.

## `hover` - per move
`query_ray` (vectorised) plus `set_angle_from_cavity` on a change of snapped cavity. Fine.
