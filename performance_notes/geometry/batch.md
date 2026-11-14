# harness_designer/geometry/batch.py

Array versions of the quaternion, matrix, Euler and point rotation math, for the pooled slots. Built 2026-11-14 and checked against the real classes (`Quaternion.__add__`, `Quaternion.as_matrix`, `pjt_housing._euler_from_matrix_continuous`, the old point rotation): worst difference 3e-16 (quaternion), 3e-8 (matrix), 2e-5 degrees (Euler), float32 rounding for points.

## Cost
Measured (interpreted, 100 cavities): the per-cavity math of a rotate frame is 0.42 ms with these functions against 60 ms for the per-object loop (144x); rotating 700 points is about 90 us. Everything is float64 NumPy on arrays of a few hundred rows, so the per-call overhead (a dozen array operations) is the whole cost and is already small.

## Memory
Each call allocates temporaries of a few hundred rows: `(n, 8, 3)` for the rotated OBB corners is 19 KB for 100 cavities, the rest is smaller, all freed on return. Preallocating them would save microseconds and keep tens of KB resident, so it is not worth doing.

## Precision
The stored data is float32 (as it always was); the intermediates are float64 and each quaternion product is renormalised, so a loop that feeds results back in (a drag is one rotation delta per frame) has the same float32 rounding floor per frame as before and no worse. Plain float math on `Decimal`-wrapped objects is a different question (see `decimal.md`).
