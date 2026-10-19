## FILES

#### __init__.py

`from . import grid2d as _grid2d` — re-exports `compile_program`.

#### fragment.frag

Computes every dot procedurally from world position, at a single power-of-2 spacing tier, with no
CPU-side per-dot precompute at all — matching `canvas_pegboard/floor.py`/`canvas_schematic/
floor.py`'s current `Floor` classes, which deliberately dropped an earlier major/minor "nice
value" (1/5/10/50…) two-tier scheme after visual testing showed it looked inconsistent (see those
files' own MAP.md entries). Uses the same single-quad-per-frame technique `gl/shaders/floor/
fragment.frag` uses for the 3D floor grid.

#### grid2d.py

`compile_program()` — compiles+links `vertex.vert` + `fragment.frag` (no geometry stage) into the
2D procedural dot-grid program, wrapped by `program.GridProgram` and shared by both
`canvas_schematic/floor.py` and `canvas_pegboard/floor.py`.

#### vertex.vert

One small quad, resized every frame to exactly cover the current viewport.
