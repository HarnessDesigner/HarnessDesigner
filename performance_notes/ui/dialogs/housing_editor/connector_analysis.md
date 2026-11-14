# harness_designer/ui/dialogs/housing_editor/connector_analysis.py

Fit/clearance analysis logic, referenced by tree_panels.py's hole-selection flow (see that file's own entry).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `split_into_components` (lines 60-112, depth 3), `compute_surfaces` (lines 20-56, depth 2), `extract_boundary_loops` (lines 123-181, depth 2), `align_holes` (lines 285-323, depth 2), `_cylinder_mesh` (lines 335-361, depth 2), `_box_mesh` (lines 365-388, depth 2).

Status: static read of the code only. Nothing here has been profiled.
