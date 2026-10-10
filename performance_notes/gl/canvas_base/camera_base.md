# harness_designer/gl/canvas_base/camera_base.py

## Line 1-205 — module docstring is ASCII art
About 175 lines of diagrams in the docstring. No runtime cost, only file size.

## Line 213-215 and 280-296 (`CameraBase.__init__` and `_updating_rig`)
Creates two `Point`s and two `Angle`/`Line` helpers once per camera. The `_updating_rig` flag is the fix for a double recompute on rigid moves; the comment explains why a context manager was rejected. Good.

**Import style:** line 193 uses `from harness_designer import app as _app`, an absolute import. Every other module in `gl/` uses a relative import (`from ... import app`). It works, but it breaks the file's style and makes the import order matter. Flag for the typing pass.

## Line 292-296 (`_update_camera`) — `CallAfter` on every move
Every position or focal-point write calls `_app.CallAfter(self.canvas.update)`. A drag makes many writes per second, and each posts a repaint request. Qt coalesces repaint requests, so the visible cost is small, but it is one posted event per move. Could be coalesced with a dirty flag and a single pending `CallAfter`.

## Line 457-507 (`_send_event`, `_refresh_active_hover`) — synchronous work on every camera move
Every camera move emits a signal, then `_refresh_active_hover` runs, which calls `self.set()`, reads the cursor position, and dispatches a MOVE to the active handler. This happens during a drag and during key-driven moves (see `key_handler.md`). The matrix work is one `_calculate_camera` if dirty. The handler dispatch is the expensive part when a wire is being placed. Acceptable for interactive use, but it runs on every key repeat tick too.

## Line 645-662 (`set`) — gated on `is_dirty`
Good: only recomputes the basis vectors when the camera moved.

## Line 664-738 (`_calculate_camera`) — basis vectors, allocated each call
Builds several small NumPy arrays and does two `cross` calls per call. Runs only when dirty. Fine. The `_WORLD_UP.copy()` on line 682 is a per-call copy of a module constant; it is copied because the fallback writes into `up`. Fine.

## Line 741-798 (`set_view`) — per-frame matrix work when dirty
Called from the canvas `_set_view` only when the camera is dirty (3D: `_set_view` rebuilds every frame; see `canvas_3d/canvas.md`). Each call:
- one matrix multiply (`projection @ modelview`);
- one 4x4 inverse (`np.linalg.inv`);
- one frustum extraction and two `ascontiguousarray` copies.

About 20 small allocations and a 4x4 inverse per call. If the 3D canvas calls `set_view` every frame, this is the per-frame cost. The 2D canvases gate on `is_dirty`, so they are fine.

## Line 800-906 (`Rotate`, `_rotate_about`) — per-drag-event work and a nested function
`_rotate_about` defines `_rodrigues` each call (nested `@_check_types.do` function). It is called twice per call. The function object is cheap to create, but it is created on every mouse drag event. Moving it to module level would avoid that. `_rotate_about` also carries both `@staticmethod` and `@_debug.logfunc`, so `logfunc` runs on every drag tick (see `key_handler.md` for the same `logfunc` concern).

## Line 908-1100 (`PanTilt`, `Zoom`, `Walk`, `Dolly`, `TruckPedestal`) — movement methods
Each is a few NumPy operations plus one `_send_event`. Each is wrapped with `_debug.logfunc`. Same `logfunc` concern as above.

**Signature check needed:** `Walk` takes `(dx, dy, speed)` (line 973) and `TruckPedestal` takes `(dx, dy, speed)` (line 1062). `CanvasWindowBase.Walk` calls `self._canvas.Walk(delta_z, delta_x)` with two arguments. Whether `CanvasBase.Walk` supplies `speed` needs checking in `canvas_base.py`.

## Line 1026-1058 (`Dolly`) — rigid translation
`if distance == 0: return` before any work. Fine.

## Line 1102-1128 (`CenterOn`) — rigid translation
One subtraction and two additions. Fine.

## Line 1130-1165 (`ProjectPoint`) — called per object in culling and picking
Builds a 4-element array from the point on every call, one matrix-vector product, then Python arithmetic on NumPy scalars. Called per object (see `canvas_window_base.md`, `object_picker.md`). Vectorising over all objects would be faster, but this is per object only on user actions.

**Typing:** `ProjectPoint` returns `None` when `clip_point[3] == 0`, but was annotated `-> _point.Point`. Changed to `-> _point.Point | None` in this pass. Callers already check for `None` (see `canvas_window_base.objects_in_window`).

## Line 1167-1194 (`UnprojectPoint`) — uses the cached inverse
Uses the cached `_inv_clip`, so no per-call inverse. This matches the intent of `set_view`. Good.

## Line 1196-1209 (`unproject_from_ndc`) — `np.isclose` and in-place divide
Per call one matrix-vector product, one `isclose`, one in-place divide. Called from `get_mouse_ray`. Fine.

## Line 1211-1246 (`get_mouse_ray`) — the ray used by picking
One unproject, one subtraction, one norm. Called once per pick. Fine.

## Line 1248-1265 (`get_position_on_focal_plane`) — per mouse move while a handler is armed
Called from add handlers on each mouse move. `self.focal_distance` goes through `float(str(...))` (line 350), the same string round-trip as in `material.md`. It is one call per move, but `focal_distance` can just return the stored float.

## Line 1267-1319 (`closest_point`) — vectorised and per-point paths
Two paths: a vectorised NumPy path for an `(N, 3)` array, and a Python loop for individual points. Both use squared distance, so no `sqrt`. Good. The Python loop path does one `np.asarray` per point; pass an array for large candidate sets.
