# harness_designer/exporter/exporter.py

## Line 139-152 (`_build_assimp_scene`) and Line 288-303 (`_build_assimp_scene_with_progress`) — per-vertex Python loop to fill a ctypes array from a numpy array
Vertex and normal data starts as a numpy `(N, 3)` float32 array (`verts`/
`normals`) and is copied into a `ctypes` array of `structs.Vector3D` one
element at a time: `v_arr[i].x = float(verts[i, 0])`, `.y`, `.z`, repeated
per vertex, twice (once for positions, once for normals). Each iteration
pays both Python loop overhead and `ctypes` attribute-set overhead.

If `structs.Vector3D` is a plain 3-float struct with no padding (worth
confirming against `pyassimp/structs.py`), its memory layout is identical
to a C-contiguous `(N, 3)` float32 numpy array, which means this could
become a single bulk copy instead of an N-iteration loop -- e.g.
`ctypes.memmove(v_arr, verts.astype(np.float32, copy=False).ctypes.data, verts.nbytes)`
(and the same for `n_arr`/`normals`), replacing two O(n) Python loops with
two `memmove` calls. Whether this matters depends on how large an exported
mesh typically is -- a full harness assembly's tessellated geometry could
plausibly be large enough for this to be noticeable in a one-shot export
(not a per-frame path, but still a user-facing wait).

**Caveat for `_build_assimp_scene_with_progress` specifically:** its whole
purpose is periodic `progress_cb` calls during the fill (lines 294, 302) --
the very existence of a progress-reporting variant suggests this loop is
already known/expected to take long enough to need one for large meshes.
A bulk-copy replacement would need to either accept losing that granular
feedback or fake progress around the single `memmove` call. The plain
`_build_assimp_scene` (used by `_export_assimp`, no progress reporting) is
the cleaner target for this change.

Not applicable to the OCP path (`_build_ocp_face`/`_build_ocp_face_with_progress`,
lines 55-73/252-276): `Poly_Triangulation.SetNode`/`SetNormal` are OCP's
own bound API calls, not a self-authored ctypes fill -- there's no bulk-set
entry point visible in this module to substitute.
