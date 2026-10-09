# harness_designer/objects/objects_3d/menu_ops.py

Module of context-menu callbacks and helpers. None of its functions are on the
per-frame render path. Costs are per user action (a menu click, a dialog open),
not per frame or per mouse move, so no performance concerns from the review.

Note: `start_handler` and `run_attached_handler` have no callers and may be
dead code (see the functional review). `trace_circuit` runs per click and walks
the circuit's members once; it is O(members) per click, which is fine.
