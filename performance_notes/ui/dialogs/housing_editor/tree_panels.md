# harness_designer/ui/dialogs/housing_editor/tree_panels.py

The three always-visible bottom-panel tree controls -- _TreeControlBase (shared caption/toolbar/tree/info-label shell, multi-select, Delete-key + auto-reselect-next-after-remove), PlaneTreePanel (wire-side and terminal-side surfaces, with Group-by-Plane/Group-by-Size views), CavityTreePanel (flat list of pending AnalysisItems awaiting Accept Cavities).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `_TreeControlBase._flattened_items` (lines 176-186, depth 2), `_TreeControlBase._selected_units` (lines 189-199, depth 2), `PlaneTreePanel._build_plane_tree` (lines 504-539, depth 2), `PlaneTreePanel._build_size_tree` (lines 542-570, depth 2).

Status: static read of the code only. Nothing here has been profiled.
