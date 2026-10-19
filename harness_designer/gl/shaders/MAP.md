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
`diameter`/`enabled`). This class (together with `gl/vbo.py`'s `render()`, which takes a `Program`
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
