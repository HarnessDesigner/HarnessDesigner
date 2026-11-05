## FILES

#### __init__.py

`from . import shader_program as _shader_program` — re-exports `ShaderProgram`.

#### compiler.py

`compile(source, shader_type)` — the one shared helper every shader submodule's own
`compile_program()` calls to compile a single GLSL stage (vertex/geometry/fragment), raising
`RuntimeError` with the real `glGetShaderInfoLog` on failure. Does not link programs itself — each
submodule's `compile_program()` does its own `glCreateProgram`/`glAttachShader`/`glLinkProgram`.

#### program.py

Defines `Program` (a ref-counted `with program:` wrapper around `GL.glUseProgram`/
`glUseProgram(0)`, with typed write-only uniform properties whose GL locations are cached once at
construction) and its 6 concrete subclasses — `FacesProgram`/`EdgesProgram`/`VerticesProgram`/
`GridProgram`/`FloorProgram`/`TextureProgram` — each wrapping one compiled program int from the
matching submodule's own `compile_program()`. `FacesProgram` is the one with `has_normal_mode =
True` and owns the headlight spotlight uniforms (`headlight_position`/`direction`/`diffuse`/
`diameter`/`enabled`) and, since 2026-11-05, the twisted-conductor uniforms (`twist_rings`/`length`/`rate`/`phase`/`profile`/`start`/`end` and `twist_stripe_half`/`ambient`/`diffuse`/`specular`; see `faces/vertex.vert`). This class (together with `gl/vbo.py`'s `render()`, which takes a `Program`
object itself, never a raw location int) is meant to remain the only place in the app that calls
`GL.glGetUniformLocation`/raw `GL.glUniform*`/`GL.glUseProgram` directly — every consumer
(canvases, `vbo.py`, `materials/material.py`, drag/rotation handlers, floor renderers) gets handed
a `Program` instance and sets uniforms only through its properties.

#### shader_program.py

`ShaderProgram` — owns one instance each of the 6 `Program` subclasses (`.grid`/`.faces`/
`.edges`/`.vertices`/`.floor`/`.texture`). ⚠ Despite the repo-root `CODEBASE_MAP.md`'s older
description of this as a process-wide singleton (`_ShaderProgramMeta`), the current class's own
docstring explicitly rejects that design: each of the 3 canvases is a separate `QOpenGLWidget`
with its own non-shared GL context and constructs its OWN `ShaderProgram` from `initializeGL`
(with that canvas's context current) — a process-wide cache would hand a later-constructed
canvas program ids only valid in whichever canvas's context compiled them first, which is exactly
the cross-context `GL_INVALID_OPERATION` bug this per-canvas design replaced. Treat "one
`ShaderProgram` per canvas instance," not "one `ShaderProgram` ever," as current when reasoning
about this class.

## FOLDERS

#### edges/

Compiles the edge-rendering GL program (`vertex.vert` + `geometry.geom` + `fragment.frag`) wrapped
by `program.EdgesProgram`.

#### faces/

Compiles the face-rendering GL program (`vertex.vert` + `geometry.geom` + `fragment.frag`) wrapped
by `program.FacesProgram` — the program headlight uniforms and the material-rewrite's
peak-channel-normalize overflow fix both live here.

#### floor/

Compiles the 3D procedural floor program (`vertex.vert` + `fragment.frag`, no geometry stage)
wrapped by `program.FloorProgram`, used only by `gl/canvas_3d/floor.py`.

#### grid2d/

Compiles the 2D procedural dot-grid program (`vertex.vert` + `fragment.frag`, no geometry stage)
wrapped by `program.GridProgram`, shared by both `canvas_schematic/floor.py` and
`canvas_pegboard/floor.py`.

#### texture/

Compiles a small textured-quad program (`vertex.vert` + `fragment.frag`, no geometry stage)
wrapped by `program.TextureProgram` — not documented anywhere in the repo-root
`CODEBASE_MAP.md`'s older "## `gl/`" section at all; its real consumer is
`objects.objects_pegboard.table.Table`'s floating wire table.

#### vertices/

Compiles the vertex-point-marker program (`vertex.vert` + `geometry.geom` + `fragment.frag`)
wrapped by `program.VerticesProgram`.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### A real app crash: `Program.__enter__`'s ref count could get permanently stuck (found + fixed 2026-10-27)
After ~14 idle minutes `GL.glUseProgram(28)` (a face program that had worked all session) raised `GLError(1282)` inside `Program.__enter__` (`gl/shaders/program.py`), cascading into 104 "object render error" entries in under a second (one `glUseProgram` error then 101 `glUniform4fv` ones) and a hard `access violation` crash in `canvas.repaint()` (faulthandler dump `crash_*.log`; no Python-visible cause). Root cause: `__enter__` incremented `_ref_count` BEFORE calling `glUseProgram` with no `try`; when it raised, Python never called `__exit__`, leaving the count stuck at 1, so the `if self._ref_count == 1: glUseProgram(...)` rebind never fired again and every later `material.set(...)` ran with no program current. **Fix:** `glUseProgram` is called first (when `_ref_count == 0`) and the count is incremented only after it succeeds, so a failure is retried next frame. What first invalidated the program id is unknown (no TDR or power event in the Windows logs). `Program` and its subclasses in `gl/shaders/program.py` are the only place meant to call `glUseProgram`; route any other direct call through a `Program` `with` block. The same increment-after-success ordering applies to any first GL call inside `__enter__`/`__exit__` (e.g. `canvas_base.py`'s `self.context` wrapper, not audited).
