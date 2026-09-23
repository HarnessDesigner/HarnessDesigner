# harness_designer/drag_handlers/editor_schematic/generic.py

This file is already well-optimized (single GL context entry for the whole
move, drag-arm-time caching of `_attached`, set-based membership checks in
`_route`) and already carries its own built-in profiling scaffolding:
`_TIMING` (line 55) prints per-phase timing on every drag event, `_PROFILE`
(line 62) runs `cProfile` over a window of drag events and prints the
busiest functions. No separate perf investigation needed here beyond
flipping those two flags on and dragging a housing with several attached
wires in a real project -- that answers "is `_route`/`follow_moved`
actually slow at real scene sizes" directly instead of guessing from
reading the code. Nothing else in this file stood out as a concrete,
actionable finding.
