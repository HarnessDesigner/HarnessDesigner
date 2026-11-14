# harness_designer/geometry/angle/angle.py

Measured 2026-11-13 on the real class, interpreted Python 3.11, isolated profile:

| Operation | Time |
|---|---|
| `a.x` read | 0.46 us |
| `a.as_matrix_numpy` | 0.06 us (cached array, no conversion) |
| `Angle.from_euler(10, 20, 30)` | 650-680 us |
| `a + b` | 675-700 us |
| `a.copy()` | 193-197 us |
| `p @ a` (rotate a Point) | 66-70 us |

## Composition and construction cost 0.2-0.7 ms each — almost all of it is `Decimal`
`from_euler`, `__add__`/`__iadd__`/`__sub__`/`__isub__` (lines 494-616) and `copy` (431-442) build the result through `Quaternion` arithmetic done in `Decimal`. A profile of `from_euler` shows about 285 `Decimal` objects per call and `Decimal.__new__` (the `str(float(str()))` normalisation) as about 63% of the time. These run on every rotation drag frame for every rotated object and for each cavity of a rotated housing, so a rotation of an object with 50 children is tens of milliseconds in the interpreter. Fixes, in order of effort (see [../decimal.md](../decimal.md) for the measurements):
1. Skip the normalisation for `Decimal` input in `Decimal.__new__`. Measured: `from_euler` 680 -> 344 us, `a + b` 698 -> 376 us, `copy` 197 -> 84 us. No memory cost.
2. Rewrite `Quaternion.__mul`, `__norm` (the normalise step) and `as_matrix` on raw `decimal.Decimal` (a raw add is about 0.1 us against 2.0 us wrapped) and wrap once at the end. Same precision as today or better, so repeated composition does not drift; expect a several-fold gain (benchmark first). No memory cost, fewer temporaries. Plain `float` was considered and rejected as the default because loops accumulate error; it is safe only for `as_matrix`-style results derived fresh each time (see [../decimal.md](../decimal.md)).

## Line 313-334, 369-390, 407-428 (`x`, `y`, `z` setters) — each one rebuilds the quaternion and the matrix, even inside `with angle:`
`x`, `y` and `z` each store the Euler value, call `Quaternion.from_euler(*euler)` and `__update_quat` (four component sets plus `__update_matrix`, which is `as_matrix` and nine element copies), then `_process_callbacks()`. `with angle:` (`CallbackMixin.__enter__`) only makes `_process_callbacks()` return early; it does not skip the rebuild. Measured: one `a.x = v` is 0.67 ms, so setting all three axes costs about 2 ms. `PJTHousing._update_angle3d` sets all three on each of the cavity, terminal and seal angles and then overwrites `_q` and `_matrix` with the quaternion it already has, so on a 100-cavity housing that is 300 objects x 3 discarded rebuilds, 613 of the 676 ms of a rotate frame (see `database/project_db/pjt_housing.md`). Fix: add a method that sets the Euler list, the quaternion and the matrix together without recomputing (a direct assignment measured 0.05 ms per object, with an identical final state on 50 random angles), and use it wherever a caller already holds all three. Per-axis setters are fine for a user typing one value; they are expensive when called in a loop with three axes.

## Line 99-226 (`__array_ufunc__`) — `float(str())` and `tolist()` eight times per ufunc call
Used when an `Angle` appears in a NumPy expression. Not on the per-frame path today; if a hot caller shows up, convert once with `as_quat_float`.

## Line 299-405 (`x`/`y`/`z`) and 740-800 (`as_*_float`) — `float(str())` per component
Same root cause and recommendation as in [../point.md](../point.md): about 0.5 us per read versus 0.1 us direct. Small per call; matters in loops over many angles.

## Line 479-491 (`__update_matrix`) — rebuilds the cached rotation matrix eagerly on every change
Each angle change calls `Quaternion.as_matrix` (about 216 us per call in the profile of `from_euler`, roughly a third of its total, because the 3x3 is built with `Decimal` arithmetic) and then copies it element by element in a 3x3 loop. The matrix is eagerly refreshed even if nobody reads it before the next change; during a rotation drag many intermediate angles are never read as matrices. Making the matrix lazy (compute on first `as_matrix_numpy` read after a change, using a dirty flag) would skip the cost for angles that are only composed; it costs one bool per angle and a branch per read. Doing the matrix in plain `float` arithmetic (see `quaternion.md`) is the bigger saving and is needed anyway.

## Line 842-1095 (`from_direction`, `from_matrix`, `from_points`, `from_frame`)
One-shot constructors with NumPy (4 to 9 small allocations each). Fine unless called per vertex; `from_direction`'s docstring records an earlier benchmark-driven fix.

## Memory
An `Angle` holds a `Quaternion` (four float32), a cached 3x3 matrix and the callback lists, about 300-400 bytes. The matrix cache is worth its memory because `as_matrix_numpy` is read far more often than the angle changes.
