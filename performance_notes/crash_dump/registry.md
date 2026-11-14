# harness_designer/crash_dump/registry.py

@capturable(severity=None) — a class decorator declaring which attributes/properties (via Attr/ @dump_property-tagged properties, see schema.py) a crash dump may read from instances of that class, and at what severity.

Nested loops (cost grows with the product of the sizes; check the sizes are small): `_resolve_own_severity` (lines 75-88, depth 2), `decorator` (lines 105-145, depth 2).

Status: static read of the code only. Nothing here has been profiled.
