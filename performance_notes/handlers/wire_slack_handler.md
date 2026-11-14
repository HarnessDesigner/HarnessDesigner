# harness_designer/handlers/wire_slack_handler.py

One `WireSlackHandler` per wire (and per cable) binds a reconcile callback to the wire's points so any move re-fits the wire's length. Every move of a bound point that reaches `_on_pegboard_changed` runs `_reconcile`, so it sits on every peg-board drag and every housing move.

## Line 283-365 (`_reconcile`) — unbind, solve, rebind on every call
Inside the guards (`_released`, `_suspended`, `_loading`, `_reconciling_any`, `is_committing`) each reconcile does `unregister_pegboard()` (unbind from every bound point), `realize_length_change(...)` (one `_evaluate_points` plus a commit, see `rope_pull_handler.md`), then `register_pegboard()` (line 165-215) in the `finally`, which re-derives which points to bind and binds them again. The unbind/bind is O(bound points x callbacks per point) with `CallbackMixin.unbind`'s list scans (see `app_mixins/callback_mixin.md`), and runs once per reconcile, so per mouse move for every wire touched. It exists so that the move the reconcile itself makes does not re-trigger it (`_reconciling_any` already blocks nested calls, but the unbind keeps the callback list consistent while points move). If a profile shows `register_pegboard` / `_rebind` high, the cheaper alternative is to leave the binding in place and rely on `_reconciling_any` alone for the nesting, which removes the O(points) rebind from every move; it needs a check that no path depends on the temporary unbind.
When several wires are bound to the points of one housing move they reconcile one after another; the guard in `PJTHousing._update_position_pegboard` (suspend/resume of the chains' geometry) keeps the geometry rebuilds to one per wire, but each wire still pays a solve.

## Line 114-140 (`_rebind`)
`unbind` for each old weak reference, `bind` for each new point, then a new list of weak references. About 2 x points small operations; fine per call, multiplied by the reconcile count above.

## Memory
One handler and `n` weak references per wire; each bound point holds one extra `WeakMethod` (about 100 bytes). For 1,000 wires of 6 points that is under 1 MB. Not a concern.
