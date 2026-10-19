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
is the single choke point that reconciles a wire's persisted waypoint DB rows against a fresh
route — moving what it can reuse, only inserting/deleting the difference, rather than replacing
the whole waypoint list every time. `on_wire_attached()` is the cross-editor "wire just became
fully connected" hook; `_terminal_exit_stub_point()` computes the mandatory
straight-exit-off-a-terminal stub every wire must have before orthogonal routing takes over;
`wires_attached_to()`/`sweep_for_overlaps()` are drag-time helpers (finding every wire attached to
a moving object, and sweeping for newly-introduced overlaps after a move); and
`follow_moved()`, `shift_targets()`/`apply_shifts()`, `add_waypoint()`/`remove_waypoint()`/
`set_waypoints()` are the waypoint-list mutation primitives `reroute_wire()` and drag handlers
build on.

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
visually scattered path (see MEMORY.md's "Wire bundle packing requirements" entry — concentric
bundle packing itself is a separate, not-yet-built solver; this is just the schematic router's own
lane-hugging heuristic). `free_segment_blocked()` checks whether a hand-placed segment at any
angle (not grid-constrained like `route()`) cuts through a housing/splice/note or runs parallel
over another wire — this is what the schematic add-wire handler
(`add_handlers/editor_schematic/wire.py`) checks on every click while a user manually places
waypoints. `_astar`/`_astar_py` are the actual search loop in two forms: `_astar` is the name the
compiled `astar.pyx` module replaces at import time, and `_astar_py` is the pure-Python reference
`route()` falls back to if the compiled extension isn't present — the two must be kept in
behavioral lockstep (see `astar.pyx`'s entry above).
