# Claude Memory — harness_designer

This file is the single source of truth for Claude's persistent memory about this project. It replaces the auto-memory system's per-topic files. When memory needs to change (add/update/remove a learned fact, feedback, or project note), edit **this file** directly — do not write to the separate auto-memory store.

Compiled from prior auto-memory on 2026-07-28. Entries are point-in-time observations, not live state — verify claims about code behavior against the current code before asserting them as fact, especially older entries.

---

## MANDATORY: CODEBASE_MAP.md

- **Read `CODEBASE_MAP.md` (repo root) at the start of every new session**, before exploring the tree, to get oriented on where things live.
- **Update `CODEBASE_MAP.md` any time a file is added, removed, renamed, or otherwise changed in a way that affects the map** (new module, moved file, restructured directory, etc.) — do this as part of the same change, not as a follow-up. Don't leave the map stale for the user to catch later.
- Follow the map's own "## Formatting" section (bulleted lists for readability, never compressed to prose).

---

## Reference

### Codebase map
See the MANDATORY section above for the read-at-start / update-on-change rule. The full directory/file map of the harness_designer package lives in the repo at `CODEBASE_MAP.md` (repo root) — the single source of truth, since the user also edits it directly.

Key insight: **part-type fan-out** — a part type (e.g. "seal") has parallel files in `database/global_db`, `database/project_db` (`pjt_*`), `database/create_database`, `objects/objects2d`, `objects/objects3d`, `handlers`, and `ui/editor_db`. Changing a part type usually touches all seven.

---

## User

### Naming convention: dunders
`__name__` (dunder prefix AND suffix) is a deliberate project convention meaning the instance variable or method is high-importance and must not be modified or overridden from outside the class that defines it — including from child classes.

Distinct from:
- `__name` (dunder prefix only): Python name-mangling, class-private by the interpreter
- `_name` (sunder): internal but accessible to subclasses

