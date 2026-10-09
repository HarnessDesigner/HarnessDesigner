# harness_designer/objects/objects_pegboard/base_pegboard.py

## Line 214-245 (`touching_budgets`) — scans every wire and bundle, once per drag arm
Scans `project.wires` and `project.bundles` for any whose start or stop point matches this anchor's point. The docstring notes this runs once per drag arm, never per mouse move, which is the correct call frequency. There is no reverse index from point to wire, so the cost is linear in the number of wires and bundles per arm. That is fine at current project sizes; a point-to-wire index would make it constant if large harnesses start to feel slow at drag start.

## Line 35-58 (`notify_table_wires_changed`) — one attribute read after the typing change
Direct `table_position_peg_id_raw` access replaced the earlier `getattr`. No cost change. The table lookup and the `refresh_wires` call that follows are per wire-membership change, not per frame.

## Line 252-272 (`_table_row`) — an `is_*` check through `self.parent` on every call
`_table_row` now returns early through four `self.parent.is_*` property reads (housing, bundle, transition, splice) for every non-anchor pegboard object. Each `is_*` is a cheap facade property, so the check is negligible, and it replaces the `getattr` probe with the same result. Callers are `has_visible_table` and `show_table`, both UI-driven.

## Inherited render and update path
`BasePegboard` inherits `BaseVar.render` and the GL-context update hooks, so the costs in `objectsvar/base_var.md` apply to every pegboard object.
