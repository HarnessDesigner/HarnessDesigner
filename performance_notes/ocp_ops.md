# harness_designer/ocp_ops.py

All OCP work runs on the single OCP thread (`@_ocp_thread` on `build_text_mesh`, line 250), one call at a time.

## Line 183-246 (`_tessellate_shape`) — per-vertex and per-triangle Python loops with an OCP call each
For every node it calls `Node(i).Transformed(trsf)` and `X()/Y()/Z()` (four OCP calls), and for every triangle three `tri.Value(...)` calls, appending Python tuples/lists, then `np.array` at the end. For a text glyph (a few hundred triangles) this is fine, and callers cache the result (see `shapes/mesh_cache.py` and `shapes/text.py`). For large shapes it would be the slow part; there is no cheaper pure-Python route without a bulk extraction API, so leave it and keep glyph meshes cached. The temporary Python lists are held until the arrays are built, so peak memory is roughly 3x the final arrays for a big shape. `gc.disable()` around the loop avoids collector pauses on the many short-lived tuples and is restored in `finally`.

`isInParallel=False` is passed to `BRepMesh_IncrementalMesh`, so tessellation is single threaded. Turning it on might speed up big shapes, but this module only handles small glyphs and OCP is serialised through one thread anyway; not worth the risk.

## Line 251-292 (`build_text_mesh`) — a font, a text builder, an extrusion and a fuse per call
The cost per string is the OCP boolean plus tessellation, milliseconds to tens of milliseconds. Callers must build a glyph once per (character, font, size, depth) and reuse the mesh (`shapes/text.py` does), never per frame.
