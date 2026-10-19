## FILES

#### __init__.py

The single public entry point, `solve_chain()` — prefers the compiled extension (`from . import
rope_pull as _rope_pull_ext`) when built, falls back to the pure-Python reference
(`rope_pull_py.solve_chain`) otherwise. Same import-and-fall-back pattern `wire_routing/routing.py`
uses for `astar`. The package as a whole is the peg-board rope-pull solver: it keeps a WIRE's or a
BUNDLE's peg-board polyline length identical to its real 3D length while it's being dragged on the
peg board (see `BUNDLE_PLACEMENT.md` section 6b, repo root). Pure numeric geometry, no DB/objects
dependency — works unchanged for either chain type, since a `PJTWire`/`PJTBundle` row exposes the
same anchor/length shape (per `objects_pegboard.chain_edges`'s own docstring). Compiled and
verified 2026-09-30 (2000 randomized cases, exact agreement between the pure-Python reference and
the compiled extension); as of that date not yet wired into any drag handler — don't assume a live
caller exists anywhere in the drag-interaction code without checking `dep_trace.py --imported-by`
first.

#### offline_store.py

A small free-function store keyed by `chain_id: bytes` —
`for_chain`/`push`/`pop_front`/`overlay`/`set_overlay`/`overlay_chain_ids`/`overlay_points`/
`release`/`release_overlay`. **Not documented in CODEBASE_MAP.md's "Other subsystems" section as
of this writing** — likely added after that section was last written, or in anticipation of the
"not yet wired into any drag handler" integration work. Reads as a per-chain scratch/undo-style
buffer for drag-in-progress state (an "overlay" of pending points per chain, released once
committed or discarded), separate from `solve_chain`'s own stateless recompute-every-call design,
but treat that purpose as inferred from its function signatures, not confirmed design intent — no
callers were found wired up as of the rope-pull feature's last documented state. Confirm actual
call sites with `dep_trace.py --imported-by` before relying on this description, and flag this gap
when CODEBASE_MAP.md is next updated.

#### rope_pull.cp311-win_amd64.pyd

The compiled build artifact for `rope_pull.pyx`, gitignored like `wire_routing/`'s equivalent.
Must stay registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS` — `wire_routing/
astar.pyx` was found missing from that list on 2026-09-30 (a from-scratch wheel build silently
never compiled it), and `rope_pull.pyx` was added to the list the same day as a direct consequence
of that finding; it is not auto-discovered. If this package's build ever stops producing this
file, check that list first.

#### rope_pull.pyi

Type stub for the compiled `rope_pull` extension, giving callers static types for `solve_chain()`
without parsing the `.pyx` source — note the stub's `drag_end` is a plain `int`, matching the
`.pyx` implementation rather than the `DragEnd` enum used in `rope_pull_py.py`.

#### rope_pull.pyx

The compiled hot path, a **line-for-line port** of `rope_pull_py.py` with one deliberate
difference: `drag_end` is a plain `int` instead of the `DragEnd` enum, with no Python-level objects
at this call boundary at all. **Type hints here are load-bearing for Cython, not just style** — the
whole codebase compiles to C extensions via Cython for release builds, and weakening a type hint
(generalizing to a base class, swapping in a `TypeVar`/`Generic`, or dropping a `@property` return
annotation) makes Cython fall back to Python object boxing and silently lose the performance this
split exists for; the plain `int` for `drag_end` is exactly this kind of deliberate, concrete-type
choice at the Python/Cython boundary, not an inconsistency to "fix" by taking `DragEnd` for
symmetry with `rope_pull_py.py`. Any fix to the solve logic must be made in both files, and the
2000-case randomized cross-check (2026-09-30) is the way to re-verify they still agree after either
changes. Registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS` (confirmed present as
of this writing) so a from-scratch wheel build always compiles it from source.

#### rope_pull_py.py

The pure-Python reference implementation. `solve_chain(start, stop, required_length, drag_end,
target, diameter_mm, zigzag_length_factor, threshold_factor, tolerance=1e-06) -> ChainResult`:
given the chain's two peg-board anchors, the required total length, which point is being dragged
(`DragEnd`: `START`/`STOP`/`WAYPOINT`) and its target, returns the WHOLE new chain. Stateless —
recomputes every interior waypoint from scratch on every call, never reads the old ones — or
refuses outright if even the bare anchor-to-anchor skeleton already needs more length than is
available. Slack beyond the bare skeleton is split across its segment(s) proportional to their own
straight length, then laid out per segment as independent diamond-shaped bumps; the closed-form bow
count/height math is used, and `count == 1` matches `geometry.line.Line.bow_midpoint`'s own
construction exactly — if either changes, check the other. `DragEnd(enum.Enum)` and
`ChainResult(NamedTuple)` are the two public value types `__init__.py` re-exports;
`_polyline_length`/`_solve_span` are internal helpers (total length of a point list; per-segment
bow-layout solve).
