# harness_designer/drag_handlers/move_arrows.py

The arrow objects are created once per axis lock. Their `_floor_guard` flag is a class-level default now (it used to be read through `getattr`), so there is no per-move reflection. Cheap.
