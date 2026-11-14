# harness_designer/geometry/point.py

The most used class in the app (every wire, housing, terminal and cavity position is a `Point`). Per-call overhead here is multiplied across a drag. Measured 2026-11-13 on the real class, interpreted Python 3.11, in an isolated profile (not the live config):

| Operation | Time | A plain equivalent |
|---|---|---|
| `p.x` read | 0.47 us | `float(data[0])` 0.10 us |
| `p.as_numpy` | 0.06 us | (a view, no copy) |
| `p.as_float` | 2.1 us | |
| `p.as_decimal` | 7.8 us | |
| `Point(1.0, 2.0, 3.0)` (no db_id) | 2.0 us | |
| `p.copy()` | 3.5 us | |
| `p + q` | 19.2 us | NumPy add then `Point(...)`: 3.9 us |
| `p + ndarray` | 17.8 us | |
| `p += q` (in place, no listeners) | 24.3 us | |
| `p @ angle` | 66-70 us | |

## Line 494-560 (`x`/`y`/`z`) — `float(str(self._data[i]))` on every coordinate read
About 0.5 us versus 0.1 us for a direct `float(...)`. It is deliberate (a float32 cast straight to `float` shows binary noise such as `0.10000000149011612`; the `str()` round trip uses numpy's shortest repr). Four times slower than plain, but in absolute terms small; a render pass that reads 10,000 coordinates pays 5 ms for it, which is why it matters per frame. A cheaper way to get the same clean value is worth a benchmark (for example `round(float(data[i]), 7)`; float32 carries about 7 decimal digits), and anything that reads whole points should use `as_numpy` (no conversion) instead of three getters. Also in `PointMeta.__call__` (line 101-144): three more `float(str(...))` conversions per construction, even for an existing singleton.

## Line 649-758 (`__add__`, `__sub__`, `__mul__`, `__truediv__`) and 791-834 (`__imatmul__`) — arithmetic goes through `Decimal`
`p + q` is 19 us, about 5x the NumPy equivalent, because it builds `self.as_decimal` (7.8 us: three `Decimal`s each normalised with `str(float(str()))`), `__other_to_decimal(other)` (another three), three `Decimal` additions (each result re-normalised) and then `Point(x, y, z)` (three more conversions). `p @ angle` (66-70 us) is the same pattern: line 761-788 converts back and forth with `tolist()` and `float(str(item))` for every component. `p += q` (24 us) is the one the drag handlers use, so it is the most important. The drag move paths call these per object per mouse move, so 20-70 us each adds up for housings with many cavities and for wire waypoints (hundreds per frame is already several ms).
Fix options, cheapest first:
1. `decimal.py`'s fast path (see [decimal.md](decimal.md)): does not help `Point + Point` (measured, unchanged) because the cost is building Decimals from float input, but removes the double normalisation inside the Decimal results.
2. Do the arithmetic in float64 on `_data` (`p._data.astype(np.float64) + other`) and construct the result once. Measured 3.9 us for the add. It changes results only below float32 resolution (the stored `_data` is float32 anyway), and because the result is stored back as float32 each time, a `p += q` loop has the same rounding floor (one float32 rounding per step) as today. That holds only for state kept in a `Point`; a loop that accumulates in a local variable must not switch to float without the drift rules in [decimal.md](decimal.md). No memory cost; it removes about 15 us per operation.
3. For `__matmul__`/`__imatmul__`, rotate with the quaternion's rotation matrix directly (one 3x3 multiply) instead of through the `Decimal` quaternion.

## Line 579-590 (`copy`) and 1037-1041 (`as_float`) — list comprehension of `float(str())`
3.5 us and 2.1 us. Fine unless called per vertex.

## Line 985-1012 (`__bool__`, `__eq__`) — allocate or compare via NumPy
`__bool__` builds an array per call (`np_alloc`); `__eq__` calls a NumPy compare. Both tiny, but `if point:` in a hot loop pays an allocation. Prefer `is not None` where the intent is a None check.

## `__iadd__`/`__isub__`... — callbacks fire once, not per coordinate
In-place operators write all three components before calling `_process_callbacks()` once. Measured firing cost: 0.6 us with no listeners and about 5 us with three (see [../app_mixins/callback_mixin.md](../app_mixins/callback_mixin.md)); the arithmetic above dominates it.

## Memory
`Point` keeps one 3-element float32 array plus the callback lists. Interned `Point`s (those with a `db_id`) are held by weakref in `PointMeta._instances`, so unused points free themselves. Caching Decimal triples on the point would speed `as_decimal` but costs three `Decimal` objects (about 300 bytes) per Point and needs invalidation on every write; with Point counts in the hundreds of thousands that is tens of MB for a gain that fix option 2 gives without any memory, so do not do it.
