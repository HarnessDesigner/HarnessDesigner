# harness_designer/geometry/angle/quaternion.py

The cost is not NumPy call overhead (the old note's reading) but `Decimal`: the arithmetic runs through `as_decimal`, `Decimal` multiplies and `Decimal` normalisation. In a profile of `Angle.from_euler`, `Quaternion.from_euler` is 77% of the time, `__mul` 50% and `__norm`/`__init__` 33%, and about 285 `Decimal`s are created per call. See [../decimal.md](../decimal.md) for the table and the fixes.

## Line 31-120 (`__array_ufunc__`) — 5 NumPy allocations and 4 `Quaternion` objects per call
Only used for NumPy expressions that contain a `Quaternion`; not a frame-rate path.

## Line 386-405 (`__mul`, the Hamilton product), 122-172 (`__norm`), 175-197 (`__init__`)
`__init__` normalises every new quaternion, so every composition pays a normalise on top of the product. A float-only product plus normalise is about a dozen multiplies and one square root; as `Decimal` it is hundreds of microseconds. Moving these three off the wrapped `Decimal` is the best speed-up available in the geometry package (no memory cost; fewer temporaries), but loop drift rules out plain `float` as the default (see [../decimal.md](../decimal.md), "Constraint"): do the product, normalise and matrix build on raw `decimal.Decimal` and wrap once at the end (same precision, about 20x cheaper per operation than the wrapper), and keep plain `float` for results that are derived fresh and never fed back.

## Line 550-621 (`__matmul__`, `__rmatmul__`) — rotate a point or array
Five small NumPy allocations per call. Used by `Point @ Angle` (66-70 us measured for the whole operation, most of it `Decimal` conversion in `Point`, see [../point.md](../point.md)).

## Line 635-725 (`conj`, `__neg__`, `negation`), 624-632 (`__iter__`), 317-325 (`as_float`)
Each builds the result with `float(str())` per component and `tolist()`; about 3.6 us for `as_float`. Fine per call; not for loops over thousands.

## Line 729-849 (`from_euler`, `as_euler`, `as_matrix`, `from_axis_angle`)
One-shot conversions; `from_euler` is the expensive one because it multiplies three axis quaternions with `Decimal` (see above). `as_matrix` (789-810) builds the 3x3 with `Decimal` arithmetic at about 216 us per call (profiled) and is called by `Angle.__update_matrix` on every angle change; it is a prime candidate for a rewrite on raw `decimal.Decimal` (precision kept). The matrix is derived fresh from the quaternion every time, so a float64 build is also safe here if the raw-Decimal version is still too slow.

## Memory
A `Quaternion` is a 4-element float32 array plus small caches; the cost per object is a few hundred bytes. No memory concern.
