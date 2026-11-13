## FILES

#### __init__.py

Package marker for `wire_routing/`; no logic of its own. The package provides orthogonal
(H/V-only) auto-routing for the 2D schematic editor's wires — moved out of
`objects/objects_schematic/` on 2026-09-16 into its own top-level package. It answers "give me an
orthogonal path between these two points" (single wire or a whole drag-frame batch) and owns the
stateful reconciliation of a wire's persisted waypoints against a freshly computed route. Bundles'
placement and cross-view reaction rules live in `BUNDLE_PLACEMENT.md` (repo root), and broader
bundle design in `BUNDLE_DESIGN.md` — read both in full before touching anything here that
interacts with bundle wires specifically, rather than assuming this package's per-wire routing
model covers bundle-level behavior.

#### astar.cp311-win_amd64.pyd

The compiled (Cython) build artifact for `astar.pyx`, built in place from source and gitignored. If
missing, `routing.py` falls back to its pure-Python `_astar_py` reference silently, with no visible
indicator at runtime of which path is active besides checking whether this file exists.
`astar.pyx` was found missing from `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS` the whole
time it existed (found 2026-09-30) — a from-scratch wheel build never compiled it from source at
all, only ever picking up a pre-built `.pyd` if one happened to already be in the tree, which a
clean checkout never has. Now fixed: both this and `rope_pull/rope_pull.pyx` are listed in
`_HAND_WRITTEN_EXTENSIONS` (confirmed present as of this writing).

#### astar.pyi

Type stub for the compiled `astar` extension module, giving `routing.py` static types for
`build_tables()`/`astar()`/`Router` without needing the `.pyx` source parsed.

#### astar.pyx

