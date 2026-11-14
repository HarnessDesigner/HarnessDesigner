# harness_designer/plugins/ai/cancel.py

CancelToken/Cancelled, generalized from ../plugins/claude_ai/cancel.py's version (formerly ../../claude/cancel.py before that package's relocation) one layer up, with a *reason* (REASON_CLOSE — the Session itself is shutting down, stop and do not re-send; REASON_STEER — "Send now", discard the in-flight call and immediately re-send with the folded-in message, the Job keeps running).

Cold path (98 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
