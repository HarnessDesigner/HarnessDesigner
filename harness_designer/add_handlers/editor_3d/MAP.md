## FILES

#### __init__.py

Package docstring only; no code. Notes this is the 3D-editor add-placement package — one module per object type that can be placed in this view (see `objects.objects_3d.<type>.<Type>.start_add` for each type's own classmethod entry point); every object type supports placement here, unlike the schematic/pegboard views, which only support a subset.

#### bundle.py

`Bundle` — skeleton-first placement (`BUNDLE_PLACEMENT.md` section 3): phase 0 places the start (free, or snapped to a free transition branch); phase 1 grows the stop one waypoint at a time, ending on a fitting free branch or free space. Tracks a narrowing `(diameter_lo, diameter_hi)` range as branches attach; seeds the peg-board position once, at the end of a successful placement (`_seed_pegboard`). Module-level `drop_joint_layout` creates a `BundleLayout` marker exactly on a branch's shared joint point.

#### bundle_layout.py

`BundleLayout` — interactive waypoint placement, started only from a bundle's own "Add Handle" context-menu action, pinned to that one bundle for the whole session (no toolbar mode, so no "which bundle" ambiguity).

#### cover.py

`Cover` — housing-snapping single-slot placement, same shape as `cpa_lock.py`/`tpa_lock.py`.

#### cpa_lock.py

`CPALock` — housing-snapping single-slot placement, same shape as `cover.py`/`tpa_lock.py`.

#### housing.py

`Housing` — single-click placement, floats freely (no attach targets/snapping), locks in on the first non-drag click. Finalizes the housing's peg-board position **before** `update_cavities()` runs, since that call reads the housing's current peg-board position to compute each cavity's own — doing it in the other order used to create every cavity against a stale pre-placement position (fixed 2026-09-07).

#### note.py

`Note` — single-click placement, same free-floating shape as `housing.py`, plus a highlight material shown while placing.

#### seal.py

`Seal` — category-driven placement (SWS/MAT/PLUG/ACC, decided by the picked part's own category once known, not a pre-chosen flag): a housing+PLUG snaps to empty cavities; housing+SWS snaps to seated terminals (even an ill-fitting one, just flagged with a distinct highlight color); housing+other category is instant (pre-defined seal slot); terminal-only or cavity-only are each instant; "nothing given" is free project-wide placement. Also holds `cavity_midpoint`/`cavity_midpoint_pegboard`/`cavity_plug_search_params` module-level helpers. Every mode still arms a session and waits for a confirming click; only the housing-interactive and free modes actually move the preview during hover.

#### splice.py

`Splice` — wire-snapping placement; the preview splice is deleted and recreated every time the wire it's snapped to changes (bookkeeping has to move `self.target`/`canvas.active_handler_obj` to the new facade instance each time).

#### terminal.py

`Terminal` — cavity-snapping placement. Only Modes 2 ("housing given, snap to its own empty cavities") and 3 ("nothing given, snap to any compatible cavity project-wide") ever need an interactive session; Mode 1 (housing AND cavity both given) finalizes synchronously inside `start_add` and never arms this handler — don't assume every `start_add` call produces a live handler instance. Male/female positioning geometry stays in `handlers.terminal_handler`, imported not duplicated.

#### tpa_lock.py

`TPALock` — housing-snapping single-slot placement, same shape as `cover.py`/`cpa_lock.py`, additionally having to pick whichever of a housing's two independent `tpa_lock1`/`tpa_lock2` slots is still open.

#### transition.py

`Transition` — free placement (follows the mouse, commits with every branch left free) or snapped to a bundle's free end (found via `handlers.transition_handler._find_free_bundle_end`, an endpoint only, never mid-span; hovering a branch highlights it green/orange by diameter fit via a real ray-sphere test). Rewritten 2026-09-27 per `BUNDLE_PLACEMENT.md` section 4, replacing a bundle-snap-only implementation that in fact crashed the moment it actually found a bundle (called `utils.get_closest_point_on_wire_endpoint`, a function that never existed anywhere in this codebase) — worth remembering as a caution that "it imports cleanly" is not evidence a code path was ever actually exercised. No wire assignment/concentric rows are ever created here any more.

#### wire.py

`Wire` — two-click interactive placement (phase 0 = start point, phase 1 = stop point, growing one section at a time), snap probes (ambient "capable" highlight on every valid attach point for the whole session + "engaged" highlight on whichever is under the cursor), waypoint commit/cancel/finalize, extension mode (continuing an existing wire's dangling end). Ported from `handlers.wire_handler.AddWireHandler`; one real behavior change — a free-space start now has a real preview wire from the moment placement begins (used to create nothing until the first click).

#### wire_layout.py

`WireLayout` — wire's own waypoint-placement counterpart of `bundle_layout.py`, started from a wire's "Add Handle" context-menu action.

#### wire_service_loop.py

`WireServiceLoop` — fixed-wire service-loop placement, started only from a wire segment's own context menu; the wire is cut live the moment the session starts (before this class even exists), so unlike Splice/Bundle/Transition there is no placeholder-preview phase. Also holds `SplitState`, `wire_segments`, `split_wire_for_loop`, `restore_wire_from_split`. **Cancelling a placement (2026-10-26):** `split_wire_for_loop` cuts the wire into `state.wire2` (BEFORE the loop: the original start to the loop's STOP point) and `state.wire1` (AFTER it: the loop's START point to the original stop); `restore_wire_from_split` deletes the two cut markers and merges them with `handlers.wire_topology.merge_wires_in_place(state.wire2, state.wire1)`, which deletes `wire1` and leaves `wire2` as the whole wire. `_teardown_preview` runs that BEFORE the preview loop's own `delete()`, on purpose: `WireServiceLoop.delete()` merges the two wires it still has either side of it, so with the old order (loop first) the same two wires were merged twice. After the restore the loop has lost `wire1` from its siblings (`Wire.delete` calls `remove_wire`), so its `delete()` merges nothing.
