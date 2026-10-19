## FILES

#### __init__.py

`from . import floor as _floor` — re-exports `compile_program`.

#### floor.py

`compile_program()` — compiles+links `vertex.vert` + `fragment.frag` (no geometry stage) into the
3D procedural floor program, wrapped by `program.FloorProgram` and used only by
`gl/canvas_3d/floor.py`'s `Floor` class.

#### fragment.frag

Computes the checkerboard tiles plus major solid/minor dashed lines analytically, per-pixel,
using screen-space derivatives (`fwidth`) rather than relying on thin rasterized line geometry —
the technique that avoids the orientation-dependent moiré thin geometry quads produce at sub-pixel
widths. `gl/shaders/grid2d/` uses the same single-quad-per-frame technique for the 2D dot grid.

#### vertex.vert

Single large screen-covering quad, resized every frame to exactly cover the current viewport — no
per-vertex detail; all visual detail is computed in `fragment.frag`.
