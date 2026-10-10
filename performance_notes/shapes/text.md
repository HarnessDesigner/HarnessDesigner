# harness_designer/shapes/text.py

## Line 124-160 (`_font_metrics`) — font tables built once per style
Builds the advance and kerning tables for a style the first time it is asked for, then returns the cached pair. Good: the font file is parsed once.

## Line 286-376 (`_tessellate_char`) and 377-409 (`_build_char`) — OCCT work per glyph, with a disk cache
Each glyph is built with build123d/OCCT and tessellated. This is the slow part of text. `_load_glyph_cache` (docstring) keeps the result on disk, so the next launch reuses it. A glyph is built once per style and cached in `_CHARS`.

## Line 410-420 (`build_chars`) — builds every glyph used by a string
Calls `_build_char` for each new character. Runs when a note's text changes. Cost is the number of new glyphs, not the length of the string.

## Line 610-890 (`_CameraTrackingArena`) — one arena for all tracked notes
Keeps the object, transform and bounds of every camera-tracked note in shared arrays, so a camera move updates them in one batched pass (see `update_camera_tracking`). `register` and `unregister` change the arrays (line 722, 768). Growing the arrays (`_grow`) copies them. Growth is by capacity steps, so it is rare.

**Reflection removed (fixed in this pass):** `_CameraTrackingArena` probed each owner with `hasattr(owner, 'refresh_canvas_registration')` (lines 714 and 1407-1408 area) and `getattr(owner, '_vbo', None)` (line 818). Every owner passed in is a 3D note, which defines both members, so the calls are direct now. An owner type without those members would raise `AttributeError` instead of being skipped. The only callers are `objects_3d/note.py`.

## Line 892-1571 (`Text`) — the text object
`_build_mesh` caches its result in `self._mesh` (line 1483-1484), so the `data`, `vertices`, `smooth_normals`, `face_normals` and `vertex_count` properties do not rebuild the mesh on each access. Good.

`enable_camera_tracking` and `disable_camera_tracking` (lines 1372-1420) add or remove the owner in the arena. Called on note changes, not per frame.

**Typing (fixed in this pass):** owners are typed by a `CameraTrackedOwner` protocol (the `_obb`, `_aabb`, `_vbo` attributes and `refresh_canvas_registration`). `Callable` comes from `collections.abc`. The Qt context import is module-qualified.