The compiled (Cython) hot loop behind `routing.py`, built in place to `astar.<abi>.pyd`
(gitignored). Holds `build_tables()` + `astar()` (a one-off grid for a single `route()` call) and
`Router`, the shared grid for one drag frame (obstacle/lane counts painted in and out,
generation-stamped search buffers) that `RoutingFrame` drives. All math is in scaled-integer
coordinates, not floats, for Cython-friendly typing. **Type hints on this module's hot paths are
load-bearing for Cython, not just style** — the whole codebase compiles to C extensions via Cython
for release builds, and every `@property` return type, `__iter__` yield type, and `__getitem__`
return type must name the most specific concrete class, not a base/abstract type or a
`TypeVar`/`Generic`; a weakened hint makes Cython fall back to Python object boxing and silently
lose the performance this package exists for (`TYPE_CHECKING`-only imports are fine, since Cython
ignores them at compile time — it's runtime annotations on the hot path that must stay concrete).
If a new `.pyx` is ever added to this package, it must be added to `_HAND_WRITTEN_EXTENSIONS`
explicitly — auto-discovery does not pick up hand-written Cython extensions (see
`astar.cp311-win_amd64.pyd`'s entry above for the bug history). `routing.py`'s pure-Python
`_astar_py` fallback and this compiled path must be kept in behavioral lockstep — a fix to the
search logic in one needs the equivalent fix in the other.

#### reroute.py

The stateful orchestration layer built on top of `routing.py`'s pure pathfinding. `reroute_wire()`

**Shield ring (2026-11-12, user's design):** the wires of a cable that has a sleeve are routed THROUGH the sleeve's shield ring (`shield_ring.py`, see its docstring). `route_shield_group(project, cable)` places each ring (`shield_ring.auto_place`: the closest place beyond the terminals' stubs where it circles all of the cable's wires and nothing else is in its box, one lane spacing further out at a time; a `ring_hard` ring is left) The ring's connected end is on the line of the shield pin's exit stub when that pin is beside the cable's wires (all on one side, same exit direction), so the shield wire runs straight out of its pin and meets the ring without a turn; the end is never nearer to the nearest wire than one lane spacing and the ring is just long enough to circle the wires (`_pigtail_exit`); the ring's length is one lane spacing per wire (`wires_length`: N wires side by side = N pitches, the pitch being 3 wire diameters, `Config.layout.wire_spacing`, when no font metrics are known, else the cavity height; user 2026-11-12), at least `MIN_HALF_LENGTH` (1 pitch) as a semi-long axis, routes every drawn conductor shortest first and then the shield wires (pigtails) to the ring's connected end, and returns `False` when a ring that had a place found none. `reroute_wire` routes a shield wire in LEGS (`shield_ring.ordered_gates`: up to the near side of the ring, straight through it, on from the far side, each leg with the crossing as a lane of its own); `routing._obstacle_excludes` leaves the cable's own ring out of its wires' obstacles (`shield_ring.excluded_for`), every other wire sees the ring's box as an obstacle. Hooks: `on_wire_attached` (a conductor), `_show_attached_shield_sleeve` (the pigtail), `Cable.add_shield_sleeve`, the housing drag (`drag_handlers/editor_schematic/generic.py`: the cable's wires are not followed but routed as a group first, and the drag is REFUSED for that frame when a ring finds no place) and the housing rotation. NOT done: the refusal for a rotation or a wire attach; a manual drag of one shield wire is not special-cased (the group is routed through the ring again, the ring is the way to move them). Stand-in tests `twist/shield_ring_test.py`, `ring_legs_test.py`, `shield_group_test.py`, `sleeve_schematic_test.py`; the router's real result is NOT seen in the app.

**The wires of a shielded cable are routed FIRST again (user, 2026-11-12; for a while it was LAST, which was dropped): the group is routed before every other wire (housing drag, rotation, `auto_arrange`: `reroute.route_shield_group` per cable, `reroute.shield_cables(wires)` lists them) so the ring and the cable's wires claim their place close to the housing and the rest route around them. The wires that are not the cable's but leave the housing BETWEEN the ring's ends get out because the ring is pushed away from the housing: `shield_ring.foreign_pins` counts the pins on the ring's span (one per pin, in the order they are displayed, not the cable's) and `auto_place` pushes the ring out one pitch for each (the minimum push away distance), on top of the stub, margin and the search for a free place. `route_shield_group(project, cable)` routes the drawn conductors of such a cable as ONE batch (shortest first, through one `build_frame`), then the shield wires; `on_wire_attached` calls it whenever a conductor of such a cable is attached, and `Cable.add_shield_sleeve` when a sleeve is added. `is_shield_group_wire(wire)` = a drawn conductor (`ConductorRun`) of a cable that has a solder sleeve on either end. Stand-in test `twist/shield_group_test.py`; the router's actual result is NOT seen in the app.
is the single choke point that reconciles a wire's persisted waypoint DB rows against a fresh
route — moving what it can reuse, only inserting/deleting the difference, rather than replacing
the whole waypoint list every time. `on_wire_attached()` is the cross-editor "wire just became
fully connected" hook; `_terminal_exit_stub_point()` computes the mandatory
straight-exit-off-a-terminal stub every wire must have before orthogonal routing takes over;
`wires_attached_to()`/`sweep_for_overlaps()` are drag-time helpers (finding every wire attached to
a moving object, and sweeping for newly-introduced overlaps after a move); and
`follow_moved()`, `shift_targets()`/`apply_shifts()`, `add_waypoint()`/`remove_waypoint()`/
`set_waypoints()` are the waypoint-list mutation primitives `reroute_wire()` and drag handlers
build on. **Cable conductors (step 8, 2026-11-06):** `on_wire_attached` hands a cable LEAD to its conductor (`conductor_node.refresh_schematic(True)`) and returns: a lead is never drawn in the schematic, the conductor is (`objects/cable_conductor.py` `ConductorRun`, which quacks like a wire for this module). `wires_attached_to` goes through `_schematic_wires`: a lead is replaced, once, by its conductor's run when that is drawn, and left out when it is not, so a moved housing or terminal reroutes the conductor. `sweep_for_overlaps` and the router read `project.schematic_wires` (wires plus drawn conductor runs).

#### routing.py

The A* pathfinder itself. `route()` is the single entry point for one wire's path — obstacle
(housing/splice/note) avoidance, wire-to-wire spacing, returning a list of `(x, z)` waypoints.
`RoutingFrame`/`build_frame()` build one shared grid for a *whole batch* of wires (everything
attached to a dragged object) once per drag frame instead of once per wire — the
performance-critical path for dragging a housing with many wires attached. Route packing
(`RoutingFrame._pack` / the A* cost function) marks sibling runs — wires that followed the dragged
housing, plus each batch wire as it settles — via `paint_pack`-style tagging, and a step not
exactly one lane-spacing beside one of those costs an extra 1/16 of its own length, which is what
makes a re-routed wire hug its bundle where it can rather than taking an equally-short but
visually scattered path (see `harness_designer/ui/concentric_section/MAP.md` DESIGN NOTES's "Wire bundle packing requirements" entry — concentric
bundle packing itself is a separate, not-yet-built solver; this is just the schematic router's own
lane-hugging heuristic). `free_segment_blocked()` checks whether a hand-placed segment at any
angle (not grid-constrained like `route()`) cuts through a housing/splice/note or runs parallel
over another wire — this is what the schematic add-wire handler
(`add_handlers/editor_schematic/wire.py`) checks on every click while a user manually places
waypoints. `_astar`/`_astar_py` are the actual search loop in two forms: `_astar` is the name the
compiled `astar.pyx` module replaces at import time, and `_astar_py` is the pure-Python reference
`route()` falls back to if the compiled extension isn't present — the two must be kept in
behavioral lockstep (see `astar.pyx`'s entry above).

#### shield_ring.py

NEW 2026-11-12. The shield ring of a solder sleeve in the schematic: its stored state (`ring_from` / `ring_of` / `ring_rect`, the 1:3 long:short ratio), the automatic placement (`auto_place`), the places where a conductor crosses the ring (`gates` / `ordered_gates`), the router's exclusion of the cable's own ring (`excluded_for`) and the user's operations (`move_ring`, `resize_ring`, `refresh`). Read its module docstring and the `reroute.py` entry above; the sleeve's schematic view is `objects/objects_schematic/splice.py`.
