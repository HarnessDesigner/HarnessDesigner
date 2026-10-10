# harness_designer/rotation_handlers/rotation_rings.py

## Line 91-135 (`RotationRings.__init__`) — builds the view-specific gizmo per editor
Creates one gizmo object for the editor that is active (3D, peg-board or schematic). Runs when the rotation gizmo is opened, not per frame.

## Line 165-185 (lock on open) — one lock check when the rings open
Locks the selected object's angle when the rings open (if it is not already locked), and records the angle so it can be restored if nothing changes. The check uses the base object's lock members (see `objects/object_base.md`), so any selectable object answers it.

**Probe removed (fixed in this pass):** the three `hasattr` checks are now one `if not selected.is_angle_locked:`. `ObjectBase` gained default lock members (`is_angle_locked` returns `False`; `lock_angle` and `unlock_angle` are no-ops), and the note classes override them. Before this change, only note objects took the lock path.

## Line 205-250 (`delete`, `close`) — teardown on every close path
Restores the angle lock if the session ended without a change, and releases the gizmo. Runs once per session.

## Line 260-300 (`set_selected`, `is_selected`, `set_treeitem`, `get_treeitem`) — selection and tree wiring
Plain accessors. Cheap.

**Typing (fixed in this pass):** `set_treeitem` takes a tree item; `set_selected` takes a `bool`.
