# harness_designer/objects/cavity.py

Wrapper for a housing's cavities. See the Rigid-child positioning convention note below — a cavity's world position/angle must come from its *immediate* parent housing, never re-derived from further up the chain.

Cold path (115 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
