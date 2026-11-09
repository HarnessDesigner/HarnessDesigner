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

(2026-11-05) a twisted conductor's stripe (the local `stripeHalf`, 0 = off, and `stripeAmbient`/`Diffuse`/`Specular`, which since 2026-11-08 come only from the batched wire's entry; the `twistStripe*` uniforms are gone) is painted where `fragStripeGeom`, the angular distance from the stripe's centre, is below the half width; the base material's three colours are copied into `baseAmbient`/`baseDiffuse`/`baseSpecular` first and everything after uses those. **(2026-11-08)** The material is read into locals first (`matAmbient`, `matDiffuse`, `matSpecular`, `matEmissive`, `matShininess`, `rimPower`, `rimIntensity`, `stripeHalf` and the stripe's three colours), from the uniforms, or, when `fragEntryGeom` is 0 or more (a batched wire, cable or bundle), from the batched wire's entry in `twistEntries` (texels 2 to 8; the rim glow is worked out as `Material.set` does: the sum of the emissive colour times 2). `fwidth(fragStripeGeom)` is now evaluated outside the stripe `if` (a derivative in a branch that differs between primitives is undefined).

Sums ambient+diffuse+specular(+emissive for the glow branch) and divides all 3 channels by the
peak channel together when it exceeds 1.0 (the 2026-09-15 material-rewrite fix — see
`gl/materials/material.py`), **except** for the emissive glow branch specifically, which is
deliberately left to overflow/clamp per-channel so the rim-glow effect is allowed to run hot.

#### geometry.geom

Geometry-shader stage building the smooth/face-normal-aware mesh faces are rendered through. Passes `fragStripe` through to `fragStripeGeom` (2026-11-05, for the twisted conductors' stripe), and (2026-11-08) the flat `fragEntry` to `fragEntryGeom` in both the triangle and its reflection.

#### vertex.vert

TWISTED CONDUCTORS (2026-11-05, reworked 2026-11-08; `TWISTED_WIRE_DESIGN.md` sections 5 and 7): with the `twistBatch` uniform above 0 (the default is 0, and `gl/wire_batch.py` sets it back to 0 after its draw) `main()` skips the mesh attributes entirely: `loadBatchPiece()` finds the vertex's ENTRY (one conductor, or a bare conductor end, of a wire in view, 10 texels in the texture buffer `twistEntries`: the wire's first row and row count, the entry's first vertex, the stripe half angle, the twist rate and the conductor's circle, the material, and in texel 9 the vertex within the wire's draw where the entry's rows begin) by a binary search on the entries' first-vertex values, `loadPiece(base, count, vertex)` finds the piece in the wire's rows of `twistPieces` (`gl/wire_pool.py`, 5 texels per row, first vertices relative to the wire so rows can move) by a second one, and `twistVertex()` builds the vertex from `gl_VertexID`: a tube of `rings` rings of `TWIST_SIDES` (16) sides, two triangles per quad, in real mm in the piece's own frame (`objectScale` is not used). The cross-section turns by `phase + rate * z` about the axis, the mitre closes the outside of a bend (both rings moved onto the bisecting plane, faded in over the last `w` mm), and `fragStripe` carries the angular distance from the stripe's centre. `flat out int fragEntry` carries the entry's number to the fragment stage (-1 for every other draw, set first thing in `main`); the geometry shader passes it on and the fragment shader reads the material from the same texels. The per-piece (`twistRings`, `twistLength`, ... uniforms) and per-wire (`twistPool`) modes that existed until 2026-11-08 are gone, with the program's `twist_*` properties for them and `TwistedTube`; checked pixel-identical (max channel difference 0, 100 random wires, also over 8 arenas and after a compaction) to the image the per-piece draw made, and ordinary meshes identical to the committed shaders. The edges and vertices programs have no twist mode (a wire's debug passes are not drawn). **Smooth bends (2026-11-08):** the radial normal of a piece is blended, over the distance the mitre fades in over, towards the bisector of its own and the neighbouring piece's normal at the joint (`smoothAcrossJoint`; the neighbour computes the same bisector, so the pieces agree): the rounded corner, a run of short pieces, used to show as facets (a normal jump at every joint) and now shades as one surface. Everything that is not a twisted conductor pays one assignment and one `twistBatch` test.