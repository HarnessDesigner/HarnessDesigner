## FILES

#### __init__.py

Package init.

#### bounding_boxes.py

`compute_aabb()`, `compute_obb()`, `adjust_aabb()` — axis-aligned and oriented bounding-box math, consumed heavily by `bounds/` and the GL/culling pipeline.

#### mesh_normals.py

`compute_normals()`, `compute_smooth_normals()`, `compute_face_normals()`, `compute_face_indexes()` — builds the packed vertex/normal layout `gl/vbo.py` expects (see `gl/MAP.md`'s 3D rendering pipeline notes).

#### mesh_surface.py

`Surface` — a mesh-surface value type (likely one planar/curved region of a picked/analyzed mesh, consumed by `mesh_surface_picker.py` and the housing-editor connector analysis — see `ui/dialogs/housing_editor/MAP.md`).

#### mesh_surface_picker.py

Mesh surface picking (ray/triangle hit testing). `split_into_components()`'s vectorization history is a real lesson: a scipy-based rewrite (`scipy.sparse.csgraph.connected_components`) caused a 24.6s → 72s regression because real housing meshes have many small raw groups and scipy's per-call overhead multiplied across them — the fix keeps one cheap vectorized global vertex-weld pass (`np.unique`) but does per-group connected-components as a plain Python BFS over the pre-welded ids. General lesson: when a hot path is called many times with small/variable-size inputs rather than once over one huge array, don't reach for numpy/scipy vectorization by default — benchmark against plain Python first, and remember the Cython-compiled release build doesn't make a vectorized approach's per-call overhead disappear. Separately, `_refresh_transform_cache`/`_on_angle` get the forward-vs-inverse transform right by convention: when building a matrix-based ray/point transform cache from `Angle.as_matrix_numpy`, store `rot = angle.as_matrix_numpy`; forward (local→world) uses `rot.T`; inverse (world→local) uses `rot` (unrotated/plain) — easy to get backwards, and picking then silently misses or hits the wrong geometry rather than raising.

#### model_utils.py

`compute_edges()`, `convert_model_to_mesh()`.

#### natural_sort.py

`natural_sort_key(name)` — a sort key for "human" ordering of names containing numbers (e.g. "Terminal 2" before "Terminal 10"), for use as a `list.sort(key=...)`/`sorted(..., key=...)` argument wherever names are shown in UI lists.

#### paths.py

`get_appdata()`, `get_documents()` — platform app-data/documents directory lookups. `get_appdata()` uses a non-recursive `os.mkdir`, so a scratch/sandboxed `USERPROFILE` must have its `appdata/roaming` parent pre-created or this raises `FileNotFoundError` (see the root `MAP.md`'s "Config is a live DB" note — this directory is also where `config.db` and the log files live). `paths.py` also owns `SKELETON_WORKER_NAME` (`'Skeleton Generator Worker'`, the name of the worker process PyCharm builds stubs in; re-exported as `utils.SKELETON_WORKER_NAME`) -- the one place that string is written. `config.py` and `logger/log_handler.py` compare `multiprocessing.current_process().name` against it, and so does `get_appdata()`, which skips its `os.mkdir` on a match: three `Config` class bodies in `config.py` call it, so it runs on every import of this package.

#### remap.py

`remap()` — linear value-range conversion (map a value from one `[min, max]` to another).

#### snap_pool.py

`SnapPool` — numpy-backed nearest-point lookup used by the various snap-to-grid / snap-to-point interactions.

#### ui_utils.py

`HSizer()`, `IMAGE_FILE_WILDCARDS`, `MODEL_FILE_WILDCARDS` — small Qt layout helper plus file-dialog filter constants.

#### window_geometry.py

`safe_center(target_rect, candidate_size)` — computes a `QPoint` to center a window/dialog of `candidate_size` within `target_rect` without going off-screen; likely used by dialogs that don't inherit standard centering (or need to center against a specific monitor rect rather than the primary screen).

#### wire_conversions.py

AWG / mm² / diameter conversions for wire sizing. This is the single sanctioned place for wire-size derivation — don't inline a fallback chain elsewhere. Wire size columns (`wire_size_dia`/`wire_size_cross`/`wire_size_awg` on `wires`, similarly on `seals`/`terminals`) can be NULL even though derivable from a sibling column; the plan is a standalone maintenance utility (invoked from an app menu, eventually also run automatically when a new part is added) that scans for NULLs and backfills via this module — *not* a 3-way dia←cross←awg fallback chain added into handler/query code. Code reading a wire-size column that could be NULL should add NULL-safety (`IS NULL OR` guards, skip-if-None) only, and leave derivation to the maintenance utility.
