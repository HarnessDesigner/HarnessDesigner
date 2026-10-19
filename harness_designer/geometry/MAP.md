## FILES

#### __init__.py

Package marker for `geometry/`; no logic of its own. The package holds the core numeric geometry
types used throughout the app: `Point`, `Line`, a Cython-friendly `Decimal` subclass, and (in
`angle/`) `Angle`/`Quaternion`. **`Point` and `Angle` together are the reactive backbone of the
whole program.** Their `CallbackMixin`-backed `bind()`/`unbind()`/`with:`-batching system (see
`app_mixins/callback_mixin.py`) is not one reactive pattern among several available in this
codebase — the user (sole author) called it directly and emphatically "literally the backbone to
this entire program" (2026-08-17), confirmed empirically: in one session alone this same
unmodified mechanism drove camera dirty-gating, the 3D headlight's direction tracking, the
rotation-rings gizmo following a selected object, the 2D camera mirroring on pan, and a planned
protractor feature's camera-facing labels — every one a materially different problem solved with
nothing more than another `bind()` call. Default to `Point.bind()`/`Angle.bind()` for any new
reactive behavior here before inventing a new event/signal mechanism. Writers that are also bound
listeners must use the **unbind -> write -> rebind** idiom to avoid feedback loops (see
`prop_ctrls` and `Rings3D.apply_drag_angle` for the reference pattern).

#### cavity_layout.py

**Not a procedural mesh generator like `shapes/`** — this computes 2D layout geometry for
engraving/placing cavity-number text around a housing's cavity stack (`compute_stack_geometry`,
`CavityStackGeometry`, `CavityGeometry.point_at_180`/`z_shift_at_180`,
`compute_housing_cavity_geometry`). It imports `build123d` directly (via `shapes.text`'s
`Text`/`CHARACTER_HEIGHT`/`TOP_DOWN_TILT`) — a deliberate exception to the "`shapes/` is NOT
build123d" rule, not a drift from it, since it's about engraved text geometry rather than
primitive mesh generation (see `shapes/MAP.md`'s `text.py` entry for the other half of this
exception).

#### decimal.py

`Decimal(decimal.Decimal)` — a stdlib-`Decimal` subclass that overrides every arithmetic dunder
(`__add__`/`__radd__`/`__mul__`/`__pow__`/etc.) to always return this subclass rather than plain
`decimal.Decimal`, so decimal-precision arithmetic composes cleanly through `Point`/`Line`/`Angle`
math without silently downgrading back to the stdlib type.

#### line.py

`Line` — a two-`Point` segment with its own operator overloading (`__iadd__`/`__add__`/etc.
translate both endpoints; `__imatmul__`/`__matmul__` rotate around the line's own frame),
`length`/`center`/`p1`/`p2` properties, `get_angle`/`set_angle` (same origin-relative convention as
`Point`), `point_from_start(distance)`, `get_rotated_line`, `get_parallel_line`,
`project_to_line`, `__contains__` (point-on-segment test), and `bow_midpoint(target_length)` — the
closed-form single-bow bulge-to-length construction that `rope_pull_py.solve_chain`'s `count == 1`
case deliberately matches exactly (see `rope_pull/MAP.md`).

#### point.py

`Point` — a `CallbackMixin`-backed, metaclass-managed (`PointMeta`) 3D point. `PointMeta.__call__`
interns/tracks instances via weakrefs (`_remove_ref`) rather than being a plain constructor.
Supports full numeric-operator overloading (`__iadd__`/`__add__`, `__isub__`/`__sub__`,
`__imul__`/`__mul__`, `__itruediv__`/`__truediv__`,
`__matmul__`/`__imatmul__`/`__rmatmul__` for rotation via an `Angle`) and a numpy
`__array_ufunc__` hook so it interoperates with raw numpy arrays and with `Angle`/`Line`/
`Quaternion` directly. `set_angle`/`get_angle` convert to/from an `Angle` relative to an origin
point. `attach()`/`detach()` implement a **self-healing-alias mechanism** (a point's identity
permanently merges into another's) — this is explicitly a *different* concept from the
`parent_point_id` child-tracking mechanism described in MEMORY.md's "Wire-snap feature" entry:
`attach()` is a permanent self-healing alias used for wire-placement-preview point merging, while
`parent_point_id` (a `pjt_points3d`/`pjt_points2d`/`pjt_points_peg` DB column, not anything in this
file) is a *different*, independently-written row that just also tracks a parent's position going
forward, used for multiple wires sharing one terminal's snap point — the user explicitly corrected
a case where the latter was mislabeled "clone" in code/comments, so don't conflate the two.
Separately, **the rotation matrix convention is load-bearing and has caused a real bug**:
`Angle.as_matrix_numpy` returns the **column-vector** rotation matrix `R` where `R @ v` rotates a
column vector, but everywhere in the codebase that applies rotation via numpy `@` (e.g. `corners
@= angle`, including this file's own point/line math) uses **row-vector** convention, equivalent
to `v @ R.T`. So: `world = (local * scale) @ R.T + position`, inverse: `local = (world - position)
@ R / scale`. A bug in `MeshSurfacePicker` had `rot_mat`/`inv_rot` swapped (`R` vs `R.T`) — worked
at zero rotation (`R == I`) but broke picking/overlay rendering once a housing was actually
rotated. When building any matrix-based ray/point transform cache from `Angle.as_matrix_numpy`:
store `rot = angle.as_matrix_numpy`; forward (local->world) uses `rot.T`; inverse (world->local)
uses `rot` (see `utils/mesh_surface_picker.py` `_refresh_transform_cache`/`_on_angle` for the fixed
reference implementation).

## FOLDERS

#### angle/

`Angle` and `Quaternion` — the rotation half of the `Point`/`Angle` reactive pair documented above
under `__init__.py`. See `angle/MAP.md` for the full breakdown; its "Point/Angle callback system"
dependency and the rotation-matrix-convention gotcha both apply equally there.
