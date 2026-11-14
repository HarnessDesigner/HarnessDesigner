# harness_designer/objects/wire.py

Wire.delete releases the wire's WireSlackHandler first (2026-10-25; see handlers/MAP.md), so a deleted wire stops reacting to its points moving. All three views; imports terminal.py/splice.py (wire endpoints).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `Wire.trace_run` (lines 236-286, depth 3).

Status: static read of the code only. Nothing here has been profiled.
