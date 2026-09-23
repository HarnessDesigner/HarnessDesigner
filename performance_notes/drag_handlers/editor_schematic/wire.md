# harness_designer/drag_handlers/editor_schematic/wire.py

## Line 269-319 (`_find_blocking_wire`) — full project wire scan, called once per push-cascade level
The module docstring (lines 277-279) reasons that this "only ever runs once
or twice per interactive mouse move, never per A* neighbour" -- true for
the direct call from `__call__` (line 503), but `_attempt_push` (line
322-406) can recurse up to `_MAX_PUSH_DEPTH` (12) levels deep when a push
cascades through a stack of wires, and each recursive level that hits the
`reason == 'wire'` branch (line 382-388) calls `_find_blocking_wire` again
-- a fresh O(wires x segments-per-wire) scan per level, not just once or
twice, whenever a push chain actually engages multiple wires. The docstring
frames this as a bounded, not-expected-to-bind ceiling ("a generous ceiling
against a pathological stack... a real bundle is a handful of wires wide"),
which is probably right in practice -- flagging only because the actual
depth a real project's bundle stacks reach isn't verified here, and the
per-level cost compounds if it does bind.

## No profiling instrumentation, unlike the sibling `generic.py`
`editor_schematic/generic.py` (housing/terminal/splice drag) has built-in
`_TIMING`/`_PROFILE` flags for exactly this question -- measuring real
per-mouse-move cost instead of guessing from reading the code. This file
(wire segment drag, the more algorithmically involved of the two: push,
partial-jog, and reroute-fallback logic) has no equivalent. If the push/
jog path is ever suspected slow in a real large project, porting that same
instrumentation here would answer it directly rather than needing to
reason about it from the source.
