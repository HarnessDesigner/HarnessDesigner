## FILES

#### __init__.py

Package docstring only. This package is a single-Y-axis protractor, reusing the exact same `rotation_ring.RotationRing` class 3D/pegboard use (it only ever needed a GL context and a camera, never anything 3D-view-specific). Kept as its own view package rather than folded into `editor_3d` so a future real schematic rotation gizmo has a home without another restructure. The package's own `__init__.py` docstring describes `Rings2D` as "currently just... a dummy placeholder (the rotation gizmo is 3D-only for now; see `..editor_3d.generic` for the real implementation)" even though `Rings2D` itself is a real, working single-axis gizmo — don't read "dummy placeholder" as "non-functional"; it means this view's rotation support is a reduced subset of the real (3D) one, not that it doesn't work.

#### generic.py

`Rings2D(BaseSchematic)` — single Y-axis `rotation_ring.RotationRing` (`has_torus=False`). The 3D gizmo's always-on torus exists so the user can pick which of 3 axes to rotate about; with only one axis here there's nothing to pick between, so the protractor is already active the moment this gizmo is built (`__init__` calls `self.activate('y')` directly) instead of waiting for a click on a ring that would otherwise be the only thing ever shown. Confirmed 2026-09-22 as the fix for both the pointless extra click and the gizmo taking a visible moment to appear. Also has `_route_attached_wires` — re-routes every wire attached to the object being rotated, tying rotation directly into the schematic auto-router (rotating an object here isn't purely a visual/transform change, it can trigger a reroute of every wire touching it, same spirit as `drag_handlers.editor_schematic.generic.Generic`'s live-reroute-on-move).
