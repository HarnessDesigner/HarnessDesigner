## FILES

#### __init__.py

No module docstring; package marker only.

#### _axis.py

`get_axis`/`set_axis`/`axis_color` — explicit per-axis (`'x'`/`'y'`/`'z'`) branches instead of `getattr`/`setattr`, so an unknown axis fails loudly (matches the codebase-wide "never use getattr/hasattr to control flow" convention — see MEMORY.md).

#### rotation_mesh.py

Shared geometry helpers — per-axis ring-plane orientation math (`slot_ring_angle`/`slot_normal`), angle wrapping (`wrap_angle`), and the unit torus mesh (`build_ring_mesh`) the always-on activation ring renders. Ring planes follow the same nested Euler order `objects.objectsvar..._angle.Angle.from_euler` itself uses — effective matrix `Ry*Rx*Rz` (Z innermost, X middle, Y outermost), verified numerically in this module's own docstring.

#### rotation_rings.py

`RotationRings(ObjectBase)` — the facade tying one view-specific implementation per view together (mirrors every `objects.*` type's own facade/view-package split), built by `Base3D.handle_interaction`/the schematic and pegboard equivalents when a selected object enters angle mode. Only the one view matching whichever canvas armed it is actually constructed. The 3D gizmo class is the class attribute `_rings_3d_class`; `WireRollRings(RotationRings)` (same file) overrides it with `editor_3d.wire_roll.WireRollRings3D`, so a wire service loop's "Rotate on Wire" ring is armed, dispatched and rendered through exactly the same `_active_handler` / `isinstance(..., RotationRings)` paths as the ordinary gizmo.

## FOLDERS

#### editor_3d/

The real 3-axis implementation (`Rings3D`). See `editor_3d/MAP.md`.

#### editor_pegboard/

Single-Y-axis implementation (`RingsPegboard`). See `editor_pegboard/MAP.md`.

#### editor_schematic/

Single-Y-axis implementation (`Rings2D`). See `editor_schematic/MAP.md`.

#### rotation_ring/

The shared torus+inner+outer ring assembly and its individual ring implementations, used by every view. See `rotation_ring/MAP.md`.

This whole package is the protractor-style rotation gizmo shown around a selected object in angle mode — the rotation counterpart to `add_handlers/` (placement) and `drag_handlers/` (translation), part of the same "object-driven handler classes, not canvas isinstance checks" rebuild (MEMORY.md, 2026-08-17). It replaces the old single-ring-per-axis gizmo and the fixed-handle `DragRotate` drag that used to live in `gl/canvas_3d/rotation_rings.py`/`move_arrows.py` (confirmed dead; do not touch, see `drag_handlers/MAP.md`'s note on the same rule). Right-clicking a selected object shows three always-on activation rings (one per Euler axis, in 3D — `rotation_ring.torus_ring.TorusRing`). Clicking one shows that axis's protractor — an object-space inner ring (spins with the object, grab-and-drag anywhere on its band free-rotates about this axis) and a world-space outer ring (own spin held fixed; hover a tick to highlight it, click to snap the object's local zero to that exact angle) — and dims the other two axes' torus rings. Only the Euler value is ever written; the quaternion is rebuilt from it by `geometry.angle.Angle`. Like `add_handlers/`/`drag_handlers/`, this package is essentially undocumented in the repo's top-level `CODEBASE_MAP.md`. A "Future rotation-rings redesign" is recorded in MEMORY.md (2026-08-17, explicitly a "side thought," not implemented at the time): a protractor-styled disc with degree ticks, click-anywhere-on-the-ring-band instead of small grab handles, and a translucent glow-fill on the active axis while dragging. **Most of this has since been built** — the current `rotation_ring/` package already is the protractor-disc-with-ticks design and grab-anywhere-on-the-band inner ring described there; re-check against that MEMORY.md entry before assuming anything it describes is still purely aspirational, and before proposing further redesign work without asking (the glow-fill-while-dragging part specifically does not appear to be built yet, based on the files in `rotation_ring/` — verify before assuming either way).
