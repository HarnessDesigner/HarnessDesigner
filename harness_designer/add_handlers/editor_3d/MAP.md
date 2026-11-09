## FILES

#### __init__.py

Package docstring only; no code. Notes this is the 3D-editor add-placement package — one module per object type that can be placed in this view (see `objects.objects_3d.<type>.<Type>.start_add` for each type's own classmethod entry point); every object type supports placement here, unlike the schematic/pegboard views, which only support a subset.

#### bundle.py

`Bundle` — skeleton-first placement (`BUNDLE_PLACEMENT.md` section 3): phase 0 places the start (free, or snapped to a free transition branch); phase 1 grows the stop one waypoint at a time, ending on a fitting free branch or free space. Tracks a narrowing `(diameter_lo, diameter_hi)` range as branches attach; seeds the peg-board position once, at the end of a successful placement (`_seed_pegboard`). Module-level `drop_joint_layout` creates a `BundleLayout` marker exactly on a branch's shared joint point.

#### bundle_layout.py

`BundleLayout` — interactive waypoint placement, started only from a bundle's own "Add Layout" context-menu action, pinned to that one bundle for the whole session (no toolbar mode, so no "which bundle" ambiguity).

**Preview (2026-11-08):** as `wire_layout.py`: a sphere 1.25 times the bundle's diameter riding on the drawn (rounded) path, the waypoint committed on the straight path, the sphere removed on the click.

#### cable.py

`Cable(wire.Wire)` (NEW 2026-11-05): the placement session of a cable, a subclass of the wire's session with everything that attaches taken out (no snap probes, no hover highlights, no terminal / splice / layout / wire picks, no circuit). First click sets the start, each further click commits a waypoint, right click ends the cable at the last waypoint: `finalize_at_last_point` then makes the conductors (`PJTCableConductorsTable.insert_for_cable`, from the FINAL end points, because each conductor's end points are children of the cable's and the cable's end point is replaced at every waypoint commit) and adds the cable to the project. Its route goes in `pjt_cable_paths` through the wire session's new `_paths_table` hook. A cable with no outer jacket (`CableStyle.TWISTED` or `RIBBON`) gets NO `WireLayout` at its waypoints (user, 2026-11-05): the wire session's new `_waypoints_get_layouts` hook, which this class answers from the part's `cable_style`. **Not run in the app.** When the placement ends it also SEEDS the cable onto the peg board (`cable.objpegboard.seed_from_3d()`, before the cable joins the project and its conductors are drawn), as a bundle is seeded.

**No coincident waypoints (2026-11-08):** `Cable._commit_waypoint` adds nothing when the end being placed is within `_SAME_SPOT_MM` (1 mm) of the previous point (the last waypoint, or the other end for the first one): saved cables were found with two waypoints on the same spot (and one at the very end), which read as one bend until a drag pulled them apart ('the waypoint splits in two', 'dragging an end leaves a waypoint behind'). Cables made before this still have them: **Delete Layout** removes one.

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

