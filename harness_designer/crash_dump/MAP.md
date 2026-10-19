## FILES

#### __init__.py

Public API surface: re-exports `Attr`, `dump_property` (schema.py), `capturable`, `capture_groups_for`,
`CaptureGroup` (registry.py), `iter_render_children` (render.py), `dumps_for_script_embed`,
`HtmlDumpWriter` (writer/), `walk`, `dump_to_html` (walker.py), and the three app-facing entry points
`dump_state_on_fatal_exception`, `dump_render_failure`, `dump_visible_objects` (entrypoints.py). This package
is schema-driven, severity-gated capture of application object state for render-failure and fatal-crash
dumps — the evidence behind `%APPDATA%\HarnessDesigner\log\render_failure_<Class>_*.html` and
`manual_dump_Canvas_*.html` files; see repo-root `MEMORY.md` "Reading a live run's evidence" for how to
actually read one (each `.html` embeds one JSON object per line in a `<script type="application/json"
id="dump-data">` block — parse that, not the rendered page; a dump shows LIVE in-memory state, not
necessarily what's saved to the project DB).

#### entrypoints.py

The public, app-facing entry points. `run.py`'s fatal-exception hook and `canvas_base.py`'s per-object
render-failure handler call straight into `dump_state_on_fatal_exception`/`dump_render_failure` — the same
two names the old, single-file `crash_dump.py` module exposed before this was promoted to a package, so
neither call site needed to change. `dump_visible_objects` is a third, newer entry point: a deliberate,
user-triggered (Ctrl+Shift+D) snapshot of whatever a canvas actually drew last frame, rather than something
tied to an error at all. All three are deliberately exception-safe themselves, independent of whatever the
call site does — a broken diagnostic must never mask, or worse propagate past, the real error it was trying
to describe; that matters most for the fatal path, which runs moments before the process aborts outright.
`dump_render_failure` is rate-limited per `id(view_obj)` (30 s cooldown) since a render failure can repeat
every frame once something is persistently broken about one object. Every dump runs inside the current
project's write-suppressing `gesture()` if one is open, since some lazily-created-on-read columns (e.g.
`PJTSplice.branch_position3d_id`) insert a database row as a side effect of a plain attribute read — a
passive diagnostic must never trigger that for real.

#### registry.py

`@capturable(severity=None)` — a class decorator declaring which attributes/properties (via `Attr`/
`@dump_property`-tagged properties, see `schema.py`) a crash dump may read from instances of that class, and
at what severity. All cascade/override/merge work (inherited capture groups from already-decorated
ancestors, deduplicated by source class for multiple inheritance, with a subclass's own entries overriding
same-named inherited ones) happens once, at decoration time, so `capture_groups_for(cls)` at dump time is a
single MRO walk with no merge work left to do. `@capturable` never mutates the class it decorates — classes
in this app are Cython-compiled (pure-Python mode) — and every `cls`/`source_class` parameter is annotated
`object`, not `type`, on purpose: Cython's pure-Python-mode `ArgTypeTest` for a bare builtin `type`
annotation rejects any *subclass* of `type` (e.g. a custom metaclass like `PointMeta`), so annotating `type`
here would crash a compiled build at import time for any app class with a nonstandard metaclass. Capture
groups are treated as immutable and shared by reference across descendants that inherit them unchanged.

#### render.py

Per-type rendering: how to label/format a captured value and what counts as its children, consulted only
*after* the capture-schema registry has already decided a value is NOT itself a walkable, schema'd app
object (those stay `$ref`s, handled entirely by `walker.py`). Dispatch is a single `functools.singledispatch`
function, `iter_render_children`, with two tiers: true builtins (`dict`/`list`/`tuple`/`set`/`frozenset`)
and app-authored custom types are registered directly (zero import cost for builtins); optional stdlib/
third-party "extras" (`decimal.Decimal`, `uuid.UUID`, `datetime.datetime`/`date`, `numpy.ndarray`) are
resolved lazily by a `f'{module}.{qualname}'` string key against `extras/` submodules, so importing
`crash_dump` never forces importing a module the host app doesn't otherwise use. A renderer returns
`('value', json_safe_scalar)` (terminal), `('children', [(name, child_value), ...])` (recurse — each child
is fed back through the walker's own classification, so a child that's itself a walkable app object still
becomes a `ref` rather than being inlined here), or `None` (type not covered; the caller omits it entirely).

#### schema.py

The per-class capture-list vocabulary: `Attr(name, severity)` — one capturable attribute/property name and
the dump severity it requires. `dump_property(severity)` — a decorator for a `@property`'s plain getter
function (must be stacked *below* `@property`, closer to `def`, since a `property` object itself has no
`__dict__` to stash the tag on); marks it capturable at the given severity for `registry.py`'s
`@capturable` to pick up.

#### walker.py

Walks an object graph from one or more roots (breadth-first over an explicit queue, not recursion, so a
cycle or a shared object reached from two places is handled the same way: once an id has been seen, every
further encounter just emits a `ref`, never re-queued or re-walked), producing one node dict per captured
object for the writer to serialize. A node's own id is just `id(obj)` — stable only for the lifetime of a
single walk, exactly the lifetime a `$ref` needs. Only attributes/properties covered by a passing capture
group (per `registry.capture_groups_for`) are ever read — nothing here falls back to `repr()` for a type
with no schema and no registered renderer; it's simply omitted. Container recursion is bounded
(`_MAX_CONTAINER_DEPTH = 4`, `_MAX_CONTAINER_ITEMS = 50`) since dedup only matters for the app's own shared
objects, not incidental small containers. `walk(roots, *, trigger_severity)` is the generator; `dump_to_html
(roots, *, trigger_severity, dump_kind, path, exception=None)` wraps it with an `HtmlDumpWriter` and writes
the meta record (dump kind, severity, timestamp, root ids, optional exception) first.

## FOLDERS

#### extras/

Lazily-imported rendering support for optional stdlib/third-party types (`decimal.Decimal`, `uuid.UUID`,
`datetime.datetime`/`date`, `numpy.ndarray`) consulted only by `render.py`'s `iter_render_children`. See
`extras/MAP.md`.

#### writer/

Streaming output: NDJSON record serialization plus the self-contained HTML dump file (static shell + a
small vanilla-JS tree viewer) that embeds it. See `writer/MAP.md`.
