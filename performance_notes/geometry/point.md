# harness_designer/geometry/point.py

This is the most heavily-used class in the codebase (every wire/housing/
terminal/cavity position, per MEMORY.md's "architectural backbone" note) --
worth treating any per-call overhead here as multiplied across the whole
app.

## Line 495, 525, 553 (`x`/`y`/`z` getters) and Line 1031 (`as_float`) — every coordinate read goes through `float(str(...))`
Reading any coordinate does `float(str(self._data[i]))` rather than a
direct `float(self._data[i])`. This is deliberate -- `_data` is float32
(see the corrected module docstring), and casting a `np.float32` straight
to Python `float` can surface binary-representation noise (e.g.
`float(np.float32(0.1))` -> `0.10000000149011612`) that the `str()`
round-trip avoids by using numpy's own shortest-repr formatting first.
Correct, but every single coordinate read anywhere in the app pays a
string format + parse for it. Same root cause as the finding in
`geometry/decimal.py` (`_ALLOWED_TYPES` round-tripping every arithmetic
result the same way) -- both stem from the same "avoid float32 noise via
string round-trip" pattern. Worth a benchmark against an alternative like
`round(float(self._data[i]), 7)` (float32 has ~7 significant decimal
digits) before assuming the string round-trip is the cheapest way to get a
clean value, given how hot this getter is.

## `__iadd__`/`__isub__`/etc. — already efficient on the callback side
Worth noting as a non-finding: every in-place operator writes all three
`_data` components before calling `_process_callbacks()` once (not once
per component), so the callback-firing cost already isn't multiplied per
coordinate. No change needed there.
