## FILES

#### __init__.py

Package marker for `exporter/`; no logic of its own.

#### exporter.py

Project mesh export: takes already-tessellated vertex/normal buffers and writes them out through
either OpenCascade (OCP) or assimp, to whichever file format the user picked. The two backends are
fully independent, both operating on the same packed `(verts, normals)` numpy buffers with no
shared intermediate mesh type — the OCP path (`_build_ocp_face`/`_export_ocp`/`export_ocp`) builds
a `TopoDS_Face` directly from triangle data via `OCP.Poly.Poly_Triangulation`/`Poly_Triangle` +
`BRep_Builder` for CAD-oriented formats, while the assimp path
(`_build_assimp_scene`/`_export_assimp`/`export_assimp`) builds a `pyassimp`
`Scene`/`Mesh`/`Material`/`Node` graph by hand via raw `ctypes` pointer wiring
(`ctypes.cast`/`ctypes.pointer` into `structs.Face`/`structs.Mesh`/`structs.Vector3D` arrays) and
exports via `pyassimp.core.export`, for the broader mesh-interchange formats assimp supports. Each
backend has a `_with_progress` variant (`_build_ocp_face_with_progress`,
`_build_assimp_scene_with_progress`) accepting a `progress_cb(done, total, label)` for a UI
progress bar during large exports; the public `export_ocp`/`export_assimp` entry points both
accept an optional `progress_cb` and dispatch into these. Because the two paths share no
abstraction, a fix to triangle/normal handling in one (e.g. `_unpack`, `_safe_dir`, including
degenerate-normal handling) does not automatically apply to the other — check both when the bug
looks like shared logic. The assimp path in particular is built entirely through raw `ctypes`
manipulation against `pyassimp.structs`, with no higher-level assimp-Python API involved, so
changes there need to respect the manual memory/array layout rather than assuming a Pythonic
object model.
