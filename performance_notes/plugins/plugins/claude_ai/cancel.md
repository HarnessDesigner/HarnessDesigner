# harness_designer/plugins/plugins/claude_ai/cancel.py

CancelToken — cancellation for an in-flight Claude call. Predates (and is distinct from) the more general plugins/ai/cancel.py CancelToken, which is generalized from this one with an added reason (REASON_STEER vs REASON_CLOSE) — see plugins/ai/MAP.md. Whether this module should eventually be replaced by that one, or kept as this backend's own, isn't resolved yet.

Cold path (71 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
