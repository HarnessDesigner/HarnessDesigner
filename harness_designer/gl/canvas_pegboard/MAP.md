## FILES

#### __init__.py

`from . import canvas_window as _canvas_window` — package construction entry point, same pattern
`canvas_3d/`/`canvas_schematic/` use.

#### camera.py

`Camera(CameraBase)`, `is_top_down = True` — locked top-down orthographic 2D camera (pan moves the
focal position, zoom changes distance from the focal plane). Near-identical twin of
`canvas_schematic.Camera`: same docstring, same mechanics, differing only cosmetically (wording,
where the default-distance constant is placed) — not in behavior.

#### canvas.py

`Canvas(CanvasBase)` — the Peg Board Editor's GL surface. Reuses each placed part's EXISTING
`obj3d`/`_vbo`/material/scale (the same shared VBO/arena the 3D editor draws from, no new GPU
upload) under the real 3D shader pipeline with an identity object transform where the geometry is
already baked into world-space vertices, rather than building separate pegboard-only geometry for
most objects — mirrors the pattern pegboard wrapper objects in `objects/objects_pegboard/` already
use.

#### canvas_window.py

`CanvasWindow(CanvasWindowBase)` — thin wrapper, builds the inner `Canvas` then calls
`super().__init__()`. Byte-for-byte the same shape as `canvas_schematic.CanvasWindow` minus one
method: pegboard's version has no `add_preview_object` forwarder — nothing here registers an
in-progress wire-placement preview the way the schematic editor's wire tool does.

#### floor.py

`Floor(FloorBase)` — procedural top-down dot-grid floor, rendered in a single fragment-shader pass
on a viewport-sized quad resized every frame. Deliberately uses one power-of-2 spacing tier rather
than the major/minor "nice value" (1/5/10/50…) pair the old `canvas2d`-era `Grid` class used (see
the repo-root `CODEBASE_MAP.md`'s now-superseded description of that class) — dropped after visual
testing showed the old scheme's uneven 5×/2× jump ratios read as an inconsistent, sometimes
near-empty-looking grid, and the two tiers weren't visually distinguishable enough to tell apart
anyway. Confirmed byte-identical to `canvas_schematic/floor.py` except for one line of module
docstring ("peg board editor" vs "schematic editor") — a real, currently-unresolved duplication
between the two editors that has not yet been folded into the shared `floor_base.py` abstract
shell the way the three main render shaders were.

#### mouse_handler.py

`MouseHandler(MouseHandlerBase)` — the only override is `_get_view_object`, returning
`obj.objpegboard`. The old pegboard-only `_find_anchor_at_point` AABB hit-test is gone from current
source: this file is now exactly as thin as the 3D/schematic editors' and goes through the same
shared `gl.object_picker`/`MouseHandlerBase` dispatch they do — this closes the one gap MEMORY.md's
"new_canvas2d" notes (2026-08-12) had flagged as still open, so that specific claim there is now
stale.
