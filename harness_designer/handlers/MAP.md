## FILES

#### __init__.py

Package docstring only — explains that most of this package's former `Add*Handler` classes have been migrated onto the objects themselves (see `add_handlers/`) and removed; what remains here is view-agnostic logic those replacements (and `drag_handlers/`/`rotation_handlers/`) still call into: part-compatibility lookups, wire fork/merge, terminal/transition/seal placement geometry, snap-probe building blocks, and the peg-board rope-pull reconciliation solver. No code of its own.

#### bundle_diameter.py

The shared bundle-diameter rule (3D + peg-board) — a bundle's diameter is `max(wire-driven diameter, every attached transition branch's own min_dia)`, and growing/shrinking a branch's own project-level `diameter` to meet the bundle is symmetric (not a one-way ratchet). Wire-driven diameter uses the real concentric-packing figure when one exists, else an "unorganized packing" area-sum estimate scaled by a fudge factor. `wires_diameter(bundle)` is the read-only public form of the wire-driven diameter (mm), used by the circuit solver; unlike `effective_diameter` it never grows a transition branch.

#### bundle_layout_handler.py

Inserts a new interior `BundleLayout` waypoint into a bundle's 3D path at the clicked position/segment (`_create_bundle_layout_on_bundle`), reached only from a bundle's own "Add Handle" context-menu action.

#### bundle_topology.py

`merge_bundles` — the one bundle-topology operation that survives the waypoint model (bends are just interior waypoints, not forks): merging two independently-placed bundles dragged together end-to-end into one row, mirroring `wire_topology.merge_wires`.

#### concentric_handler.py

Which concentric a bundle / transition branch uses (2026-10-25): `find_concentric_for_bundle` / `find_concentric_for_branch` (read-only, `None` if there is none) and `concentric_for_bundle` / `concentric_for_branch` (the same, making an empty concentric when there is none). A connected bundle and branch share ONE concentric (and so one widget) by LOOKUP, never by writing ids: a bundle uses its own, else the first one among the branches plugged into either end; a branch uses its own, else its bundle's. Where BOTH already have one (made separately before they were joined) each keeps its own -- nothing merges concentrics, so that case still has two widgets. Wires in a concentric (NEW 2026-10-25): `add_wire` (the drop of a wire from a peg-board wire table onto a concentric section widget lands here), `replan`, `needs_plan` and `build_section` (the adapter from the database to `ui/concentric_section`'s `SectionSpec` + `WireDetail`). A wire is "in" a concentric when a `pjt_concentric_wires` row of one of its layers names it; a new wire goes in the OUTERMOST layer, and a concentric with no layers gets layer 0. **Layer diameters are deliberately left alone**: `bundle_diameter._wires_diameter` takes the outermost layer's `diameter` as the bundle's size the moment its concentric has any layer, so a placeholder or a made-up figure would silently resize the bundle in 3D and on the peg board; a new first layer gets the diameter the bundle has right now (its wires' estimate, else the attached branch's `diameter`, else the wire's own OD) and an existing layer's diameter is never rewritten. **`replan` is INTERIM**: it packs every cable as tightly as it can in a circle (`ui/concentric_section/packing.py`) and stores each cable's place in its `point2d`; it does not follow the MIL-STD-339 layer rules (CONCENTRIC_TWIST_DESIGN.md sections 4-8) -- when that solver exists it replaces `replan` and nothing else here changes. It also overwrites every cable's place on each add (a manual drag of a cable is not saved yet either). **Cables are drawn from what the catalog knows** (`_cable_for`): there is no jacket flag and no jacket / shield thickness, so a coaxial or shielded part gets a shield and a jacket (`_SHIELD_FRACTION` / `_JACKET_FRACTION` of its OD), any other wire none (several conductors = a twisted group); the conductor colour is the plating row's own `color`, the insulation / stripe colours the part's. The wire details (`_detail_for`) take the current and temperature from `circuit.solve()` (one solve per circuit per build) and are `None` for a wire in no circuit. Nothing checks that a dropped wire actually runs through the bundle the concentric belongs to. Checked 2026-10-25 against fake rows only (no real database): no duplicates, layer diameters untouched, no overlapping cables, the cable kinds, the details.

#### handler_base.py

`HandlerBase` (~290 lines) — captures mainframe/part_id/camera/ptables state for a handler; mouse-capture lifecycle (`capture_position()`/`release_capture()`/`ignore_next_input()`, where `release_capture` raises `NotImplementedError` so subclasses must implement placement); and orientation-alignment helpers used to snap a newly placed accessory to the face of the housing/cavity it's being dropped into: `obb_face_direction()` (outward-normal for one OBB face), `euler_from_matrix_continuous()` (YXZ Euler from a rotation matrix, unwrapped continuous with the previous angle to avoid +/-180 degree flips), `set_angle_from_housing()`/`set_angle_from_cavity()` (align an object's angle3d to a housing's/cavity's world rotation via `model3d.forward_up` face indices), and `reset_angle()` (reset angle3d to identity).

#### rope_pull_handler.py

The peg-board "rope pull" reconciliation solver (`BUNDLE_PLACEMENT.md` sections 6/6b). `resolve_rigid_move` (interactive drag of an anchor/waypoint) and `realize_length_change`/`realize_3d_move` (after a 3D length change) binary-search the largest fraction of a drag's delta every touched chain can accept, cascading through whatever rigid object (Transition, Housing, Splice, WireServiceLoop) each chain's far end is anchored to when its own slack can't absorb the move. A pulled Transition rotates about the arriving branch's own pivot rather than just translating. Waypoint count is held fixed during an in-progress drag (`_commit_points`'s `in_progress` flag) and only reconciled to its real shape once on mouse-up (`finalize_drag`), to avoid DB churn every frame.

#### seal_handler.py

Seal compatibility-lookup helpers (`is_mat_seal_type`, `terminal_seal_search_params`, `wire_seal_fit_ok`) reused by `objects.objects_3d.seal.Seal.start_add` / `add_handlers.editor_3d.seal`.

#### snap_probe_set.py

The abstract `SnapProbeSet`/`SnapProbeSetType` base for invisible sphere snap probes — reuses `objects.wire_layout.WireLayout` itself as the pickable hit-test target instead of inventing a new object type. Deliberately holds only the abstract base; the two concrete per-editor subclasses live in `drag_handlers.editor_3d.wire_snap`/`drag_handlers.editor_pegboard.wire_snap`. Never call `.delete()` on a probe's `WireLayout` wrapper — `.delete()` runs `_reconnect_wires()`, which assumes a real attached wire row; use `SnapProbeSet.close()` instead.

#### splice_handler.py

`_wire_fits` — AWG-range compatibility check for inserting a splice into a wire, reused by `objects.objects_3d.splice.Splice.start_add` / `objects.objects_schematic.splice.Splice.start_add`.

#### terminal_handler.py

Terminal-placement geometry — `_male_terminal_position`/`_female_terminal_position` (crimp-point math off a cavity's own already-correct position/angle, per the rigid-child-positioning convention: offset rotated by the parent's world angle then translated by the parent's world position, never re-derived from a grandparent), peg-board equivalents, free-end (cavity-less) positioning, `reposition_from_model` (rerun once a first-time model download completes), and part-dimension estimation.

#### transition_handler.py

Transition-placement helper functions reused by `add_handlers.editor_3d.transition`, plus `RouteThroughTransitionHandler`/`RouteThroughBundleHandler`/`RoutedWireHandler` — routed-wire-placement handlers with **no UI entry point anywhere in the app** (not part of the add-session migration); `RoutedWireHandler`'s own branch-picking (`isinstance(selected, _Branch3D)` against a plain `find_object` result) is now structurally unreachable, not just unwired, since a branch is no longer its own pickable object — left for whoever revives this handler.

#### wire_circuit.py

`reconcile_wire_circuit(project, wire)` — works out which circuit a freshly connected wire and the objects on its two ends belong to, reading the ends from `Wire.start_sibling`/`stop_sibling` (so call it only AFTER the ends are attached). No circuit among them and one end is a terminal: `Project.create_circuit()` and the first terminal (start end first) becomes the start terminal. One circuit: the wire and every circuit-less end join it via `PJTCircuit.add_member`. Two or more: a Yes/No dialog, then `Project.merge_circuits` into the start side's circuit; No leaves everything as it was. The decision is made over the WHOLE chain the wire is part of (`PJTCircuitsTable.connected_members`), not only its two ends: a circuit anywhere along it takes part in the Yes/No question, and the chosen circuit then spreads to everything connected (`PJTCircuitsTable.propagate`, via `add_member`). It never removes a member from a circuit, and a wire with only free or layout ends, or only splices, creates nothing. Idempotent. Called from the three add-wire handlers (`add_handlers/editor_3d|editor_pegboard|editor_schematic/wire.py`), `wire_snap.commit_snap` (terminal/splice snap, extension mode and endpoint drags) and `wire_drag_base.merge_wire_into` (every wire-to-wire join). Not covered: deleting a wire, terminal or splice never removes an emptied circuit, and detaching a wire end (`Terminal.detach_wires`) does not touch circuits. `reconcile_wire_circuit` now does two things after a connection: `_reconcile_circuits` (the circuit logic above) and `_replicate_operating_temp`, which spreads the operating temperature across the wire and the objects at its two ends: a part with none takes the value the others hold, and when the parts hold DIFFERENT values a Yes/No dialog asks whether to set them all to the start side's value (No leaves everything, so a harness passing a firewall can keep parts at different temperatures; it asks again on the next connection). The temperature is also carried by `wire_topology.split_wire_at_point` (both halves) and `merge_wires`, the 3D and schematic splice handlers, and the service-loop creation in `objects_3d/wire_service_loop.py`, because those create a part from an existing wire without a connection event.

#### wire_drag_base.py

`WireDragMixin` — the shared segment-local wire drag algorithm (which point(s) a click-drag moves, snap-probe teleport, AWG-mismatch warning-only behavior), used identically by `drag_handlers.editor_3d.wire.Wire` and `drag_handlers.editor_pegboard.wire.Wire`. It deliberately defines **no** `__init__`/`delete`, and only `__call__`, under an explicit-dispatch discipline rather than relying on `super()`/MRO: a mixin combined via plain multiple inheritance has its method resolution decided by base-class order, which was confirmed live (2026-09-13) to silently break — reversing `class Wire(WireDragMixin, DragHandler3D)` to the other order changed which `__init__`/`delete` ran, or dropped the mixin's setup entirely, and `DragHandlerBase.__call__`'s `NotImplementedError` silently won over the mixin's real `__call__` until each concrete `Wire` added its own explicit override. Every concrete `Wire` (`drag_handlers.editor_3d.wire.Wire`/`editor_pegboard.wire.Wire`) calls its real base (`DragHandler3D`/`DragHandlerPegboard`) by name, never `super()` — a confirmed MRO bug, not a style preference.

#### wire_handler.py

Wire-compat search-param builders (`terminal_wire_search_params`/`splice_wire_search_params`) reused by the object-owned wire add-handlers; compares the wires table's `wire_size_cross` (bare-conductor cross-section) against a terminal's/splice's crimp range, not `od_mm` (insulated OD — a different quantity).

#### wire_layout_handler.py

Inserts a new interior `WireLayout` waypoint into a wire's 3D path (`_create_wire_layout_on_wire`), mirrors `bundle_layout_handler.py`.

#### wire_routing_drag.py

The UI half of the skeleton-first wire routing engine (`BUNDLE_PLACEMENT.md` section 12): drag-start eligibility scan + two-tier highlight (`compute_eligible_targets`/`highlight_eligible`/`set_hover_highlight`), `WireRouteMixin` (mixed into `drag_handlers.editor_3d`/`editor_pegboard.wire_route.WireRoute`, alongside that view's own ordinary `wire.Wire` drag handler), and `RouteSession` (the click-driven continuation through further transitions, installed as a Wire view object's own `_active_handler`). This feature was **dead on arrival from a naming typo** (found and fixed 2026-10-08): `WireRouteMixin._is_routing_eligible` read `self._moving` (a never-written class-level placeholder, copy-paste drift from a different name) instead of `self.moving` (the real attribute `WireDragMixin._arm_drag` in `wire_drag_base.py` actually sets) — since that check started with `if self.end is not None or self._moving is None or ...: return False`, it returned `False` unconditionally, so nothing was ever highlighted and `drop_hit` was never set, for every wire drag in both views. The fix was a simple attribute-name correction (`_moving` -> `moving`, 3 reads), not a logic bug; it is still not verified running end-to-end in the live app.

#### wire_routing_handler.py

The skeleton-first wire routing engine itself: `RouteWalk` (resumable, one hop at a time) and `route_wire` (thin wrapper for an already-resolved hop list) walk bundles/transitions, computing guard/housing-breakout-point geometry, and commit to `pjt_wire_paths`. Takes a `view` arg (`'3d'`/`'pegboard'`) throughout — same skeleton topology, each view's own point columns. Every other call site here (`EnterBundle`/`EnterBranch`/`ContinueBranch`/`begin_route`/`is_bundle_end_free`/`wire_fits_bundle`/`wire_fits_branch`/`highlight_branch`/`clear_branch_highlight`/`hit_test_branch_ray`) was cross-checked against `wire_routing_drag.py`'s naming-typo fix above and found clean — all argument counts/order match, no further typos found.

#### wire_slack.py

`reconcile` — bows a single waypoint into whichever of a wire's two view-paths (3D or peg-board) is shorter, so both agree on one real `length_mm`. Runs once, right after both real endpoints are known; not a continuous solver (later peg-board dragging stays within that length via the existing per-segment length-budget clamp).

#### wire_slack_handler.py

`WireSlackHandler` — a per-wire safety net, one instance per `objects.wire.Wire` facade, binding callbacks onto every one of that wire's own points (both views) so ANY move of ANY of them re-runs `wire_slack.reconcile`, supplementing (not replacing) the explicit `rope_pull_handler.realize_length_change` call sites that can miss a case (confirmed live: a housing drag didn't enumerate a point that mattered). **`release()` (2026-10-25):** `Wire.delete` calls it, and a released handler unbinds and does nothing. Without it a deleted wire's handler lived on (facade and handler refer to each other, so only the garbage collector frees them) and, bound to the wire's points, reconciled a wire whose row was gone: adding a wire service loop (which deletes the wire it replaces, then moves a point that wire was bound to) raised `KeyError` from `table_data.select`. The `finally` in `_reconcile` also used to skip clearing `_reconciling_any` when `register_pegboard()` raised, which silently turned off every wire's reconcile for the rest of the session; it now clears the flag in an inner `finally`.

#### wire_snap.py

View-agnostic snap helpers used by both the add-session and drag flows — `SnapOverlay` (floating compat-message label), `check_terminal_compat`/`check_splice_compat`/`capacity_warning` (AWG/cross-section compatibility, non-blocking warnings), `resolve_picked`/`get_snap_info` (unwrap a snap-probe hit to the real target), and `snap_point`/`commit_snap` (finalize a connection on release). Deliberately kept separate from `snap_probe_set.py` so code that only needs these helpers never has to import the abstract probe-building machinery. The snap-COMMIT side of a drag's snap (`commit_snap`) is still 3D/2D-only for a snap onto a TERMINAL or SPLICE — `Terminal.add_wire`/`Splice.add_wire` only write `*_position3d`/`*_position2d` columns. The live in-drag teleport-onto-a-probe already works for peg-board (via `SnapProbeSet`'s peg-board subclass); only finalizing that specific case into a real connection on mouse-up does not yet.

#### wire_topology.py

`split_wire_at_point`/`merge_wires` — forking a wire in two around a real junction (splice, wire service loop) and merging two forked wires back into one when the junction is removed. Ordinary bends never go through here (see `wire_layout_handler.py`).
