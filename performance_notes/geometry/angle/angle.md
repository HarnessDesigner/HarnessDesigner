# harness_designer/geometry/angle/angle.py

## Same `float(str(...))` round-trip pattern as `geometry/point.py`
The `x`/`y`/`z` getters (lines ~304, ~362, ~400 after edits) and several
`as_*_float` properties read cached Euler/quaternion components via
`float(str(value))` rather than a direct `float(value)`, for the same
float32-noise-avoidance reason documented in `performance_notes/geometry/point.md`.
Same recommendation applies here: worth a benchmark against a cheaper
"round to float32 precision" alternative given how often `Angle` component
reads happen (bound to the same per-object callback/render paths as
`Point`). Not re-detailing the full reasoning here -- see the `point.py`
note, which covers the shared root cause.

No other distinct findings in this file -- the rotation-math functions
(`from_matrix`, `from_points`, `from_direction`, etc.) are one-shot
construction calls with extensive existing author commentary on the
numerical tradeoffs already made (see `from_direction`'s docstring for an
example of a deliberate, already-benchmarked fix in this exact file).
