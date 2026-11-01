## FILES

#### __init__.py

Docstring only.

#### job.py

`print_layout(canvas, printer, layout, dpi, progress)` -- prints every tile of a `PrintLayout` on a `QPrinter` (a real printer or a PDF writer). Sets `setFullPage(True)` so the paper's corner is the origin and the margins are ours, draws in device pixels (`printer.resolution() / 25.4` px per paper mm; painter fonts are in points, so the painter is deliberately NOT scaled to mm), renders each tile with `renderer.render_tile`, then `marks.draw_page_marks`. The picture is whole pixels, so it overhangs its area by under one pixel and is clipped rather than squeezed -- the SCALE is exact (`mm_per_pixel = 25.4 / (dpi * scale)`). `progress(done, total)` returning False cancels (`printer.abort()`). Also `page_geometry(printer, margin, overlap)` (paper from `pageLayout().fullRect(mm)`, orientation applied) and `minimum_margin(printer)`.

#### layout.py

Pure maths, no Qt/GL (checkable on its own): `PageGeometry`, `Tile`, `PrintLayout`, `build_layout(bounds, scale, geometry)`, `fit_scale(bounds, cols, rows, geometry)`. World X runs right, world Z runs DOWN the page (the pegboard canvas's convention). Neighbouring tiles overlap by exactly `geometry.overlap` paper mm; the grid is centred on the content. `overlap * 2` must be under the printable size (marks sit half an overlap in from the edge).

#### marks.py

`draw_page_marks(painter, layout, tile, px_per_mm)` -- crosshair-with-ring marks half an overlap in from each edge of the printable area, so a page's right-hand mark is on the SAME peg board point as its right neighbour's left-hand mark (same for top/bottom): glue up by putting crosshairs on top of each other. Corners are marked when either adjoining edge has a neighbour, plus edge midpoints; "joins R2C3"-style labels name the neighbour; the bottom strip has "Page n/N RrCc scale x%" and a scale bar of a round world length (check it with a ruler: if short, the printer scaled the page). Labels sit on white boxes; marks have a white halo.

#### renderer.py

`render_tile(canvas, left, top, width_px, height_px, mm_per_pixel)` and `content_bounds(canvas)`. Renders by pointing the pegboard canvas's own camera at the tile (`camera.CenterOn` + `camera.distance = mm_per_pixel * 1000`, because that camera's scale is `distance / 1000` mm per pixel), setting `canvas.size`, and calling `canvas._on_draw()` into a multisampled `QOpenGLFramebufferObject`. Everything it touches is restored in a `finally` BEFORE returning and with no event processing in between (a queued repaint in the print state would draw garbage): camera, `canvas.size`, `_selected` (cleared so no selection overlay), the floating table/section selection ring, the floor grid (`_render_floor_after` shadowed by an instance attribute), clear colour. `camera._is_dirty` is forced True both ways (a camera that did not move would keep the projection of the previous size; the live view needs its own rebuilt). `camera._min_distance` is lowered for big enlargements. Alpha is forced to 1 so translucent parts do not print pale. Floating wire tables and concentric sections are ordinary canvas objects, so they print as on screen, made sharp for the print by `sharp_tables` (below). A wire highlight (blue) in effect when printing is printed too. `sharp_tables(canvas, dpi, scale)` is a context manager that has every floating table and section view re-captured at `ceil(dpi * scale / (25.4 * PIXELS_PER_MM))` times the pixels (so the texture has about one pixel per printed pixel; nothing happens when that is 1) and puts them back on exit, error or not. `job.print_layout` wraps the whole job in it, so the capture is done once per print, not per page.

## FOLDERS

None.
