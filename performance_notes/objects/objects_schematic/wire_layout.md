# harness_designer/objects/objects_schematic/wire_layout.py

Not analysed line by line for performance. This file does not override `render`, `_update_position`, `_update_angle`, or `_update_scale` in a way that changes the draw path, so it inherits the `BaseSchematic`/`BaseVar` costs described in `base_schematic.md` and `objectsvar/base_var.md`. Any file-specific hot path would show up as an override of one of those hooks or as a per-mouse-move handler; re-check if it gains one.