`Wire` — two-click interactive placement (phase 0 = start point, phase 1 = stop point, growing one section at a time), snap probes (ambient "capable" highlight on every valid attach point for the whole session + "engaged" highlight on whichever is under the cursor), waypoint commit/cancel/finalize, extension mode (continuing an existing wire's dangling end). Ported from `handlers.wire_handler.AddWireHandler`; one real behavior change — a free-space start now has a real wire from the moment placement begins (used to create nothing until the first click), but it is HIDDEN (`is_visible = False`, set in `objects_3d.wire.Wire._start_free_space` / `Cable.start_add_cable`) until the first click: the stop point sits at the origin through phase 0, so a visible wire would be drawn from the origin to the cursor. `hover` shows it once phase 1 has moved the stop to the cursor (same rule as the bundle session). The peg-board session does the same (`objects_pegboard.wire.Wire._start_free_space`, `add_handlers/editor_pegboard/wire.py` `hover`).

#### wire_layout.py

`WireLayout` — wire's own waypoint-placement counterpart of `bundle_layout.py`, started from a wire's "Add Layout" context-menu action.

**Preview (2026-11-08, `WAYPOINT_REWORK_DESIGN.md`):** the sphere is `HANDLE_SCALE` (1.25) times the wire's diameter and rides on the path AS DRAWN (the rounded corners): `hover` asks the wire for `get_closest_curve_point`, or snaps to an end as before. The waypoint itself is committed on the STRAIGHT path (`get_closest_endpoint`), so inserting one never changes the shape of the other corners; the preview can differ from it by up to a fraction of a diameter near a corner, and is removed on the click (`_previewing` False: the layout is then undrawn and is only a drag handle while its wire is selected, see `objects/mixins/waypoint_handles.py`).

**Cable (2026-11-08):** the same session places a waypoint on a CABLE (`ObjectBase.is_cable` on the target): no endpoint snapping (`_closest_endpoint`), and the click deletes the preview and calls `Cable.add_waypoint` (`_finalize_cable`) instead of making a `WireLayout`.

#### wire_service_loop.py

`WireServiceLoop` — fixed-wire service-loop placement, started only from a wire segment's own context menu; the wire is cut live the moment the session starts (before this class even exists), so unlike Splice/Bundle/Transition there is no placeholder-preview phase. Also holds `SplitState`, `wire_segments`, `split_wire_for_loop`, `restore_wire_from_split`. **Cancelling a placement (2026-10-26):** `split_wire_for_loop` cuts the wire into `state.wire2` (BEFORE the loop: the original start to the loop's STOP point) and `state.wire1` (AFTER it: the loop's START point to the original stop); `restore_wire_from_split` deletes the two cut markers and merges them with `handlers.wire_topology.merge_wires_in_place(state.wire2, state.wire1)`, which deletes `wire1` and leaves `wire2` as the whole wire. `_teardown_preview` runs that BEFORE the preview loop's own `delete()`, on purpose: `WireServiceLoop.delete()` merges the two wires it still has either side of it, so with the old order (loop first) the same two wires were merged twice. After the restore the loop has lost `wire1` from its siblings (`Wire.delete` calls `remove_wire`), so its `delete()` merges nothing.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Wire-snap two-tier highlight in 3D (built 2026-10-08, 3D only)
Spec'd over several rounds with the user (the first guess, "highlight the whole terminal", was wrong).
- **Ambient "capable" tier:** every wire-compatible terminal/splice is lit in `Config.colors.add_object.snap_capable_highlight` (dim yellow) for the whole `add_handlers.editor_3d.wire.Wire` placement session, built from `handlers.snap_probe_set.SnapProbeSet.snap_terminals`/`snap_splices` (pure data, view-agnostic) and applied/cleared by `Wire._apply_ambient_highlights`/`_clear_ambient_highlights` (called from `_ensure_snap_probes` and `_cleanup`, which every exit path funnels through).
- **"Snap engaged" tier:** a distinct colour layered on top for the one target the cursor is within probe range of (`_set_hover_obj`/`_clear_hover` via `_apply_highlight`/`_revert_highlight`); on mouse-away it reverts to the ambient colour, not off. There is no flash-on-click state: hovering into range IS the snap and a click commits it.
- **Where the colour shows:** a free-floating terminal (`cavity is None`) tints its whole mesh via `identify()`. A cavity-seated terminal is never itself visible, so `Terminal.set_snap_highlight(material)` (`objects/objects_3d/terminal.py`) stores `_snap_highlight_material`, which `render_cavity_overlay` uses to override only the WIRE-side overlay on the housing mesh (never the pin side). A splice is always a visible mesh and just uses `identify()`.
- **Compat is not filtered for free-floating terminals** (a probe always exists; compat only warns/blocks the connection), so a hard-incompatible free terminal still gets the ambient highlight. Cavity-seated terminals ARE compat-filtered before a probe or `snap_terminals` entry exists.
- **Free-end drag:** the same two tiers live entirely in the 3D-only `drag_handlers/editor_3d/wire.py` (ambient around `_arm_drag`/`_disarm_drag`; engaged via `_set_engaged_target(kind, target)` each tick, diffing against `snapped_kind`/`snapped_target` that the shared `WireDragMixin.__call__` already sets). The shared mixin was deliberately not touched (peg-board shares it and has no highlight mechanism). A `'wire'`-kind target is never highlighted. Not done: extension mode (`Wire._hover_extension`, its own `_extension_snap_*` tracking) and peg-board's free-end drag have no highlighting; peg-board would first need a `render_cavity_overlay`/`set_snap_highlight` equivalent.
