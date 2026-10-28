## FILES

#### __init__.py

`DragHandlerPegboard(DragHandlerBase)` — the OLDER length-budget clamp mechanics (`_clamp_to_edge`/`_apply_local_clamp`): never stretches an attached wire/bundle segment past its real remaining length, and never pulls whatever's at the other end along with it (a purely local, independent clamp). Budgets come from the dragged object's own `BaseVar.touching_budgets`. Superseded for most object types by the rope-pull solver (see `generic.py`), but `bundle.py` still uses it directly. The camera here is a locked top-down orthographic projection, so a screen position maps unambiguously to world X/Z with no depth ambiguity — unlike the 3D editor, peg-board dragging never shows a directional-arrows gizmo and is never axis-locked. Two separate clamp mechanisms deliberately coexist in this package: this OLDER per-edge length-budget clamp and the NEWER rope-pull cascade solver (`handlers.rope_pull_handler`, used by `generic.py`) — don't assume one has fully replaced the other; check which base class a given handler actually inherits from.

#### bundle.py

`Bundle(DragHandlerPegboard)` — segment drag for the rendered strand between two chain nodes (waypoints/ends are covered by `generic.py`). Both bounding nodes move rigidly by the same delta; the most restrictive scale factor across both points' budgets is found first (`_max_scale_within_budget`) so the segment moves as one true rigid unit, not independently clamped per point. Kept as a self-contained copy, deliberately NOT reusing `wire.py`'s `Wire` — `PJTBundle.part` is a `BundleCover`, not a wire part, so `SnapProbeSet`'s AWG/crimp-range checks don't apply, and a bundle never has a genuinely free/unattached true end.

#### generic.py

`Generic(DragHandlerPegboard)` — locked-X/Z drag for transitions, housings, wire layouts, bundle layouts, and free terminals. Movement is gated by `handlers.rope_pull_handler.resolve_rigid_move` (the rope-pull cascade solver), NOT the older per-edge clamp — this handler bypasses `DragHandlerPegboard`'s own clamp entirely. Caches every real peg-board point this drag could ever move at its position when the drag BEGAN (re-deriving "current" position every frame was exactly what caused a dragged object to get stuck — a confirmed fix for a live "stuck transition" bug report, 2026-10-01: re-deriving a candidate fraction from a previous frame's possibly-clamped result is what caused the stuck state; always measure from the drag's own fixed start). For a Transition, every branch's own point is cached and moved by the exact same rigid delta the center does.

#### wire.py

`Wire(DragHandlerPegboard, WireDragMixin)` — segment-local drag; thin view-specific shell around `handlers.wire_drag_base.WireDragMixin`, shared with the 3D editor's own drag handler. **Known gap (2026-09-13, narrowed), not a bug to "just fix" without checking:** finalizing a live in-drag snap onto a TERMINAL or SPLICE on mouse-up does not yet work here (only a snap onto another wire's dangling end does) — `Terminal.add_wire`/`Splice.add_wire` and `commit_snap`'s splice branch remain 3D/2D-only. The live teleport-onto-a-probe during the drag itself already works for every snap kind. `handlers/wire_drag_base.py`'s own module docstring documents this as the authoritative source.

⚠ A click anywhere on a wire's body here only ever has as many distinct grab-points as the wire has its OWN peg-board interior waypoints (`waypoints_pegboard`) — a wire with 3D-side bends but none in peg-board has exactly one "segment" (true start to true stop), so every click drags a true end (or nothing, if both ends are anchored), never a true middle. See `handlers/MAP.md`'s `wire_drag_base.py` entry for the full explanation and the fix (`Add Handle` in this view).

#### wire_route.py

`WireRoute(Wire, WireRouteMixin)` — peg-board mirror of `editor_3d.wire_route.WireRoute`; same `BUNDLE_PLACEMENT.md` section 12 mechanism, subclassing this view's own `Wire` instead of the 3D one. Inherits the grab-point limitation from `wire.py` above directly: section 12's own eligibility rule additionally requires the grabbed pair to be two of THIS view's own real interior waypoints, never the true start/stop — so a wire needs at least 2 peg-board-side "Add Handle" waypoints before any peg-board drag-into-a-bundle is possible at all, regardless of how many 3D waypoints it already has.

#### wire_snap.py

`SnapProbeSet(handlers.snap_probe_set.SnapProbeSet)` — the peg-board-view concrete subclass (builds probes at `*_position_pegboard`).
