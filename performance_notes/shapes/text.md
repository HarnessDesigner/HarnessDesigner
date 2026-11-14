# harness_designer/shapes/text.py

## `word_draw_data` (2026-11-14) -- placing a Text from outside
Returns each word's VBO and its scaled offset from the anchor, so a caller can place and draw the words with `VBOHandlerBase.render_raw` and array math instead of calling `Text.render` (which compares and copies `Point`s and composes `local_tilt + angle` in `Decimal` on a change: 0.7 ms per label in the 2D views on every frame). The rotation rings place their 36 labels this way: 0.70 ms a frame for the whole ring instead of 12-25 ms. Built once per ring; cheap (one small array).

## Line 126-198 (`_font_metrics`) — font tables built once per style
Builds the advance and kerning tables for a style the first time it is asked for, then returns the cached pair. Good: the font file is parsed once.

## Line 288-365 (`_tessellate_char`) and 377-409 (`_build_char`) — OCCT work per glyph, with a disk cache
Each glyph is built with build123d/OCCT and tessellated. This is the slow part of text. `_load_glyph_cache` (docstring) keeps the result on disk, so the next launch reuses it. A glyph is built once per style and cached in `_CHARS`.

## Line 416-533 (`build_chars`) — builds every glyph used by a string
Calls `_build_char` for each new character. Runs when a note's text changes. Cost is the number of new glyphs, not the length of the string.

## Line 628-897 (`_CameraTrackingArena`) — one arena for all tracked notes
Keeps the object, transform and bounds of every camera-tracked note in shared arrays, so a camera move updates them in one batched pass (see `update_camera_tracking`). `register` and `unregister` change the arrays (line 722, 768). Growing the arrays (`_grow`) copies them. Growth is by capacity steps, so it is rare.

## Line 914-1609 (`Text`) — the text object
`_build_mesh` caches its result in `self._mesh` (line 1483-1484), so the `data`, `vertices`, `smooth_normals`, `face_normals` and `vertex_count` properties do not rebuild the mesh on each access. Good.

`enable_camera_tracking` and `disable_camera_tracking` (lines 1372-1420) add or remove the owner in the arena. Called on note changes, not per frame.
