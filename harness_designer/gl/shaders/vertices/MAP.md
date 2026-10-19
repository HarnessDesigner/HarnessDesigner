## FILES

#### __init__.py

`from . import vertices as _vertices` — re-exports `compile_program`.

#### fragment.frag

Fragment coloring for each rendered vertex-point marker.

#### geometry.geom

Geometry-shader stage expanding each mesh vertex into its rendered point/marker shape.

#### vertex.vert

Contains the same `quaternionToMatrix(vec4 q)` function (and the same scalar-first-`(w,x,y,z)`-
vs-GLSL-component-order mismatch — `q.x`=w, `q.y`=x, `q.z`=y, `q.w`=z) as `faces/vertex.vert` and
`edges/vertex.vert` — see `faces/MAP.md`'s entry for the full ⚠ warning, which applies identically
here.

#### vertices.py

`compile_program()` — compiles+links `vertex.vert` + `geometry.geom` + `fragment.frag` into
`program.VerticesProgram`.
