# harness_designer/rotation_handlers/_axis.py

## Line 1-60 (`get_axis`, `set_axis`, `axis_color`) — explicit branches, no reflection
Three small functions that map an axis name (`'x'`, `'y'`, `'z'`) to an attribute with plain `if` branches. They replace `getattr`/`setattr` calls in the generic handlers and `inner_ring`. Each call is a few string comparisons, on the drag path only. Fine.

An unknown axis raises `ValueError` rather than falling through, so a bad axis name fails at the call site.
