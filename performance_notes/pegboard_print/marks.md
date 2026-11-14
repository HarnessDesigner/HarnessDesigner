# harness_designer/pegboard_print/marks.py

draw_page_marks(painter, layout, tile, px_per_mm) -- crosshair-with-ring marks half an overlap in from each edge of the printable area, so a page's right-hand mark is on the SAME peg board point as its right neighbour's left-hand mark (same for top/bottom): glue up by putting crosshairs on top of each other.

Qt objects created inside a loop: `QColor` (line 38), `QColor` (line 39), `QPen` (line 40).
Nested loops (cost grows with the product of the sizes; check the sizes are small): `draw_page_marks` (lines 107-178, depth 2).

Status: static read of the code only. Nothing here has been profiled.
