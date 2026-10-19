## FILES

#### __init__.py

`from . import faces as _faces` — re-exports `compile_program`.

#### faces.py

`compile_program()` — reads `vertex.vert`/`geometry.geom`/`fragment.frag` from disk, compiles each
stage via `shaders.compiler.compile`, links them via `glCreateProgram`/`glAttachShader`/
`glLinkProgram` (raising with the real `glGetProgramInfoLog` on failure), deletes the individual
shader objects, and returns the linked program int. Wrapped by `program.FacesProgram`, the
`Program` subclass that also owns the headlight spotlight uniforms.

#### fragment.frag

Sums ambient+diffuse+specular(+emissive for the glow branch) and divides all 3 channels by the
peak channel together when it exceeds 1.0 (the 2026-09-15 material-rewrite fix — see
`gl/materials/material.py`), **except** for the emissive glow branch specifically, which is
deliberately left to overflow/clamp per-channel so the rim-glow effect is allowed to run hot.

#### geometry.geom

Geometry-shader stage building the smooth/face-normal-aware mesh faces are rendered through.

#### vertex.vert

Contains `quaternionToMatrix(vec4 q)`. ⚠ Confirmed still present and unchanged: the codebase's
quaternion convention is scalar-first `(w, x, y, z)`, but in GLSL here the vec4 component names do
NOT match that order — `q.x` is read as `w`, `q.y` as `x`, `q.z` as `y`, `q.w` as `z`. Any code
feeding this uniform a quaternion from an xyzw-ordered library (e.g. scipy) needs reordering at the
boundary before it reaches here. `edges/vertex.vert` and `vertices/vertex.vert` both contain the
exact same function with the same component mismatch.
