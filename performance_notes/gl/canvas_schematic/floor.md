# harness_designer/gl/canvas_schematic/floor.py

## Whole file — identical to the pegboard floor
This module is a copy of `canvas_pegboard/floor.py`, line for line (the same `_build_quad`, `_initialize_grid`, `set`, `_current_spacing` and `render`). The same performance points apply; see `canvas_pegboard/floor.md`.

**Duplication:** two copies of one floor implementation will drift apart. A shared base for the 2D floors (or moving the common code into `canvas_base/floor_base.py`) would remove the duplication. Flagged; not changed in this pass.
