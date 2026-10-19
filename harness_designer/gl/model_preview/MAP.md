## FILES

#### __init__.py

`from . import canvas as _canvas` — package entry point.

#### canvas.py

A small, standalone preview canvas (ported from `wx.glcanvas.GLCanvas`; the module docstring
itself says the OBB calculation, camera setup, and all rendering logic are "completely unchanged"
from the wx version — only the host widget changed). Computes each model's oriented bounding box
itself via a PCA/eigen-decomposition (`_calculate_obb`, `np.cov` + `np.linalg.eig`) rather than
reusing a model's already-computed OBB elsewhere in the app. ⚠ Unlike every canvas built on
`canvas_base/`, this one was never migrated onto the modern VAO+shader pipeline — it still issues
legacy fixed-function immediate-mode GL calls directly (confirmed in source: `GL.glColorMaterial`,
`GL.glColor4f`, `GLU.gluPerspective`/`gluLookAt`). MEMORY.md documents a confirmed 2026-08-21 case
(`objects/objects_3d/housing.py`'s old cavity-overlay draw) where this exact call pattern
(`glEnableClientState`/`glVertexPointer`/`glColor4f` after `glUseProgram(0)`) silently rendered
nothing once a VAO from the real shader-pipeline rendering was left bound on the same GL context —
and `app.py` sets `AA_ShareOpenGLContexts` so model VBOs upload once and are shared across every GL
canvas including this one (per the repo-root `CODEBASE_MAP.md`'s "Shared GL contexts" note). This
file was not specifically tested for that failure mode while building this map, but it is exactly
the shape of code that class of bug hits — worth checking first, rather than assuming unrelated,
if this preview canvas is ever reported to render blank or garbled after other canvases have
rendered real geometry in the same process.
