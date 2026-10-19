## FILES

#### __init__.py

`from . import edges as _edges` — re-exports `compile_program`.

#### edges.py

`compile_program()` — reads `vertex.vert`/`geometry.geom`/`fragment.frag` from disk, compiles each
stage via `shaders.compiler.compile`, links them into one GL program via
`GL.glCreateProgram`/`glAttachShader`/`glLinkProgram`, raising `RuntimeError` with the real
`glGetProgramInfoLog` on a link failure, and deletes the now-linked individual shader objects
before returning the program int. Wrapped by `program.EdgesProgram`.

#### fragment.frag

Sums ambient+diffuse+specular+emissive and (per the 2026-09-15 material rewrite — see
`gl/materials/material.py`) divides all 3 color channels by the peak channel together when it
exceeds 1.0, instead of relying on the GPU's implicit per-channel clamp-on-write — preserves the
true color's hue/ratio on overflow instead of distorting it.

#### geometry.geom

Geometry-shader stage — edges, like faces and vertices, is one of the 3 shader kinds built from a
per-vertex mesh via a GS stage rather than vertex+fragment alone.

#### vertex.vert

Edge-rendering vertex stage; shares the same `objectPosition`/`objectRotation` (quaternion)/
`objectScale` uniform contract `faces/vertex.vert` uses — see that file's MAP.md entry for the
GLSL quaternion component-name mismatch warning, which applies identically here.
