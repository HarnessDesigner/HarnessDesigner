# harness_designer/geometry/decimal.py

This wrapper is the single largest cost inside `Point`, `Angle` and `Quaternion` arithmetic. Measured 2026-11-13 with the real classes, interpreted Python 3.11 (a Cython build will be faster in absolute terms, but the share does not change much because `str()`, `float()` and `decimal` themselves are C calls either way):

| Operation | Time |
|---|---|
| `Decimal(1.5)` | 1.0 us |
| `Decimal + Decimal` | 2.0 us (a plain `decimal.Decimal` add is about 0.1 us) |
| `Point + Point` | 19-20 us |
| `Point @ Angle` | 66-70 us |
| `Angle.from_euler(...)` | 650-680 us (about 285 `Decimal` objects per call; `Decimal.__new__` is about 63% of the time) |
| `Angle + Angle` | 675-700 us |
| `Angle.copy()` | 193-197 us |

## Constraint: precision must not get worse (float drift in loops)
Plain `float` arithmetic is not an acceptable general replacement here: a loop that feeds its own output back in (repeated quaternion composition, repeated `+=` of a delta) accumulates rounding error. Every fix below has to keep or improve the precision of chained operations. Note that today every operator result is rounded to float64 by `__new__` (`float(str(...))`), so the `Decimal` only protects the inside of one operation; a loop of N operations already carries N float64 roundings.

## Line 33-52 (`__new__`) — `str(float(str(value)))` runs on every construction, including when `value` is already a `Decimal`
Every operator in the class (`__add__`, `__mul__`, `__truediv__`, ..., about 20 of them) wraps its raw `decimal.Decimal` result in `Decimal(...)`, which re-enters `__new__` and does `value = str(float(str(value)))` first. That normalisation exists for raw `float` input (the class docstring's `Decimal(0.1)` example). For a value that is already a `decimal.Decimal` it is wasted work and it also truncates the value to float64 precision.
Measured effect of skipping it for `Decimal` input (a monkey patch in a throwaway script, no source change):
- `Angle.from_euler`: 680 us -> 344 us.
- `Angle + Angle`: 698 us -> 376 us.
- `Angle.copy()`: 197 us -> 84 us.
- `Point + Point` and `Point @ Angle`: unchanged (their time is in `as_decimal` and in building `Decimal`s from float input, which still needs the normalisation).
Fix: `if isinstance(value, decimal.Decimal): return super().__new__(cls, value)`. No extra memory. **This is drift-safe, and reduces drift**: chained `Decimal` operations keep the context precision (28 digits) between steps instead of being rounded to float64 after every one. Results can differ from today's in the 16th significant digit and beyond; every coordinate still comes back through `float(str(...))` on the way out, so a position will not visibly change, but check that no code compares two results for exact equality that were computed by different routes. The cheapest large win in the geometry package.

## Beyond the quick fix — keep the precision, remove the wrapper inside the hot functions (proposal, not benchmarked)
Even with the fast path, `Angle + Angle` is hundreds of microseconds because the quaternion product, normalisation and matrix build each create dozens of wrapped `Decimal`s at about 2 us per operation. A raw `decimal.Decimal` operation is about 0.1 us. The drift-safe way to get most of the remaining gain is to do the multi-step maths inside `Angle`/`Quaternion` (product, normalise, matrix build) on raw `decimal.Decimal` values and wrap once when the result leaves the function. Same precision (better than today, since there are no intermediate float64 roundings), no extra memory (fewer temporaries). Benchmark it before committing to it; the expected result is a several-fold gain on `from_euler`, `+` and `as_matrix` without touching the numeric behaviour.

## Where plain float is safe
Only for values that are derived fresh each time from stored (float32) data and never fed back into a loop: for example the per-segment rotation in `objects_3d/wire.py` `_segment_transforms`, which is recomputed from the path for bounds, picking and rendering. A float64 result from float32 inputs is about nine digits better than what is stored. If float is used in any loop that does feed back, three rules keep drift bounded: recompute from the absolute value rather than accumulating deltas, renormalise a quaternion after each composition, and sum with `math.fsum`. Do not use it for stateful accumulation (a cached orientation updated by repeated composition).

## Precision (needs a decision, not a bug report)
Routing an exact `Decimal` result through `float(str(...))` discards precision on every operation. Millimetre-scale harness coordinates are far from the float64 limit, so this is harmless in practice, but the class's stated purpose is precision-safe maths, so confirm that is intended. The fast path above moves the rounding to the boundary (where a value leaves as a coordinate) instead of repeating it on every step.
