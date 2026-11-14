# harness_designer/objects/bom.py

Bill-of-materials support: BomLineItem, HousingTreeNode, WireCutRow, CableCutRow, BundleCutRow, format_length() (mm -> 70.0in (5'10")(1778mm), feet/inches rounded to the nearest inch), resolve_wire_icon() (takes a placed wire or a catalog Wire), cable_cut_length_mm() and build_cable_cut_sheet().

Nested loops (cost grows with the product of the sizes; check the sizes are small): `build_flat_list` (lines 161-246, depth 2), `build_housing_tree` (lines 250-343, depth 2).

Status: static read of the code only. Nothing here has been profiled.
