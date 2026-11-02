## FILES

#### __init__.py

Package init.

#### bounding_boxes.py

`compute_aabb()`, `compute_obb()`, `adjust_aabb()` — axis-aligned and oriented bounding-box math, consumed heavily by `bounds/` and the GL/culling pipeline.

#### hdm.py

The `.hdm` ("harness designer model") file format: how every numpy file the application keeps on disk (imported 3D models and the primitive/glyph caches) is written and read. An `.hdm` file is a two-line text header (`#` lines: the copyright, then a note that the data comes from unknown sources and the copyright covers only the way it is written, not the data) followed byte for byte by what numpy itself writes: `.npy` for a model (`save`/`load`), `.npz` for a cache (`save_arrays`/`load_arrays`). numpy has no slot for metadata and cannot read past a prefix, so **nothing may `np.load` an `.hdm` path directly**; `load()`/`load_arrays()` skip the header first (a header line starts with `#`, a numpy payload never does, so lines can be added to `HEADER` without touching a reader), and `load(path, mmap_mode='r')` parses the `.npy` header itself and returns an `np.memmap` at the payload's offset, so a model is still streamed to the GPU rather than copied. Writes go through a temp file and `os.replace`. `migrate(path)` upgrades a pre-hdm `.npy`/`.npz` of the same name in place (rewritten as `.hdm`, checked, then the old file deleted); it must convert rather than ignore old files because a model's source file is deleted once it is converted, so an old `.npy` model cannot be rebuilt. A lock serialises it: Windows cannot replace or delete a file another thread has open, and eight racing threads failed without one. Re-exported from `utils` as `HDM_EXTENSION`, `save_hdm`, `load_hdm`, `save_hdm_arrays`, `load_hdm_arrays`, `migrate_hdm`.

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

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Wire-size NULL backfill plan
Wire size columns (`wire_size_dia`/`wire_size_cross`/`wire_size_awg` on `wires`, similarly on `seals`/`terminals`) can be NULL even though derivable from a sibling column (conversion helpers exist in `utils/wire_conversions.py`).

As of 2026-07-09: don't add a 3-way fallback-calculation chain (dia ← cross ← awg) into handler/query code. The user is writing a standalone maintenance utility (invoked from an app menu) that scans for NULLs and backfills via `utils/wire_conversions.py`; later this will also run automatically when a new part is added.

**How to apply:** When writing queries/logic reading a wire-size column that could be NULL, do not add derivation-from-other-columns logic inline — assume the maintenance utility will keep these populated, only add NULL-safety (`IS NULL OR` guards, skip-if-None). If asked for the actual backfill utility later, that's a separate feature using `utils/wire_conversions.py`.

#### Saved numpy files are `.hdm` files with a copyright header (user, 2026-10-25)
Every numpy file the app saves (imported 3D models `<model_path>/<uuid[:2]>/<uuid>.hdm`, one array; per-name primitive meshes `<appdata>/<name>.hdm`; the glyph cache `glyph_cache.hdm`) uses the extension `.hdm` ("harness designer model") and a text header: the copyright line, then a line saying the data comes from unknown sources and the copyright covers only the way it is written, not the data. There is no `.hdma`; every file gets the header.
- `utils/hdm.py` (re-exported from `utils` as `save_hdm`, `load_hdm`, `save_hdm_arrays`, `load_hdm_arrays`, `migrate_hdm`, `HDM_EXTENSION`) is the only code that may read or write these files; nothing else calls `np.load`/`np.save`/`np.savez` on them. A header line starts with `#` and a numpy payload never does (`\x93NUMPY` or `PK`), so lines can be added to `HEADER` without touching a reader. `gl/vbo.create_model_vbo` memory-maps via `load_hdm(path, mmap_mode='r')`.
- Old files upgrade via `migrate_hdm` where the path is built (`Model3D.data_path`, the caches); loaders read only `.hdm` (the user's "no fallback paths"). A `<uuid>.npy` model is copied byte for byte behind the header (the source CAD file is deleted after conversion, so it cannot be rebuilt), size-checked, then the `.npy` deleted. A lock serialises conversions (Windows cannot replace a file another thread has open). A cache that fails to convert is a miss and rebuilds; a model that fails raises out of `data_path`.
- Not run in the real app; the six model loaders were compiled and read only. Existing, unchanged: importing `harness_designer.database.global_db.model3d` as the very first import hits a circular import (`global_db.mixins` <-> `ui`); import `harness_designer.ui` first when scripting.
