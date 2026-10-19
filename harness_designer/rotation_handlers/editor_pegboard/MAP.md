## FILES

#### __init__.py

Package docstring only. This package mirrors `rotation_handlers.editor_3d`'s own package shape (`generic.py` holds the real implementation), but single Y-axis only.

#### generic.py

`RingsPegboard(BasePegboard)` — a single Y-axis `rotation_ring.RotationRing` (protractor only, `has_torus=False` — no torus to pick between since there's only one axis). Same per-axis pick/activate/drag/snap API shape as `editor_3d.generic.Rings3D`, just reduced to one axis. The pegboard view is permanently locked top-down, so a rotation about world Y is the only one that's ever meaningful. Shares its reasoning almost verbatim with `rotation_handlers.editor_schematic` (single Y-axis, no torus, protractor already active on construction rather than waiting for a click) — see that package's MAP.md for the fuller rationale and the specific fix date (2026-09-22) this behavior was confirmed against. If one of these two gets a behavioral fix, check whether the other needs the identical fix.
