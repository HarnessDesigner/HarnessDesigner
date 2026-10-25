# harness_designer/ui/editor_circuit/design_rules.py

## `generate_suggestions` / `find_bundle_by_name` - bundle scan per bundle name on the row
`generate_suggestions` loops over `row.bundle_names` and calls `find_bundle_by_name` for each name. That lookup walks all of `db.pjt_bundles_table`, so the cost is O(bundle names on the row x bundles in the project). It also calls `bundle_wire_ods` per matched bundle. With the current stub (README bug 1), `row.bundle_names` is always empty, so this loop never runs and the cost is zero. Once the bundle lookup is fixed, a name-to-bundle dict built once per call would replace the repeated scan.

## `bundle_wire_ods` - stub (see README bug 1)
Returns `[]` without reading the bundle, so it has no cost. The loop it replaced walked every bundle wire.

FIXED 2026-10-24: `bundle_wire_ods` reads each wire's real outside diameter and `generate_suggestions` looks a bundle up by id (`CircuitRow.bundle_db_ids`), so the name scan and `find_bundle_by_name` are gone and an unnamed bundle works. Reading the wires of each bundle a row passes through is what costs now, once per bundle per row.
