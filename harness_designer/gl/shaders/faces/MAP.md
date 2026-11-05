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

(2026-11-05) `twistStripeHalf` (0 by default = off) and `twistStripeAmbient`/`Diffuse`/`Specular` paint a twisted conductor's stripe where `fragStripeGeom`, the angular distance from the stripe's centre, is below the half width; the base material's three colours are copied into `baseAmbient`/`baseDiffuse`/`baseSpecular` first and everything after uses those.

Sums ambient+diffuse+specular(+emissive for the glow branch) and divides all 3 channels by the
peak channel together when it exceeds 1.0 (the 2026-09-15 material-rewrite fix — see
`gl/materials/material.py`), **except** for the emissive glow branch specifically, which is
deliberately left to overflow/clamp per-channel so the rim-glow effect is allowed to run hot.

#### geometry.geom

Geometry-shader stage building the smooth/face-normal-aware mesh faces are rendered through. Passes `fragStripe` through to `fragStripeGeom` (2026-11-05, for the twisted conductors' stripe).

#### vertex.vert

TWIST MODE (2026-11-05, `TWISTED_WIRE_DESIGN.md` sections 5 and 7): when the `twistRings` uniform is above 0 (the default is 0, and `shapes/twisted_wire.py` sets it back to 0 after every draw) `main()` skips the mesh attributes entirely and `twistVertex()` builds the vertex from `gl_VertexID`: a tube of `twistRings` rings of `TWIST_SIDES` (16) sides, two triangles per quad, in real mm in the segment's own frame (`objectScale` is not used). The cross-section turns by `twistPhase + twistRate * z`, so a conductor's centre is a helix; normals are analytic; `twistStart`/`twistEnd` mitre the end rings onto the bisector plane of a bend, faded in over their `w` mm. `fragStripe` is the angular distance from the centre of the conductor's stripe, 1000.0 for every other draw. The edges and vertices programs have NO twist mode yet (the wire's debug passes are skipped for a twisted wire).

Contains `quaternionToMatrix(vec4 q)`. ⚠ Confirmed still present and unchanged: the codebase's
quaternion convention is scalar-first `(w, x, y, z)`, but in GLSL here the vec4 component names do
NOT match that order — `q.x` is read as `w`, `q.y` as `x`, `q.z` as `y`, `q.w` as `z`. Any code
feeding this uniform a quaternion from an xyzw-ordered library (e.g. scipy) needs reordering at the
boundary before it reaches here. `edges/vertex.vert` and `vertices/vertex.vert` both contain the
exact same function with the same component mismatch.
