# performance_notes/geometry

Covers `harness_designer/geometry/` (`point.py`, `line.py`, `decimal.py`, `cavity_layout.py`) and `geometry/angle/` (`angle.py`, `quaternion.py`).

## Highest-cost item in the whole package: `Decimal`
`Point` and `Quaternion`/`Angle` arithmetic goes through `geometry/decimal.Decimal`, whose `__new__` does `str(float(str(value)))` on every construction. Measured 2026-11-13 (interpreted): `Point + Point` 19 us (NumPy equivalent 3.9 us), `Point @ Angle` 66-70 us, `Angle.from_euler` 650-680 us, `Angle + Angle` 675-700 us, `Angle.copy()` 193-197 us. Skipping the normalisation for values that are already `Decimal` halves the Angle numbers (see [decimal.md](decimal.md)); moving `Quaternion` composition and `as_matrix` to plain `float` arithmetic would remove nearly all of it (see [angle/quaternion.md](angle/quaternion.md)). This is where rotation drags spend their CPU, and it costs no memory to fix.

## Smaller items
- `p.x`/`.y`/`.z` and `Angle.x`... do `float(str(...))` per read (0.47 us versus 0.10 us direct) ([point.md](point.md)).
- `Angle.__update_matrix` rebuilds the cached rotation matrix on every change, about 216 us of `Decimal` work each ([angle/angle.md](angle/angle.md)).
- `CallbackMixin._process_callbacks` costs only 0.6 us for a Point with no listeners and about 5 us with three, so the callback system itself is not the problem ([../app_mixins/callback_mixin.md](../app_mixins/callback_mixin.md)).

## Memory
Points and angles are a few hundred bytes each and interned ones are weak-referenced. Nothing here needs more memory to go faster; the fixes above reduce temporary objects.
