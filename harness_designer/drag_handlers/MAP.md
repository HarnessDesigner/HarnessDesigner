## FILES

#### __init__.py

No module docstring; empty/package marker only.

#### base.py

`DragHandlerBase` — the shared construct/call/destroy lifecycle every drag handler follows: a concrete handler is constructed fresh the moment a drag is armed (one instance per drag, never reused across drags), called once per mouse-move via `__call__(delta, mouse_pos)` for the drag's duration, and torn down via `delete()` the moment the drag ends (commit or abort) — the same lifecycle `add_handlers.base.AddHandlerBase` and `rotation_handlers`' gizmos follow. Holds only what's genuinely identical regardless of editor/object type (a reference to the canvas and the dragged object); everything that differs by *view* (screen<->world projection, axis locking, whether a move-arrows gizmo exists at all) belongs on that editor's own intermediate base (`editor_3d`/`editor_schematic`/`editor_pegboard`), not here.

#### move_arrows.py

`MoveArrows` — the axis-aligned directional-arrows gizmo (`Arrows3D`/`ArrowsSchematic`/`ArrowsPegboard` per-view facades) shown once a 3D drag's axis lock engages. Deliberately NOT registered via `mainframe.add_object` — not a real scene object, so `delete()` is a no-op.

#### wire_marker_arrow.py

`WireMarkerArrow`/`ArrowMarker3D` — the bidirectional arrow gizmo for a wire-marker drag, oriented along the wire instead of a world axis. Structurally mirrors `move_arrows.py` but takes an orientation supplied directly (`angle_for_direction`) rather than one of `'x'`/`'y'`/`'z'` — a wire marker's drag is constrained to an arbitrary (non-axis-aligned) line. Its rotation math was verified numerically against `Arrows3D`'s own hardcoded per-axis quaternions before use — `shapes.arrow.create_vbo`'s mesh points along local +X, NOT local -Z like `geometry.angle.Angle.from_points` assumes for every other object in the codebase, so `from_points` cannot be reused here without producing a mirrored/incorrect orientation. Also used by the wire-locked service-loop drag (`editor_3d/wire_service_loop.py`), which has to rebuild it when a bend turns the wire: the arrow's orientation is fixed at construction and it follows only the Point it is given.

## FOLDERS

#### editor_3d/

3D-editor drag handlers, including the free-orbit-camera axis-lock mechanics every 3D drag shares. See `editor_3d/MAP.md`.

#### editor_pegboard/

Peg-board drag handlers (length-budget clamp / rope-pull gated). See `editor_pegboard/MAP.md`.

#### editor_schematic/

Schematic drag handlers (locked top-down plane, no gizmo, auto-reroute on move). See `editor_schematic/MAP.md`.

This package is the "drag/rotate interaction rebuilt as object-driven handler classes, not canvas isinstance checks" effort described in MEMORY.md (2026-08-17): `CanvasBase` declares the contract (`_drag_handler: DragHandlerBase`, `_rotation_handler: RotationHandlerBase`, `gl/canvas_base/canvas_base.py:342-343`), replacing the old `gl/canvas_3d/mouse_handler.py`+`rotation_rings.py`+`move_arrows.py`+`dragging/` combo (confirmed dead — never constructed). MEMORY.md is explicit: do not propose wiring up or fixing the old `gl/canvas_3d/mouse_handler.py`, `key_handler.py`, `rotation_rings.py` (the OLD one, pre-dating this package), `move_arrows.py` (the old `gl/canvas_3d/` one, not this package's `drag_handlers/move_arrows.py`), or the `dragging/` submodules (`canvas_3d/dragging/`, `canvas_schematic/dragging/`, `canvas_base/dragging/`) — the user is rebuilding this area personally via `drag_handlers/` and will revisit each old call site himself. When decoupling a canvas file from these old modules, remove only the *import* statements; leave the old files' internals and all downstream call-site code exactly as-is (even if it now dangles/NameErrors) as a marker for the rewrite.
