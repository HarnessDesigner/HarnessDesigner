# harness_designer/pegboard_print/layout.py

Pure maths, no Qt/GL (checkable on its own): PageGeometry, Tile, PrintLayout, build_layout(bounds, scale, geometry), fit_scale(bounds, cols, rows, geometry). World X runs right, world Z runs DOWN the page (the pegboard canvas's convention).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `build_layout` (lines 141-187, depth 2).

Status: static read of the code only. Nothing here has been profiled.
