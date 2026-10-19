## FILES

#### __init__.py

Package docstring only; no code. Describes `add_handlers/` as the placement-session ("Add Housing", "Add Wire", ...) analog of `drag_handlers/`/`rotation_handlers/`: per-view, per-object-type stateful handlers that drive an interactive object placement session.

#### base.py

`AddHandlerBase` — the shared construct/call/destroy lifecycle every add session uses: a concrete handler is constructed by the object's own `start_add` classmethod the moment placement begins, attached to that view instance's own `_active_handler` slot (the same slot drag/rotation handlers use), called once per mouse event for the session's duration via the shared `__call__(last_pos, current_pos, had_motion, interaction_type, clicked_object)` contract, and torn down via `delete()` once placement finishes (committed or cancelled). Unlike a drag handler's narrow `__call__(delta, mouse_pos)`, an add session is a genuine multi-step interaction (hover preview, click to commit a point, right-click to finish early, Escape to cancel outright) spanning many separate mouse gestures. Also holds `click_at()` — replays a MOVE+LEFT_UP at a given point into an already-armed session, used by the empty-space right-click "place at the click" menus (`ui/widgets/empty_space_menus.py`).

## FOLDERS

#### editor_3d/

3D-editor add-placement handlers — one module per object type, since every object type supports placement in this view (unlike the schematic/pegboard views, which only support a subset). See `editor_3d/MAP.md`.

#### editor_pegboard/

Peg-board-editor add sessions — only Housing, Wire, and waypoints-on-each are placeable here (`ui.toolbar.toolbar.VIEW_MODE_IDS`). See `editor_pegboard/MAP.md`.

#### editor_schematic/

Schematic-editor add sessions — only Housing, Splice, Terminal, and Wire are placeable here (mechanical accessories and routing/grouping types have no 2D schematic representation at all). See `editor_schematic/MAP.md`.

This whole package (together with `drag_handlers/` and `rotation_handlers/`) is essentially undocumented in the repo's top-level `CODEBASE_MAP.md` — that file documents only `handlers/` in detail, with just a passing mention of `drag_handlers.editor_3d/editor_pegboard.wire_route.WireRoute`. This set of `MAP.md` files is the first real documentation of the "drag/rotate (and add) interaction rebuilt as object-driven handler classes, not canvas isinstance checks" effort described in MEMORY.md (2026-08-17). This package replaces a whole family of `handlers.Add*Handler` classes that used to live in `handlers/` — those were migrated onto the objects themselves and removed; `handlers/` now holds only the reusable, view-agnostic logic these replacements still call into (part-compat lookups, wire fork/merge, placement geometry — see `handlers/MAP.md`). Every concrete handler here mirrors the old `handlers.*_handler.Add*Handler` it was ported from — the underlying mechanics are usually unchanged; what moved is only *how* a session gets constructed (by the object's own `start_add`, with a real target view object already built) and driven (the one shared `__call__` instead of separate `hover()`/`release_capture()`/`finalize_at_last_point()`/`cancel()` entry points the old `mainframe`-owned plumbing called directly).