The dunder-both-sides form avoids name mangling (safe in mixins/inheritance chains) while signaling a stronger "hands off" contract than a sunder. It typically marks a cache or stored reference pointing to the original/canonical version of something — the live source of truth, not a derived copy. Confirmed examples: `__table__`/`__db__` (config.py), `__callbacks__`/`__unbound_callbacks__`/`__ref_count__` (CallbackMixin — point.py, angle.py, color.py), `__field_names__` (database/*/bases.py). Contrast with `_o_position3d`/`_o_angle3d`/etc in `pjt_housing.py` — those are mutable per-update diff snapshots, only single-underscore since they're not a pointer to a canonical resource.

The convention also extends to built-in dunders: `Config.__table_name__` (config.py:357-366) derives from `cls.__qualname__` (full dotted nesting path) specifically to avoid short-name collisions across nested config classes; `cls.__name__` is used only for debug logging, never as the real identifier.

**Why:** App is a PyInstaller-frozen binary pinned to a specific Python version — no conflict risk with future Python dunder reservations. This two-tier convention is also the intended public-surface boundary for the commercial plugin architecture (see Project section below): `import harness_designer` gives a plugin full access with no separate internal/public API split. `_name` = "internal, plugin author touching it is on them." `__name__` = "truly hands off," for internal subclasses AND external plugins alike.

**How to apply:** Treat `__attr__` names as off-limits to touch from outside the defining class (including future plugin code). Use `__name__` for mixin/attribute names that should never be touched externally; use `_name` for merely-internal-but-not-fragile things.

---

## Feedback (coding style & process rules)

### No inline conditional expressions
Never write single-line conditional/ternary expressions (e.g. `x = foo() if cond else bar()`). Always expand to a full if/else block.

**Why:** User finds inline conditionals harder to read; wants explicit branching.

**Exception:** ternaries inside list/dict/set comprehensions are fine (e.g. `[x if cond else y for x in items]`).

Not OK:
```python
wire_od = float(wire.db_obj.part.od_mm or 0.0) if wire.db_obj.part else 0.0
```
OK:
```python
if wire.db_obj.part:
    wire_od = float(wire.db_obj.part.od_mm or 0.0)
else:
    wire_od = 0.0
```

### Complete function parameter type hints
Every function parameter must be type-hinted for ALL types that can actually be passed to it, no exceptions. If `None` can ever be passed, the hint must include `None` (`Foo | None`, or `Union[Foo, None]` if forced — see the type hinting conventions entry below; never `Optional[Foo]`), not just the "normal" type.

**Why:** This codebase is Cython-compiled; parameter type hints are a major runtime performance boost when compiled. Cython does NOT raise a compile-time error if the declared type is wrong — it only raises an exception at runtime when a call passes a value that doesn't match the hint. An incomplete/wrong hint doesn't fail fast; it silently ships and crashes later on some code path. Distinct from the Cython typing/DB-cache convention below (that one covers container-shape annotations for optimization; this one covers parameter completeness/correctness including None).

**How to apply:** Whenever writing or editing a function signature, check every call site (or reasonable caller behavior) for what types/values actually get passed, including None, and make sure the hint covers all of them.

### Type hinting conventions: typing module, Union vs `|`, quoting, TYPE_CHECKING imports
Several related rules govern how type hints are written in this codebase (updated 2026-07-28, supersedes any earlier looser guidance on quoting):

- **Minimize use of the `typing` module for builtins.** Use bare builtin generics (`tuple[float, float]`, `list[int]`, `dict[str, int]`) — never `typing.Tuple`/`typing.List`/`typing.Dict`/etc.
- **`Optional` is NEVER to be used**, full stop. Use `X | None` (preferred) or `Union[X, None]` (only when forced — see below).
- **`|` is preferred over `Union`** for unions in general. Only fall back to `Union` (imported as `from typing import Union as _Union`) when using `|` would force a quoted string annotation — i.e. when the type on one side of the `|` is only available via a `TYPE_CHECKING`-guarded import and quoting the whole `X | None` expression as one string would otherwise be the only option.
- **Quotes must NEVER wrap a builtin.** Never write `"tuple[float, float]"`, `"int"`, `"None"`, etc. — always bare. This includes never quoting an entire `SomeClass | None` expression just because `SomeClass` needs deferral — quote only `SomeClass` itself, and only inside a `Union[...]`, never bare-string with `|`.
- **If a module is imported only for typing purposes, guard the import with `if typing.TYPE_CHECKING:` and import the *module*, not the type/class directly** — e.g. `from . import somemodule as _somemodule`, then reference `_somemodule.SomeClass` in the annotation. Always alias the imported module with a leading single underscore (`_somemodule`), not the bare module name.
- When such a `TYPE_CHECKING`-only module reference needs to appear in a union with `None` (or anything else), use `_Union["_somemodule.SomeClass", None]` — quote only the module-qualified class reference, use `Union` (not `|`) for the union itself, never quote the whole expression as one string.

**Why:** Cython reads the annotations for compilation; a quoted builtin annotation like `-> "tuple[float, float]"` causes a real build failure. `Optional`/heavy `typing` usage and whole-expression string quoting are style choices the user wants standardized on across the codebase so signatures are consistent and Cython-safe by construction, not just "one recurring mistake" to catch after the fact.

Not OK:
```python
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from . import somemodule as _somemodule


def some_func(some_param: "_somemodule.SomeClass | None") -> None:
    pass
```

OK:
```python
from typing import TYPE_CHECKING, Union as _Union


if TYPE_CHECKING:
    from . import somemodule as _somemodule


def some_func(some_param: _Union["_somemodule.SomeClass", None]) -> None:
    pass
```

**How to apply:**
- Never quote a builtin type/generic — always bare.
- Never quote pieces inside a subscripted generic just because one piece needs it — quote only the specific inner name that needs deferral, and do so inside a `Union[...]`, not as part of a bare `|` expression.
- If nothing needs deferral, don't quote anything and don't reach for `Union` — plain `X | None` is fine.
- Never use `Optional` under any circumstance.
- Never import an actual class/type from a module that's only needed for typing — import the module itself under a `TYPE_CHECKING` guard, aliased with a leading underscore.

### Cython variable type reuse
Never reassign a type-annotated parameter/variable to a value of a **different type** in the same function. Works fine interpreted (dynamic typing), but crashes only once Cython-compiled — Cython gives the variable a fixed C-level storage type from the annotation, and reassigning to an incompatible type triggers a coercion failure.

**Why:** `gl/canvas2d/camera.py::Camera2D.zoom_at_point` reused `delta: float` for a later `Point` value (`delta = world_pos_before - world_pos_after`). Ran fine interpreted; crashed post-compile with `TypeError: must be real number, not Point`. Fixed by giving the Point-typed value its own name (`focal_delta`).

**How to apply:** Never reuse a parameter or annotated-variable name for a different type later in the function body, even though it "works" when run as plain interpreted `.py`. If debugging a report where dynamic-Python testing shows no problem but the user reports a live crash, ask whether the crash only happens in a Cython-compiled build before looking elsewhere.

### Cython typing + DB cache convention
The whole app (except `__init__.py`/`__main__.py`, see `builder/cython_build.py` `_SKIP_STEMS`) is Cython-compiled in frozen builds; type annotations are load-bearing for C-level optimization.

**How to apply:**
- Spell out fixed container shapes fully, e.g. models3d aabb: `list[list[float, float, float], list[float, float, float]] | DefaultStoredValueType`, obb: same inner list repeated 8 times. Multi-arg `list[...]` is fine at runtime (GenericAlias doesn't check arity).
- `_stored_*` caches on DB row classes hold the plain parsed Python value (list of lists of floats), NEVER a numpy array and not None. The property getter builds `np.asarray(cache, dtype=np.float32)` fresh on every access so caller-side in-place transforms (`@=`/`+=`) can't corrupt the cache. Don't "optimize" by caching/returning a shared ndarray or `.copy()`-on-return.
- Setters normalize with the mpf-safe idiom `[[float(str(item)) for item in row] for row in np.asarray(value).tolist()]`, store that list, write `str(value)` to the DB.
- Model3D position3d/angle3d follow the same list-cache pattern but return a fresh `Point`/`Angle` per access (NULL column → world origin/identity). INTENTIONAL: `__update_position3d`/`__update_angle3d` bind callbacks persist to DB but do NOT refresh the list cache, and `_position3d_id`/`_angle3d_id` uuids are per-Model3D-instance — this isolates changes so mutating one consumer's Point doesn't propagate to other objects sharing the same catalog model. Don't "fix" the stale cache or share ids per DB row.

### Cython benchmarking + hot-path style
The release build is Cython-compiled; interpreted-Python timing numbers are a floor, not the real number — the compiled build should be faster still, especially for hot loops.

**Optimization style:** default toward plain, well-typed Python loops over numpy/scipy vectorization for hot paths with many small per-call operations. Cython compiles straightforward loops into efficient C well; vectorization's per-call overhead (array construction, scipy's Python-level dispatch) doesn't go away under Cython — a vectorized approach slower in practice than a simple loop stays slower after compilation too.

**Case study:** `harness_designer/utils/mesh_surface_picker.py`'s `split_into_components()`. A scipy-based vectorization (`scipy.sparse.csgraph.connected_components`) caused a 24.6s → 72s regression because real housing meshes have many small raw groups and scipy's per-call overhead multiplied. Fix: keep one cheap vectorized global vertex-weld pass (`np.unique`) but do per-group connected-components as a plain Python BFS using the pre-welded ids.

**How to apply:** when a hot path is called many times with small/variable-size inputs (not one big call over a huge array), don't reach for numpy/scipy vectorization by default — benchmark against plain Python first.

### Performance and resource priorities
Performance comes first. Memory should be kept low but never at the expense of speed.

**Why:** Explicit priority from the user — the DB backend can be MySQL over a network, so each extra round-trip has real latency cost.

**How to apply:**
- Prefer fast paths (pre-computed data, VBOs, direct lookups) even at higher memory cost.
- Do NOT cache results of cheap math (simple arithmetic, small matrix ops, trig on a handful of values) — memory overhead outweighs recompute cost.
- DO cache results that are genuinely expensive to recompute (large mesh transforms, unchanged DB query results, surface analysis) or called every frame.
- Ask: is the computation genuinely expensive? If no, skip the cache.

**Benchmarking discipline:** The user benchmarks extensively (more time on bench tests than writing app code) and pushes for empirical verification (`timeit`, `dis`) over reasoning alone for hot-path/micro-optimization questions — catches imprecise framing (e.g. calling something a "no-op" when it still compiles to a real instruction). Match this: run a quick benchmark rather than just reasoning about what should be faster.

**Exception — plain-language walkthrough can suffice:** when deciding whether to move wire-stripe geometry math from CPU to a GPU shader path, talking through the actual operations (a subtract+normalize per segment, a running-sum addition) and their bounded scope (2 wires recompute per moved waypoint, not the whole project) was sufficient to conclude the GPU rewrite wasn't worth it — no benchmarking needed. Reserve insistence on an actual benchmark for cases where intuition has a track record of being wrong (numpy vs. plain-loop, memory layout/conversion order) — that's what `timeit`/`dis` is for. **Hard boundary: this exception does not extend to C-extension/Cython-compiled performance** — once a comparison crosses into compiled-C territory, reasoning it out isn't reliable (compiler optimizations, cache locality, interpreted-vs-compiled overhead defy plain-language prediction); those cases always need an actual test (see the scipy case above: assumed faster, measured 3x slower after compilation).

**Database query consolidation:** Multiple sequential queries that could be one query are a performance problem, especially over a network (MySQL). Collapse reads of related columns into one `SELECT col1, col2, col3` and writes into one `UPDATE col1=, col2=, col3=` wherever possible. The `size` property on `DimensionMixin` (one SELECT/UPDATE for width/height/length together) is the pattern to follow. If existing code makes N separate queries for N columns that could be one, flag it as a suggestion even if not the primary task — but keep suggestions in proportion, don't refactor a whole file over one extra query.

### Rotation matrix convention
`Angle.as_matrix_numpy` returns the **column-vector** rotation matrix `R` where `R @ v` rotates a column vector. But everywhere in the codebase that applies rotation via numpy `@` (e.g. `corners @= angle`) uses **row-vector** convention, equivalent to `v @ R.T`.

So: `world = (local * scale) @ R.T + position`, and inverse: `local = (world - position) @ R / scale`.

**Why:** A bug in `MeshSurfacePicker` had `rot_mat = R` and `inv_rot = R.T` swapped — worked at zero rotation (R=I) but broke picking/overlay rendering once a housing was rotated.

**How to apply:** When building a matrix-based ray/point transform cache from `Angle.as_matrix_numpy`: store `rot = angle.as_matrix_numpy`; forward (local→world) uses `rot.T`; inverse (world→local) uses `rot`. Fixed in `harness_designer/utils/mesh_surface_picker.py` `_refresh_transform_cache` and `_on_angle`.

### Use VBO not file
When mesh data is already loaded and transformed in an in-memory object (e.g. a VBO), read from that object directly rather than re-reading the source file and re-applying the same transforms.

**Why:** The in-memory representation is authoritative at runtime — re-reading/recomputing is redundant and a source of drift bugs (housing editor surface picking once produced wrong results by re-applying transforms already baked into the VBO).

**How to apply:** Before reaching for `np.load(path)` or similar, check whether the data already exists on a nearby object in the correct form — e.g. `Housing3D._vbo.vertices`/`Housing3D._vbo.face_normals` are already world-space.

### DB mixin check before assuming missing
Before saying a property/method doesn't exist on a database class, check all its mixins — it may be inherited. DB classes in `harness_designer/database/global_db/` commonly mix in from `harness_designer/database/global_db/mixins/` (e.g. `DimensionMixin`, `NameMixin`, `CompatTerminalsMixin`).

**Why:** Wasted a query-count once by replacing `db_obj.size = (w, h, l)` (one UPDATE via `DimensionMixin.size`) with three individual setters, because `size` wasn't visible directly on `Cavity` — it was inherited.

**How to apply:**
1. When code references `db_obj.some_property` and it isn't obvious on the class itself, grep the mixin files before concluding it's missing.
2. If a property genuinely doesn't exist: **ask** before adding it or substituting individual calls — don't silently substitute.

### No None-guards, fix the data
When a crash traces back to a NULL DB value (e.g. `models3d.point3d` NULL making `Model3D.position3d` return None, blowing up `obb += None` in Housing3D), do NOT add downstream None-guards or lazy backfill code.

**Why:** Positions can never legitimately be None — the default is world origin `[0.0, 0.0, 0.0]`, and the invariant lives in the database column default, not consumer code. `return None` branches in properties like `position3d` are just-in-case catches, not states callers should handle.

**How to apply:** Treat a NULL where the design says "never NULL" as bad data or a wrong schema default. Fix the row(s) with an UPDATE and/or fix the column default in `database/create_database/*.py` (models3d.py had `point3d` default `'NULL'` while cavities.py uses `'"[0.0, 0.0, 0.0]"'` — the latter is the intended pattern). **Exception:** `angle3d`/`quat3d` NULL is *meaningful* on models3d — triggers the part-orientation dialog on first download — don't default those.

### No fallback paths
Don't add fallback/catch-up logic that silently handles a condition that "shouldn't happen" (e.g. a render-time staleness check that recomputes geometry if some earlier immediate-update path was missed).

**Why:** Explicit: "I don't want a fallback path. if there is a problem I would rather it not get hidden by fallback code so we can actually address the underlying issue." Concrete case: `Wire.render()` had a `_geometry_stale`/`Point.stale` "safety net" that recomputed geometry at render time for batch updates — tracing showed it was never actually needed (the real update path fires synchronously via bound callbacks) and was dead-weight cruft that could have masked a real bug. Removed the check and the now-fully-dead `Point.stale` flag.

**How to apply:** Distinct from "never let exceptions propagate" below (that's top-level exception handling in the packaged app, where crashing is worse than logging-and-continuing) — this is about internal logic layers: don't add a second, deferred code path that quietly compensates if a primary path was somehow skipped. If tempted to add a "just in case" fallback/recompute branch, either make the primary path actually correct, or ask first. If an existing fallback like this is found while reading code, flag it rather than assuming it's intentional.

### No backwards compat pre-release
App has not been released — no existing user base has project files in old schemas, so schema/DB changes need no migration path or back-compat shims. Freely rename/restructure/drop columns and tables; don't add "if column missing, fall back to old behavior" branches or schema-version migration steps. If an old dev-database breaks after a schema change, that's expected — recreate it.

**Why:** Explicit statement (2026-07-26) re: the wire/splice/service-loop sibling-graph and `pjt_wires` waypoint-column redesign: "the application has not yet been released so there is no concern there."

**This is a point-in-time fact, not permanent policy** — re-check once the app has actually shipped a release; at that point real user project files will exist and this flips.

### Assume intentional design
Across this codebase, patterns that look unusual or inconsistent at first read have consistently turned out to be deliberate, load-bearing design decisions once traced far enough — not accidents or legacy cruft.

**Confirmed examples:** `_o_position3d`/`_o_angle3d` diff-snapshot pattern in `pjt_housing.py`; dunder-both-sides marking (see Naming convention above); `Point`/`Angle` singleton instances doubling as the propagation mechanism itself; `Config.__table_name__` deriving from `__qualname__` to dodge collisions; identical lazily-computed-and-persisted-point pattern deliberately repeated across `PJTCavity`/`PJTTerminal` rather than abstracted.

**Why:** User (sole author) stated directly: "There is a method to my madness. the more you read the code the more things make sense as to why they are done the way they are." Reinforced by the plugin architecture (see Commercial release plan below), which retroactively explains a lot of the strict internal/hands-off naming discipline.

**How to apply:** When something looks odd, redundant, or like it "should" be refactored, default to investigating *why* before proposing a change — read the surrounding class, check for mixins, check whether the same shape repeats elsewhere (a repeated pattern is itself evidence of intent), and ask the user rather than assuming inconsistency.

### Context-building conversations
The user deliberately initiates conversational, non-task segments (explaining rationale, business/architectural intent) specifically to transfer understanding into persistent memory for future sessions — not idle chat.

**Why:** Stated directly: "I like to have these conversations with you from time to time because it gives you a better understanding of why things are done the way they are and you are able to save that information to use it to guide what you do in other sessions."

**How to apply:** When the user shifts into this mode, engage genuinely: ask a clarifying follow-up if something is ambiguous or interesting, verify claims against actual code before committing them to memory, write the resulting memory precisely rather than generically. Don't just acknowledge and move on.

### Never let exceptions propagate
In this packaged (PyInstaller-frozen) desktop app, an uncaught exception must never propagate out of low-level layers (DB connectors, etc.) — it would lock up or crash the app, leaving the user unable to even close it gracefully. Always catch, log (`_logger.traceback`), and continue.

**Why:** Stated directly by the user after error reporting was added to `SQLConnector.execute()`/`executemany()` in [connector.py](harness_designer/database/db_connectors/sqlite_connector/connector.py) — confirming the existing blanket `except Exception` there is intentional, not an oversight.

**How to apply:**
- When adding error visibility (logging, dialogs) to an existing catch-all `except Exception`, keep it catching and continuing — never turn it into a re-raise.
- A user-facing error dialog must not become a lockup-by-proxy: if the failing code path can be hit repeatedly in a hot loop (mouse-move handlers, hover previews), dedupe/rate-limit the dialog (one per distinct error per session, always still logging).
- Dialogs shown from a caught exception must be marshaled onto the main Qt thread via `app.CallAfter` (see `process/manager.py`'s pattern) since the catching code may run on a background thread.

See also Dialog design convention below.

### New file callout
When the Write tool creates a NEW file (not editing an existing one), immediately run `git add <path>` for that file right after creating it.

**Why:** New files aren't staged automatically; the user commits and pushes without realizing a new file was left out — caused a real CI failure when `rthook_pip_distlib.py` was created locally but never committed.

**How to apply:** After every Write tool call that creates a new file, the very next tool call should be `git add <path>`. Don't wait until the end of the session.

### No bulk mechanical code edits
Don't build an automated script to bulk-apply source edits across many functions/files (e.g. inserting `-> None` on every function flagged by a static-analysis pass), even when the underlying analysis is unambiguous. Report findings (file/line lists, CSVs) and let the user apply/review edits himself.

**Why:** Python function/method signature syntax has too much variety (multi-line signatures, decorators, `*args`/`**kwargs`, positional/keyword-only markers, overloads, embedded comments, existing string annotations) for a mechanical rewrite script to handle every case safely. A single bad rule applied at scale risks widespread broken/subtly-wrong code — worse than the original problem. The user explicitly declined a follow-up auto-fix script for this exact reason after reviewing an implicit-`None`-return report.

**How to apply:** When a static-analysis pass produces a list of "safe"/"unambiguous" fixes, stop at the report. Don't propose or write an automated multi-file transform unless explicitly asked after seeing the report — and even then, show a diff/sample first before running broadly.

### Setup.py CLI is deprecated, the file isn't
Running `python setup.py <command>` directly (install, bdist_wheel, develop, etc.) is deprecated regardless of which command follows — setuptools throws `SetuptoolsDeprecationWarning`, pip has moved fully to PEP 517 builds. This does **not** mean `setup.py` itself is deprecated — `setuptools.build_meta` still executes that file internally even when invoked via `pip install .`/`python -m build`. The fix for "setup.py throws deprecation warnings" is "stop invoking it directly," never "delete setup.py."

**How to apply:** Never recommend or write code invoking `python setup.py <command>` directly, for this or any setuptools-based project. Static metadata belongs in `pyproject.toml`'s `[project]` table; only things requiring runtime Python belong in `setup.py`, reached only via `pip install .`/`python -m build`. (Note: this project has since gone further and removed setuptools/setup.py entirely — see Build system wheel rewrite below.)

### Validate against captured logs
When reimplementing something a real system already does correctly (compiler/linker invocations, wire protocols, binary formats), proactively ask for or use real captured ground truth (verbose build logs, network traces, hex dumps) rather than deriving purely from docs/training knowledge.

**Why:** While replacing setuptools' `build_ext` with a hand-rolled compiler invocation, real verbatim compile/link command lines from actual passing CI runs caught a real gap before shipping: a first-draft Windows link command was missing `/LTCG` (required to pair with `/GL`) and an explicit `/IMPLIB:` redirect — both visible in the captured log, neither obvious from general MSVC knowledge. Low-level system-integration code has a lot of "works by convention, not spec" surface area where being subtly wrong looks plausible but fails in ways hard to catch without running it.

**How to apply:** Treat provided ground truth as the source of truth over what would otherwise be guessed — diff derived output against it token-by-token before considering the implementation done.

### spawn.py is mandatory, don't touch/bypass
Every subprocess invocation in this codebase goes through `builder/spawn.py`'s `spawn()` — never replace with `subprocess.run()`/`Popen.communicate()`, even though it looks replaceable.

**Three distinct reasons:**
1. Classic dual-pipe deadlock — `communicate()` does solve this correctly.
2. **Windows pipe-handle inheritance by grandchild processes** — what `communicate()` does NOT solve. A grandchild (e.g. `cl.exe` spawning `mspdbsrv.exe`, or `cmd.exe` relaying to whatever it runs) can inherit the pipe's write handle. Windows won't signal EOF until every write-handle closes, so if a grandchild holds one open, any blocking read hangs forever regardless of threading/`select()`. Confirmed against bpo-23213 and MS pipe handle inheritance docs — not folklore.
3. Observability for long-running commands — `communicate()` is all-or-nothing (blocks until full exit); for a multi-minute build, that's total silence indistinguishable from a hang. `spawn.spawn()`'s live stdout streaming keeps a long build looking alive.

**Why:** The user has hit real, hard-to-diagnose hangs from exactly this class of issue before; `spawn.py` reliably avoids it across Windows/macOS/Linux for this project's toolchain (MSVC, cmake, ninja — known for spawning helper processes on Windows).

**How to apply:** Never modify `spawn.py`'s read loop, return value semantics, or threading model. Never introduce raw `subprocess`/`Popen` calls anywhere in `builder/` as an "improvement" — always route through `spawn.spawn()`. If a caller needs stronger failure semantics, do it in the caller using the `(returncode, error_lines)` spawn.spawn() already returns, never inside spawn.py itself.

### Config is a live DB, not a fixture
`harness_designer.config.Config.*` nested classes (e.g. `Config.logging`) use the `ConfigDB(type)` metaclass, whose `__setattr__` writes through to a real SQLite database (`%APPDATA%\HarnessDesigner\config.db`) on **every** non-underscore attribute assignment. `Config.logging.save_path = x` is a permanent, immediate change to the user's real app settings — indistinguishable from changes made through the running app.

**Why:** A debugging session did ad-hoc `Config.logging.save_path = <temp dir>` and `Config.logging.max_logfile_size = 200` to exercise log rotation in isolation. Those wrote straight to the live config.db; the temp dir was later deleted by the test's own cleanup, and the tiny size cap made ordinary startup logging trigger rotation on almost every write — corrupting the real config and causing a startup hang/crash loop.

**How to apply:** Never read from or assign to `Config.*` attributes in throwaway scripts. Before writing any config-touching test, check if the class is metaclass-backed (`type(cls) is not type`); if so, monkeypatch/mock at the Python level without going through the metaclass `__setattr__`, use a fully isolated copy of the config module, or explicitly save+restore in try/finally. Prefer passing a value as a constructor/function argument over mutating the shared class.

**Also applies to subagent prompts:** a delegated agent building `gl/canvas_pegboard` ran real QTest-driven runtime smoke tests calling `Canvas.set_grid_snap`/`set_grid_display`, which wrote `snap=True`/`enabled=True` straight into the live config.db's new `config_editor_pegboard_grid` table. The permission system blocked both the agent's own `DROP TABLE` cleanup attempt and a follow-up `UPDATE` fix — the user opted to fix it manually. When delegating any task involving runtime-testing GL canvases/editors/config-backed UI, explicitly instruct the agent not to exercise code paths that read/write live `Config.*` attributes, or to restore any value it changes before finishing.

### Silent crash debugging
When the app dies with **zero diagnostics** (no Python traceback, nothing in the log, no console output), that pattern means a genuine native/C-stack-level crash, not a normal Python exception — this codebase compiles to Cython C extensions, and deep Python recursion doing real work per frame (e.g. a DB query) can blow the C stack before Python's own `RecursionError` trips.

**Confirmed root cause pattern (2026-07-10):** two `@property` getters on the same DB row wrapper class calling each other — `PJTTerminal.is_start` checked `self.load`, and `PJTTerminal.load` checked `self.is_start` right back, guaranteeing infinite recursion whenever the raw `is_start` column was truthy (the schema default for every new row). Triggered by `PJTCavityControl.set_obj` eagerly loading a terminal's property tab whenever a cavity has one.

**How to apply when hunting a silent crash:**
1. Consider whether it's new-code-specific first, but don't over-anchor if the user says otherwise.
2. When the user names specific files, carefully read that file's `@property` getters for cross-references — grep for `if self\.\w+` patterns and trace whether any two properties call each other.
3. Eager (non-lazy) property-panel loading (e.g. unconditional `set_obj` calls unlike the `LazyTabMixin` pattern used elsewhere) turns a merely-buggy property into an immediate crash-on-select — worth checking which `set_obj`/`_load_tab` call sites are eager vs. lazy when a crash correlates with "selecting X."

### Don't launch the app yourself
Never launch (or relaunch, close/kill) the `harness_designer` Qt desktop app via Bash/PowerShell to "verify" a code change. Make the edit, tell the user what to check, wait for them to run it and report back.

**Why:** During 2D schematic editor work, repeatedly relaunching the app in the background after each small edit annoyed the user ("stop running it!!!"). Trying to stop/check for the running process afterward was ALSO wrong — the user hadn't asked for that either ("I didn't tell you to close it!!!"). The user manages the app's process lifecycle themselves.

**How to apply:** Never call `run.py` (or the app's entry point) via Bash/PowerShell to check a UI/rendering change, and never kill/stop a running instance on your own initiative. This is a native Windows GUI app with no screenshot/automation tool available, so launching it wouldn't even allow visual verification — it only produces console output for import/syntax errors, which `python -m py_compile` already covers without touching the running app. Use `py_compile` (or equivalent static checks) for pre-flight verification, then hand off to the user for the visual check.

---

## Project (current state, plans, open work)

### Current priority order
As of 2026-07-10: CI/build squared away. Sequence, in order:
1. **Handlers for adding objects** (3D editor) — was current focus.
2. **3D schematic editor** — get it fully functioning.
3. **Object browser** — explicitly not completed yet (e.g. the tree has no click-to-select wiring at all); deliberately deferred until after the 3D schematic editor.
4. **editor2d shared OpenGL context** work (`AA_ShareOpenGLContexts` / editor2d not yet sharing context) — bumped when the user shifted to handlers work.

**Why:** Deliberate reprioritization, not a stall — each stage is intentionally gated on the previous one.

**How to apply:** Don't flag stages 2-4 as overdue/half-finished until the stages before them are done. Don't treat object-browser gaps as bugs to fix — it's simply not built out yet. (Re-check current status with the user — this snapshot is from 2026-07-10 and may have moved on.)

### 2D schematic scope
Mechanical housing accessories — boot, cover, cpa_lock, tpa_lock, seal — never get a 2D schematic representation. Confirmed 2026-07-25: "those are not going to have any visuals as they are mechanical accessories and should not be displayed in a wiring schematic."

**Why:** A wiring schematic shows electrical/logical connectivity, not physical hardware.

**How to apply:** `objects/objects2d/boot.py`, `cover.py`, `cpa_lock.py`, `tpa_lock.py`, `seal.py` stay on the inert legacy contract (`Base2D.__init__(..., None, None, None, None, None)`) permanently — not a "not yet done" gap.

Still genuinely open (not yet decided): whether `transition.py`, `bundle.py`, `bundle_layout.py`, `wire_service_loop.py` (routing/grouping, not accessories) and `note.py` (already has real position/angle wired up, needs a VBO — `objects3d/note.py` is a ready-made reference) get real 2D visuals. Ask before building those.

### Housing/cavity callback ordering bug (known, don't touch)
Confirmed bug (2026-07-25): for a freshly-added housing, `Housing2D.__init__` runs `_recompute()`/`_layout_children()` against zero cavities, because `PJTCavity` rows don't exist yet at that point — `objects/housing.py`'s `Housing.__init__` builds `obj2d` first, and cavity creation (`db_obj.update_cavities()`) only happens later inside `obj3d`'s construction (triggered by the 3D model's `download_complete()` callback). No cavity/terminal gets a real `position2d`/`angle2d` from the housing's layout on first add, and `_bind_callbacks` binds to an empty cavity list. Reloading the project papers over it (cavities already exist in the DB by then).

**Why not fixed yet:** The user said explicitly: "I have to work on getting some kind of a callback registered for when a cavity gets added. So don't worry about that for the time being." He is building the fix himself.

**How to apply:** Don't attempt to fix this construction-ordering issue unless asked. If asked to work on 2D housing/cavity/terminal code, this is the reason positions look wrong on a freshly-added housing — point to this note and ask before touching it.

### Wire-size NULL backfill plan
Wire size columns (`wire_size_dia`/`wire_size_cross`/`wire_size_awg` on `wires`, similarly on `seals`/`terminals`) can be NULL even though derivable from a sibling column (conversion helpers exist in `utils/wire_conversions.py`).

As of 2026-07-09: don't add a 3-way fallback-calculation chain (dia ← cross ← awg) into handler/query code. The user is writing a standalone maintenance utility (invoked from an app menu) that scans for NULLs and backfills via `utils/wire_conversions.py`; later this will also run automatically when a new part is added.

**How to apply:** When writing queries/logic reading a wire-size column that could be NULL, do not add derivation-from-other-columns logic inline — assume the maintenance utility will keep these populated, only add NULL-safety (`IS NULL OR` guards, skip-if-None). If asked for the actual backfill utility later, that's a separate feature using `utils/wire_conversions.py`.

### Peg Board Editor
Multi-phase new feature (`ui/editor_pegboard/`, `gl/canvas_pegboard/`) showing a wire harness laid out flat on a physical peg board (manufacturing formboard) — top-down, real 3D part meshes reused via the shared VBO/arena system, bundle strands instead of individual wires (except bare-terminated wires), user-repositionable with a length-budget clamp, plus floating Excel-like `QTableView` overlays at branch points/connectors/bare terminals.

Full plan (locked in via plan mode) at `C:\Users\drsch\.claude\plans\tranquil-orbiting-spindle.md`. **Two locked-in architecture decisions — do not re-litigate:**
1. Tables are native `QTableView` overlays repositioned/rescaled from world coordinates each frame, not a from-scratch GL text pipeline.
2. Drag repositioning uses a **local per-segment length clamp only** — no FABRIK/rope-relaxation solver.

**Phasing:**
1. Static top-down render — DONE as of 2026-07-13 (3 new `pjt_pegboard_*` DB tables, `gl/canvas_pegboard/` canvas+camera+mouse/key handlers, VBO-reuse rendering with OBB-derived flattening via `gl/canvas_pegboard/flatten.py`, anchor collection via `layout_graph.py`, dock in `ui/editor_pegboard/` wired into `mainframe.py`). NOT visually verified end-to-end (no GUI-automation tool available) — only static compile/import checks and no-crash launch test. User should open a real project and check the dock visually.
2. Bundle length property (`PJTBundle.length_mm`/`length_m`, added) + bare-wire/bare-terminal visibility filtering. `strand_mesh.py`'s `build_strand_quad()` exists but isn't wired into rendering yet.
3. Drag repositioning with the local length clamp + persistence to `pjt_pegboard_points`/`pjt_pegboard_waypoints`.
4. Excel-like table overlays (`pjt_pegboard_tables`).

**Why:** User wants a manufacturing-floor view separate from the existing Schematic Editor (`ui/editor_2d/editor2d.py`), a different simplified/arbitrary-layout rendering model unsuited to reusing real 3D meshes.

**How to apply:** When resuming, read the plan file first, check task tracking for what's done, don't re-ask the two locked-in architecture questions.

### Wire bundle packing requirements
Requirements/architecture gathered (2026-07-14) for a concentric-twist wire bundle packing feature, building on Peg Board Editor above.

**Governing spec:** MIL-STD-339 ("Twisting of Wires and Cables"), Section 600 Table XXI — NOT MIL-STD-681 (wire ID/color coding) or MIL-W-5088 (general aerospace install practice).

**Solver architecture:** Not reducible to chained closed-form formulas (an interstitial filler's contact points with flanking wires shift as its own radius changes — self-consistent/implicit, not plug-in). Right approach: numeric/geometric relaxation-based constraint solver (physics-like — circles repel when overlapping, settle toward target layer radius), seeded from layer-based construction as initial guess. Regular code running locally/on the user's own infra.

**Claude's role if embedded:** NOT as a runtime compute backend (code execution tool caps at 90s wall-clock, not for heavy numeric jobs). Actual fit: orchestration/judgment layer via API/Agent SDK tool-use — deciding repack-vs-filler-vs-shortened-lay-length tradeoffs at branch voids, explaining tradeoffs using the solver's numeric output as tool results, not computing geometry itself.

**Hard requirement:** A sectional (cross-section) view of the bundle must be renderable at **every single location where bundle composition changes** (every branch/pin-out point), not just once for the whole run. Must-have, not optional — ties into existing 2D/3D GL editors so the solver's output gets visual sanity-check.

**Prior attempt context:** A Copilot-written packer for ~75 wires took ~10 min/run with only ~30% "good" results — unconstrained stochastic search (annealing/GA) without a good deterministic seed, not a compute limitation. A well-formulated deterministic/numeric solver should run well under a second even at hundreds of wires.

**Confirmed technique:** Interstitial filler wires nested in gaps between same-layer wires, sized to stay below flanking wires' apex. Max filler diameter = flanking wire diameter / 4 (tangent-circle geometry derivation). Cross-validated against a public filler-factor reference table (asymptotic value 0.25 for 25+ wires in a layer).

**Transition bulb (branch points):** Real harnesses deliberately do NOT maintain the concentric pack through a branch — the bundle bulbs/widens where wires are pulled out, absorbing packing disruption and doubling as strain relief. This resolves the repack-vs-filler-vs-shortened-lay-length dilemma only for mid-run composition changes (no branch, e.g. pin-splitting a load across 2 wires) — true branches get their own "transition bulb" geometry (blended/tapered profile) instead. Model needs at least two distinct cross-section behaviors: concentric pack (trunk) and transition bulb (branch) — not one universal solver.

**How to apply:** Use as the requirements baseline when implementation starts, don't re-derive from scratch. Sectional-view rendering at every composition-change point is a hard requirement for v1.

### Build system wheel rewrite
harness_designer builds via a fully custom PEP 517 backend (`builder/_backend.py`) — no setuptools anywhere, not even `setup.py`.

Went through three iterations: (1) install-then-mutate site-packages (original, fragile); (2) `setup.py` + `setuptools.build_meta` via `pip install .`; (3) **final: fully custom PEP 517 backend.** Reason: setuptools is fragile and getting worse release over release; the actual compile need (uniform flags across ~475 auto-discovered `.py` modules + 2 hand-written `.pyx` files) doesn't need setuptools' generality. Windows toolchain discovery already solved by `pyMSVC`; Linux/macOS just need plain `gcc`/`clang`.

**Architecture** (all in `builder/`, `setup.py`/`MANIFEST.in` gone entirely):
- `builder/compiler.py` — per-platform compile/link. POSIX flags from `sysconfig.get_config_var`. Windows is a hardcoded flag list (no sysconfig equivalent): `/c /nologo /O2 /W3 /GL /DNDEBUG /MD` to compile, `/DLL /INCREMENTAL:NO /LTCG /LIBPATH:<py>\libs /EXPORT:PyInit_<name> /IMPLIB:<redirected>` to link. Every recipe validated against real captured compile/link command lines from actual CI runs on all three platforms. MSVC/Windows-SDK include/lib search paths deliberately NOT re-specified — `cl.exe`/`link.exe` auto-search `INCLUDE`/`LIB` env vars already populated by `pyMSVC.setup_environment()` (via `builder/msvc_env.py`). Compilation parallelized across `os.cpu_count()` threads via `ThreadPoolExecutor` calling `builder/spawn.py` (confirmed thread-safe).
- `builder/cython_build.py` — pure file discovery (`discover_modules()`, no `setuptools.Extension`) + `cythonize_to_c()`. **Gotcha (verified empirically):** `Cython.Build.cythonize(paths, build_dir=...)` silently has no effect for absolute source paths (warns, writes `.c` next to source instead) — paths must be relative to cwd, cwd must be repo root, for `build_dir` redirect to work. `discover_modules()` returns repo-root-relative paths for this reason.
- `builder/wheel_build.py` — orchestration: reads `[project]` from `pyproject.toml` via `tomllib`/`tomli`, stages a build dir (copies `__init__.py`/`__main__.py` + non-source assets, replacing `MANIFEST.in`'s job), cythonizes + compiles, hand-writes `METADATA`/`WHEEL`, hands the staged tree to `wheel.wheelfile.WheelFile.write_files()` (auto-computes RECORD with sha256 hashes). Verified end-to-end: 620 real files, zero RECORD hash mismatches.
- `builder/_backend.py` — actual PEP 517 hook module (`build_wheel`/`build_sdist`/`get_requires_for_build_wheel`/`get_requires_for_build_sdist`). Supports `pip install . --config-settings cythonize=false` for a fast uncompiled dev build (ships plain `.py` for ~475 auto-discovered modules; `bvh.pyx`/`culling.pyx` always compile, no fallback).
- `pyproject.toml`: `build-backend = "builder._backend"`, `backend-path = ["."]`. `[build-system] requires` = Cython, numpy, wheel, packaging, pyMSVC (Windows only) — no setuptools, no pyinstaller.

CI needed zero changes — `pip install .` was already the command; only what `pyproject.toml` points it at changed.

**How to apply:** If the build breaks, `builder/compiler.py`'s recipes are the most likely fragile point (hand-maintained, not setuptools-maintained) — check against a fresh captured CI log before assuming flags are still correct, especially after a Python version bump or Windows Python installer layout change.

### PyAssimp PyPI initiative
Upstream pyassimp doesn't publish to PyPI and assimp/pyassimp aren't cleanly separated. After a failed attempt to get upstream to fix this, the user intends to package and publish their own pyassimp to PyPI.

**Current stopgap:** `builder/build_native_deps.py` builds assimp from source via CMake/Ninja against the `libs/assimp` submodule, pip-installs PyAssimp's bindings from that submodule path with `--no-build-isolation`, then manually copies the built assimp shared libraries into wherever pip installed pyassimp.

**Why setuptools is still in CI at all:** upstream `libs/assimp/port/PyAssimp/setup.py` does `from distutils.core import setup` — genuinely distutils-dependent. Only still works because setuptools (≥60.x) vendors distutils and ships a `_distutils_hack` shim redirecting `import distutils`. This is the only remaining reason setuptools is installed anywhere in this project's CI.

**Concrete plan:** Give PyAssimp the same treatment harness_designer got — a custom PEP 517 backend (no setuptools, no distutils, no setup.py), following the `builder/_backend.py`/`builder/wheel_build.py` pattern. Cythonize obviously doesn't apply, but the backend-writing playbook transfers directly. Considered "fairly easy."

**How to apply:** Once shipped, remove setuptools from all three CI workflows' "Install build tools" step entirely. Expect the CMake/Ninja assimp build + vendoring step in `builder/build_native_deps.py` to collapse to a plain `pip install pyassimp` (or whatever it's named) once on PyPI — don't be surprised if that file shrinks dramatically or disappears in a future session.

### PyInstaller output cleanup (DONE)
`_clean_dist()` in `builder/build.py` strips stub `.py`/`.pyi`/`.pyc` files, dead files (duplicate data, unreferenced resources), and empty directories from the PyInstaller onedir output after the post-build rename (HD→harness_designer), before installer packaging (macOS `build_pkg.sh`, Linux `install.sh`, Windows Inno Setup).

**Why:** The onedir output contained material that got compressed/packaged into the installer unnecessarily, bloating installer size.

**How to apply:** Implemented as `_clean_dist(app_dir)` called from `build_installer()`, right after the rename and before `installer.py`'s steps. Walks the tree with `os.walk`, deletes stubs/empties, logs what was removed for auditability.

### Commercial release plan
User plans to release harness_designer commercially, targeting a business-use price point around "10 cents on the dollar" vs. incumbent enterprise harness-design CAD (Zuken E3.series, Siemens Capital, CATIA Electrical Harness Installation, Autodesk Inventor Routed Systems).

**Competitive research (2026-07-19):** Every tool with real 3D connector/housing positioning is enterprise-tier, quote-only pricing, aimed at automotive/aerospace OEMs. Every free/cheap harness tool found (harness.design, EZ Wire, Splice CAD) is 2D/schematic-only — none do 3D. No free-and-3D overlap exists in the market currently. harness_designer's live, continuous, no-button-press full-3D wire reflow during a housing drag/rotate (spotting pinch points and excess wire-entry-angle stress in real time) appears to have no public precedent even among enterprise 3D tools.

**Business model:** Core app stays lean; enterprise-tier feature parity is planned to arrive later as separate paid add-ons/extensions/plugins, not built into core — à la carte, a company buys only the modules it needs. The `harness_designer` package is purpose-written for this: a plugin does a plain `import harness_designer` and gets full access to the UI, DB layer, and rendering pipeline — no separate internal-vs-public API to maintain. A plugin is just another consumer of the same objects the core app uses.

**Why:** The user's read: the real SMB/mid-size pain isn't just enterprise CAD's price — it's being forced to pay for a "mess of things they don't use." Unbundling directly targets that: core covers the baseline, paid add-ons cover specialized capability (e.g. the wire-bundle-packing solver above could plausibly be one such add-on rather than core weight).

**How to apply:** When prioritizing features, weigh value to the underserved SMB/DIY/small-manufacturer segment over matching every enterprise-suite feature — the wedge is "the only 3D option at this price," not feature parity. When a new capability comes up that's enterprise-suite-grade in scope (heavy solvers, certification/compliance workflows, PLM integration), consider flagging whether it belongs in core or a future à la carte module. Enterprise-tier sales (Tier-1 automotive, aerospace) are a plausible later target but face real moats (PLM integration, certification, support contracts) price alone won't overcome — don't assume the low price point converts them directly.

---

## Architecture notes (deep-dive references)

### GLContext is `with`-only — manual acquire()/release() removed entirely
`harness_designer/gl/context.py`'s `GLContext` (the re-entrant, thread-safe wrapper around a `QOpenGLWidget`'s `makeCurrent()`/`doneCurrent()`) no longer has public `acquire()`/`release()` methods. They were renamed to private `_acquire()`/`_release()`, called only by `__enter__`/`__exit__`. The class can now only be used as `with some_context: ...`.

**Why:** Root-caused 2026-07-29 after a long chase through several confirmed-but-seemingly-unrelated crashes (`RuntimeError: context has not been acquired` at random, hard-to-reproduce moments — sometimes during model downloads, sometimes on app close, sometimes mid-session with no clear trigger) plus one genuinely new "Cannot make QOpenGLContext current in a different thread" crash. The actual mechanism: every call site used to do `ctx.acquire(); <GL work>; ctx.release()` manually, with no `try/finally`. If *any* exception occurred in `<GL work>` — and Qt's own slot/callback dispatch (signals, `QTimer.singleShot`, etc.) silently swallows an uncaught Python exception instead of letting it propagate — the `release()` line was simply never reached. `GLContext.ref` (its internal nesting counter) leaked upward by one, permanently, with no way to self-correct. From that point on, every future `acquire()` on that same `GLContext` instance saw `ref != 0` and wrongly trusted "we must already be current," skipping the real `makeCurrent()` call — eventually surfacing as a crash at some completely unrelated later moment, on whatever thread happened to touch that context next. This explains the "random timing, even at shutdown" pattern precisely: teardown code is exactly where an unexpected exception is most likely, and once one leaks the ref count, literally anything touching that context afterward is a ticking time bomb. Catching the exception at each call site wouldn't have been sufficient either — catching doesn't retroactively call `release()` for whatever code already ran past the point of failure; only a construct that guarantees cleanup on unwind (`with`/`__exit__`) closes the hole at the source.

**How to apply:** Never add a new `.acquire()`/`.release()` pair anywhere for a `GLContext` — the methods don't exist publicly anymore, so this is a hard error, not just a style violation. Always `with some_widget.context: <GL work>`. This is safe to nest (re-entrant — a nested `with` on an already-held context just bumps the ref counter, no deadlock) and safe across early returns/exceptions inside the block. If a future GL-touching class introduces its own similar "acquire a resource, do work, release it" pattern (VBO handling already has its own separate, unrelated `.acquire()`/`.release()` on `PooledVBOHandler`/`NonPooledVBOHandler` — those are NOT `GLContext` and were deliberately left alone in this fix), apply the same reasoning: prefer a context manager over a manual pair whenever an exception between the two steps would leave shared state permanently wrong.

### Objects3D context menu architecture
Key conventions (learned 2026-06-11 while completing the objects3d context menus):
- Every scene item is an `ObjectBase` (`objects/object_base.py`) with `.obj2d`/`.obj3d` children; `Base3D.parent` points back to the ObjectBase. Menus receive the Base3D as `self.selected` (HousingMenu uses `self.obj`); ObjectBase-level ops (select, clone, rotate menus) must use `.parent`.
- Shared menu callback helpers live in `harness_designer/objects/objects3d/menu_ops.py` (select/clone/delete/properties/trace_circuit/start_handler/run_attached_handler/get_part_id).
- Interactive placement flows are `harness_designer/handlers/Add*Handler(mainframe, ...)`; the toolbar installs them via `MainFrame._on_tool_mode_change`; context menus use the public `MainFrame.set_obj_handler()` (added 2026-06-11). Housing-attached handlers (Seal/CPA/TPA/Cover with a housing arg) create the db object in the constructor — finalize with `capture_position(...)` + `release_capture()`.
- Object creation = insert into `project.ptables.pjt_*_table`, wrap in `objects/<type>.py` class, register with `project.add_<type>(obj)`. Deletion = `project.delete_<type>(db_id)` (pops registry + deletes db) plus `mainframe.remove_object(parent)`.
- Circular import trap: `objects/<type>.py` imports `objects3d/<type>.py` at module level, `handlers` imports `objects`, `ui` imports `handlers` — so objects3d modules must import `handlers`, `ui.dialogs`, and sibling `objects` classes lazily inside callbacks. Importing `harness_designer.objects.housing` before `harness_designer.ui` also fails (pre-existing cycle via objects2d → ui.widgets); the app imports `ui` first.
- `Point.db_id` is a string like "1233d"/"1232d" — strip the 2-char suffix for raw db ids.
- Properties UX: the object editor dock shows the *selected* object via the per-table singleton control (`db_obj.table.control`, a QTabWidget with `set_obj()`); the context menu "Properties" opens `ui/dialogs/properties_dialog.py` **modelessly** (`show()`, not `exec()`) with a *fresh* instance of the same control class so both can display different objects at once. On dialog close, call `tab_widget.set_obj(None)` to unbind live position callbacks. An object "supports" the dialog iff its table has a registered control.
- `Base3D.identify()` and the 2D menus (objects2d) are still stubs/WIP (as of 2026-06-11 — re-check current status).

### Dialog design convention
All dialogs derive from `ui/dialogs/dialog_base.py` (`BaseDialog`), using `CustomizeWindowHint` plus a custom draggable `Header` widget instead of the native title bar. Dialogs intentionally have **no native close (X) button** — dismissible only via the QDialogButtonBox buttons at the bottom.

**Why:** Deliberate design choice for a clean, uniform interface.

**How to apply:** Never suggest or add native window decorations, an X button, or Escape-close behavior to these dialogs. Any close-time cleanup must hook `finished`/`accepted`/`rejected`, which the bottom buttons always emit. See objects3d context menu architecture above for the modeless properties-dialog cleanup pattern.

### CallAfter vs CallLater
`CallAfter` (`harness_designer/app.py`) emits a Qt signal; called from the main thread, sender/receiver share thread affinity so Qt uses a direct connection and the function fires synchronously — no deferral.

`CallLater` (`harness_designer/app.py`) uses `QTimer.singleShot(0, ...)`, which always defers until the event loop regains control after the current handler returns.

**Why:** Confirmed fix for the object-editor loading sequence in the 3D GL editor — the GL canvas needs to repaint to show selection state, and the busy cursor needs to be set, before heavy DB queries run. `CallLater` wrapping the object-editor load achieves this.

**How to apply:** Use `CallLater` when deferring work that must happen after the current call stack unwinds (e.g. after a selection signal has propagated and the GL canvas has painted). Use `CallAfter` only for cross-thread dispatch from background threads.

### Cavity 3D angle binding
Bind the 3D cavity object to `db_obj.angle3d` (the project cavity's world-space angle), NOT `db_obj.part.angle3d` (the global baked part angle). Using the project angle makes the cavity visually follow housing rotations.

Do NOT override `_update_angle` or `_update_position` in `objects3d/cavity.py`. Those overrides propagate deltas to the terminal — combined with the project angle binding, they create a callback chain that fires during project loading (before all objects are initialized), causing the app to freeze. `Base3D._update_angle` handles everything correctly on its own once the right angle is bound.

**Why:** The global part angle never changes when the housing rotates, so cavities stayed in their baked orientation. Switching to project angle fires `Base3D._update_angle` directly via the existing housing rotation callback chain. The overrides existed to propagate deltas to terminals, but with the project angle this delta propagation during loading caused a freeze.

**How to apply:** In `objects3d/cavity.py` `__init__`, pass `db_obj.angle3d` (not `db_obj.part.angle3d`) to `Base3D.__init__`. Don't add `_update_angle`/`_update_position` overrides. Terminal delta propagation is handled at the DB layer by `pjt_cavity._update_angle3d`.

### Per-table control widgets are class-level singletons — must be explicitly cleared, not just detached
Every `PJT*Table` wrapper (`database/project_db/pjt_*.py`) has a `_control`/`control`/`start_control()` trio where `_control` is a **class attribute**, not an instance attribute — e.g. `PJTWiresTable._control` (`pjt_wire.py:42`). `start_control()` runs once per table, at `MainFrame` construction (`ui/mainframe.py`, ~17 calls), so the same `PJTWireControl`/`PJTHousingControl`/etc. QTabWidget instance is reused for the whole app session, correctly surviving `PJTTables.load()` rebuilding the table *wrapper* instances on every project (re)load.

**The gotcha:** because the widget is a class-level singleton, detaching it from the object editor dock (`ui/editor_obj/editorobj.py` `EditorObjPanel.set_selected`) is not enough to release whatever `db_obj` it was last bound to — the widget itself keeps a strong `self.db_obj` reference (set via `set_obj()`) until something explicitly calls `control.set_obj(None)`. Found 2026-07-29 while auditing for project-switch memory leaks (see Peg Board/project-switch feature below): `EditorObjPanel.set_selected(None)` only did `self.control.hide()`/`removeWidget`/`setParent`/`self.control = None` — never `self.control.set_obj(None)` — so the last-selected object of the outgoing project stayed pinned by the shared control widget indefinitely (until a user happened to select another object of that same table type in any project, ever). `ui/editor_db/edit_dialog.py`'s `EditDialog.Destroy()` already did this correctly (`self.control.set_obj(None)` before reparenting), which is what confirmed `set_obj(None)` is a safe, already-supported call on every table's control (every `_load_tab`/mixin `set_obj` null-checks `db_obj is None`).

**Why:** This is the one non-weakref, non-self-pruning cache found in an otherwise thorough audit (Point/Angle/Color singletons, both DB-row singleton metaclasses, and `PooledVBOHandler._instances` are all weakref-keyed and self-prune when GC'd). Everything else in the project-switch teardown path (`ui.mainframe.MainFrame.unload`, `objects.project.Project.close`) works by dropping references and letting GC/weakref finalizers do the rest — this was the one place a strong reference survived that teardown by design (the widget itself is supposed to survive; only its `db_obj` binding wasn't being cleared).

**How to apply:** Fixed in `EditorObjPanel.set_selected` — both the deselect-to-`None` branch and the swap-to-a-different-object branch now call `self.control.set_obj(None)` on whatever control is being detached, guarded by `self.control is not control` in the swap branch (so reselecting a different object of the *same* table type, which reuses the same singleton widget, doesn't immediately clobber the just-set new `db_obj`). If a new "set the object editor dock's control singleton to X" call site is ever added, apply the same guard/clear discipline. If auditing for similar leaks elsewhere, the pattern to search for is: a class-level (not instance-level) attribute that's a strong reference, set once, and any place that "detaches" it without also nulling out whatever object-specific state it's holding.

### Rigid-child positioning convention: offset @ parent.angle3d + parent.position3d
Any object positioned as a rigid child of another placed object (cavity-in-housing, terminal-in-cavity, and by the same logic anything placed relative to a terminal/cavity/housing in the future) must compute its world position as:

```python
pos = local_offset            # child's own local-frame offset from the parent
pos @= parent.angle3d          # rotate by the PARENT's own already-correct world angle
pos += parent.position3d       # translate by the PARENT's own already-correct world position
```

**Never** re-derive from further up the chain (e.g. skip the immediate parent and rebuild from the grandparent's position plus a catalog-local offset) — that's the bug this entry documents.

**Why:** Confirmed 2026-07-29 by cross-referencing three independent pieces of evidence: (1) `database.project_db.pjt_cavity.PJTCavitiesTable.insert()` (`pjt_cavity.py:251-252`) computes a fresh cavity's `position3d` as exactly `c_position3d @ h_angle3d; += h_position3d` — local catalog offset rotated by the **housing's** angle, translated by the **housing's** position (not the cavity's own combined angle, which is a separate additive value used only for the cavity's own displayed orientation). (2) Empirically verified against a real project row: plugging real housing/cavity catalog data through that exact formula reproduces the DB's actual stored cavity position to 5 decimal places. (3) `PJTHousing._update_angle3d`/`_update_position3d` (`pjt_housing.py:980-1420`, the housing move/rotate handlers) already treat a terminal as a rigid child of its cavity everywhere else in the system: on any housing move/rotate, `terminal.position3d` is batch-transformed in the exact same rigid group as `cavity.position3d` (never independently recomputed), and `terminal.angle3d` is explicitly set to **mirror the cavity's own angle3d exactly** (`pjt_housing.py:1370-1373`, comment: "Terminal/seal angle mirrors its cavity's angle exactly").

`handlers.terminal_handler._male_terminal_position`/`_female_terminal_position` originally violated this — built the terminal's position from `pjt_cavity.part.position3d` (global catalog local offset) rotated by `pjt_cavity.angle3d` then translated by `pjt_cavity.housing.position3d`, i.e. re-deriving the housing→cavity leg of the chain from scratch instead of just building on the cavity's own already-correct `position3d`. Silent bug (no exception, no crash) — produced a plausible-looking but wrong position, off by a not-obviously-meaningful delta, that only diverged from the cavity's real position; discovered by directly comparing the formula's output against real project DB rows for a terminal placed in a freshly-added-this-session cavity ("cavity is visually correct, terminal is not" was the original symptom report).

**How to apply:** Fixed 2026-07-29 in both `_male_terminal_position`/`_female_terminal_position` (`handlers/terminal_handler.py`) to `pos = Point(0,0,z_offset); pos @= pjt_cavity.angle3d; pos += pjt_cavity.position3d`. If a similar "silently wrong but plausible-looking position" bug turns up for any other object type positioned relative to a parent, check first whether its placement formula uses the *immediate* parent's own already-correct `position3d`/`angle3d`, or whether it's (incorrectly) re-deriving from a grandparent + catalog-local data.

### Selection interaction convention
For list-style widgets: `itemSelected(row)` fires on any selection or selection change; `itemUnselected()` fires only on the transition from something-selected to nothing-selected (including programmatic clears like filter/sort resets). Deselection must always be possible: click the selected row to toggle off, click empty area, or press Escape.

**Why:** Qt delivers the first click of a double-click as a normal press, so naive click-to-deselect breaks double-click activation. The user wants: double-click on a selected row keeps it selected and activates it.

**How to apply:** Defer the toggle-deselect on a single-shot timer, cancel it in `mouseDoubleClickEvent`. The wait adapts to the user's measured double-click speed — rolling 5-sample window, trim min/max, blend in stored average, persist via a `ConfigDB` config class (see `EditorDBConfig.double_click_average` and `EditorList` in `harness_designer/ui/editor_db/base.py` as the reference implementation). Reuse that pattern rather than reinventing it in other widgets.
