# harness_designer/geometry/decimal.py

## Line 33-52 (`__new__`) — every arithmetic result round-trips through `str(float(str(value)))`, including when the input is already a `Decimal`
Every dunder in this class (`__add__`, `__sub__`, `__mul__`, `__truediv__`,
etc. -- all ~20 of them) wraps its raw `decimal.Decimal` result back
through `Decimal(...)`, which re-enters `__new__` and does
`value = str(float(str(value)))` before calling `super().__new__`. This
was written to fix the specific case of a raw `float`/`int` input
producing an ugly imprecise `Decimal` (see the class docstring's own
`Decimal(0.1)` example), but it runs unconditionally -- including when
`value` is already a proper `decimal.Decimal` (the normal case here, since
every dunder passes the exact result of `_Decimal.__add__`/`__sub__`/etc.,
never a raw float). `Point` (`geometry/point.py`) uses this `Decimal` type
for x/y/z storage, so every coordinate arithmetic op anywhere in the app
pays this: two string conversions and a `float()` round-trip, per
operation, most of the time on a value that didn't need any of that.

Two separate things worth splitting out:

1. **Performance:** skip the `str(float(str(value)))` normalization
   when `isinstance(value, decimal.Decimal)` already -- only genuinely
   float/int input needs it. This alone would remove the double
   string-round-trip from the common internal case (Decimal-to-Decimal
   ops) while keeping the original fix for raw float/int input intact.

2. **Precision (needs discussion, not asserted as a live bug):** routing
   an already-exact `Decimal` result through `float(str(value))` truncates
   it to IEEE-754 double precision (~15-17 significant digits) before
   parsing it back into a `Decimal` -- for a class whose entire stated
   purpose is precision-safe decimal math, this discards precision on
   every single operation, not just on construction from a raw float. In
   practice, millimeter-scale harness coordinates are almost certainly
   nowhere near float64's precision ceiling, so this may never matter for
   real project data -- but it's worth confirming that's actually true
   (and always will be, e.g. no accumulated-rounding-over-many-ops
   scenario) rather than assuming it from the class's own docstring intent.
