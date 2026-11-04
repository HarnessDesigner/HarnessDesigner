# Claude Memory — harness_designer

This file is the single source of truth for Claude's persistent memory about this project. It replaces the auto-memory system's per-topic files. When memory needs to change (add/update/remove a learned fact, feedback, or project note), edit **this file** directly — do not write to the separate auto-memory store.

Compiled from prior auto-memory on 2026-07-28. Entries are point-in-time observations, not live state — verify claims about code behavior against the current code before asserting them as fact, especially older entries.

---

## MANDATORY: per-directory MAP.md files (replaces the old single CODEBASE_MAP.md, 2026-10-19)

Documentation of "what's in this directory, what each file does, known oddities/pitfalls" now
lives **one `MAP.md` per directory**, right next to the code it describes, not in one giant
root-level file.

- **Read `CODEBASE_MAP.md` (repo root) once at the start of every new session** — a small
  folder-only tree with a brief outline of what each directory holds (about 8 KB). It lists no file
  names and holds no per-file notes; it is a trail of breadcrumbs to the right directory, whose own
  `MAP.md` lists the files.
- **Before working in any directory, read that directory's own `MAP.md` in full.** It has the
  real description of every file and subfolder there, plus any known oddities/pitfalls — this is
  more reliable than `CODEBASE_MAP.md`'s folder outlines or asking me (MEMORY.md) for structural detail.
- **Update that directory's `MAP.md` any time a file is added, removed, renamed, or otherwise
  changed in a way that affects it** — do this as part of the same change, not as a follow-up.
  `CODEBASE_MAP.md` only lists folders, so touch it only when a directory is added, removed or
  renamed (or its purpose changes).
- Every `MAP.md` follows the same minimal shape: a `## FILES` section with one `####` header per
  file, and a `## FOLDERS` section with one `####` header per subdirectory — each header followed
  by a short paragraph (what it's for, plus any oddity/pitfall folded in). The one optional extra
  is a trailing `## DESIGN NOTES` section (added 2026-11-01) with one `####` header per design note.
- **Design notes live in the `MAP.md` of the directory they describe, under `## DESIGN NOTES` --
  not in this file.** A note is anything about how a specific area works or why it is built that
  way: an incident and its root cause, a feature's design and status, a gotcha. When you learn one,
  append it to that directory's `MAP.md` (create the `## DESIGN NOTES` section if it is missing).
  This file keeps only what is not tied to one directory: user background, working-style feedback,
  coding conventions, cross-cutting rules, and project-level plans/decisions. About 90 notes were
  moved out on 2026-11-01 and then trimmed (no pointers were left here).
- **Do not record bug-fix narratives anywhere** (user, 2026-11-01): "X was broken, here is how it was
  fixed" belongs in git history. Write a design note only for a rule that still constrains the code
  (an invariant, a gotcha someone could re-break, a decision and its reason, an open limitation) and
  state it as the rule, without the story. Do not log "built, not yet run" status either; say what
  was verified in the final reply instead.

---

## MANDATORY: use `diagnostics/dep_trace.py` for "where/what/who" code questions

## Reference

### Codebase map
See the MANDATORY section above for the read-at-start / per-directory-`MAP.md` rule. `CODEBASE_MAP.md` (repo root) is a folder-only tree with brief outlines; the file lists and full descriptions live in each directory's own `MAP.md`.

Key insight: **part-type fan-out** — a part type (e.g. "seal") has parallel files in `database/global_db`, `database/project_db` (`pjt_*`), `database/create_database`, `objects/objects_schematic`, `objects/objects_3d`, `handlers`, and `ui/editor_db`. Changing a part type usually touches all seven.

### Third-party dependencies (non-stdlib imports)
Quick reference — which package a given import name comes from, and anything non-obvious about where it's used. For what each file in a directory actually does, read that directory's `MAP.md` instead.
- `PySide6` → PySide6
- `OpenGL` → PyOpenGL
- `numpy` → numpy
- `pandas` → pandas
- `PIL` → Pillow
- `requests` → requests
- `keyring` → keyring
- `pygments` → Pygments (syntax highlighting, `ui/widgets/code_editor_ctrl.py`)
- `bs4` → beautifulsoup4 (scraper CSS selectors, `scraping/html_locate.py`)
- `lxml` → lxml (scraper XPath/parser, `scraping/html_locate.py`)
- `anthropic` → anthropic (the Claude API; imported only by `plugins/plugins/claude_ai/client.py` — relocated from `claude/client.py`, see `plugins/MAP.md`)
- `win32ctypes` → pywin32-ctypes
- `mysql` → mysql-connector-python
- `build123d` → build123d
- `OCP` → cadquery-ocp
- `pyassimp` → pyassimp
- `pyfqmr` → pyfqmr
- `ezdxf` → ezdxf
- `pyopencl` → pyopencl
- `pynvml` → nvidia-ml-py
- `amdsmi` → amdsmi
- `apple_smi` → apple_smi (Apple-only)

### Local tooling: LibreOffice (for xlsx skill recalculation)
LibreOffice is installed on this machine at `C:\Program Files\LibreOffice\program\soffice.exe` (not on `PATH`; `which soffice`/`where soffice.exe` find nothing).

**Why this matters:** The `anthropic-skills:xlsx` skill's `scripts/recalc.py` fails outright on this Windows machine with `Could not prepare the LibreOffice environment: module 'socket' has no attribute 'AF_UNIX'` — that script assumes a POSIX unix-socket connection to a headless LibreOffice instance, which doesn't exist on Windows Python. This isn't a missing-LibreOffice problem, it's the script's connection method being POSIX-only.

**Workaround that works:** run LibreOffice headless directly instead of the skill's `recalc.py`:
```
"C:\Program Files\LibreOffice\program\soffice.exe" --headless --calc --convert-to xlsx --outdir <out_dir> <file.xlsx>
```
This recalculates every formula and rewrites the file (into `<out_dir>`, same filename) with cached values, same effect as the skill's intended recalc step. Verify afterward with `openpyxl.load_workbook(path, data_only=True)` and scan cells for strings starting with `#` (formula errors) — confirmed clean on a real workbook (26-row CPI reweighting model, SUM/arithmetic formulas only) on 2026-08-20.

**How to apply:** Any time the xlsx skill is used on this machine, expect `recalc.py` to fail this way — go straight to the `soffice.exe --headless --convert-to` workaround rather than debugging the socket error or reporting "LibreOffice isn't available."

---

## User

### Background: hobbyist programmer, not a professional developer
Retired mechanic / home-improvement contractor, not a software engineer by trade. Builds `harness_designer` as a personal/hobby project, self-taught — explicitly said (2026-08-04) "I am a hobbyist programmer. I don't do this for a living."

**Why this matters:** Despite the "hobbyist" self-description, engages with genuinely advanced technical material at a high level — during a deep dive into PySide6's `QEvent` type system, correctly called out an overstated claim (that pre-C++11 C++ had no way to make one event class's type parameter reject another class's type value) from his own existing knowledge, confidently and without needing it verified for his own sake. Claude ran a `clang++ -std=c++98` compile afterward to check the claim before accepting it into the conversation/memory — the user explicitly clarified (2026-08-04) he already knew the answer, that's *why* he stated the correction, not because he was guessing and wanted it checked. Don't misattribute verification steps Claude takes to the user. Separately, the user does consistently push for empirical verification *from Claude* (real benchmarks, real compiler/interpreter runs, real DB queries) rather than accepting Claude's explanations at face value — see also Benchmarking discipline and Context-building conversations below.

**How to apply:** Don't dumb down technical depth, and don't assume unfamiliarity just because of the "hobbyist" framing — he may already know the answer with confidence even when raising something as a question or correction. Do explain unfamiliar CS/software-ecosystem vocabulary plainly when it comes up (e.g. had to ask what a `QGraphicsScene` is) rather than assuming formal-CS background — then engage at full depth once oriented. When *Claude* is the one asserting something verifiable (compiler behavior, library internals, performance), verify it empirically rather than assert from memory — but don't assume the user needs the same handed to him; he may already be confident and correct.

**Punctuation signals intent, usually (stated explicitly, 2026-08-04):** "I am usually pretty good at adding a question mark when I am asking a question vs making a statement." Followed immediately by his own caveat: "most of the time. I am human after all and I do make mistakes. LOL" — so treat this as a strong default, not an absolute rule. A message ending without a `?` is *usually* a statement he already believes, not an open question inviting verification — but he's told me directly this isn't infallible, so don't over-index on it for anything consequential. Punctuation is a signal for *intent* (is he telling me or asking me), not a certification of *correctness* — still apply normal judgment/verification to what he states, same as anything else.

Mechanical reason typos happen: 50 years old, types with 2 fingers on the left hand and 3 on the right (not full touch-typing), and looks at the keyboard while typing. Stray/garbled characters (e.g. "hu8man" for "human") are typing slips, not meaningful signal — read past them for intent rather than flagging them, unless a typo genuinely changes the meaning of a technical instruction.

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

### Soft "nudge" hooks get ignored — use hard blocks (exit code 2) to enforce tool-usage rules
Before building the `Grep`-blocking hook (`.claude/hooks/grep-interceptor.sh`), the user had already
tried a softer version of the same enforcement idea: `nudge_dep_trace.py`, a `PreToolUse` hook on
`Read` that returns `permissionDecision: allow` plus an `additionalContext` reminder rather than
stopping the call. Stated directly (2026-10-01): "the nudge thing I have tried already and you
ignore it." He also declined re-adding it (and its companions `session_start.py`,
`suppress_dep_trace_nudge.py`, `dep_trace_state.py`) when offered, saying he wants to "keep it
simple like what the Grep hook does."

**Why:** A nudge hook lets the tool call succeed and just appends advisory text — nothing actually
stops the action, so it's easy to proceed anyway once a task has momentum. A hard block (exit code
2) prevents the tool call from completing at all and surfaces the redirect as an error, which is
what actually changes what happens next.

**How to apply:** When asked to enforce a "use tool/approach X instead of Y" rule in this project
going forward, default to a blocking (`exit 2`) `PreToolUse` hook on `Y` — the pattern already
proven in `grep-interceptor.sh` — not an advisory/`additionalContext` nudge. Don't suggest
reviving the dormant nudge-style scripts in `.claude/hooks/`; he's already rejected that approach.

### Write down a detailed verbal spec immediately, don't trust it to survive context compaction
When the user works out a detailed multi-round design spec in conversation (e.g. the wire-drag Mode 1/2/3 rules — clarified over several back-and-forth messages, each answer narrowing the design), write it to a durable file (TODO.md, a plan file, or straight into the target module's docstring) as soon as it's settled, not just held in conversation.

**Why:** This exact spec was worked out in detail once, then lost entirely when the session's context got compacted — neither the spec itself nor even a note that it existed survived (confirmed by grepping TODO.md/MEMORY.md afterward: nothing). The user had to dig up their own copy of the transcript and re-paste the whole exchange to recover it. Confirmed 2026-08-08: "that was a rough one to explain the first time around and then having to do it a second time... but at least I got a clear description of what was wanted so you could design it properly" — a good outcome the second time only because they happened to still have the transcript; that's not something to rely on.

**How to apply:** The moment a multi-message clarification round converges on a concrete design (not just a one-line answer), capture it in writing before moving on to implementation — a TODO.md entry, a plan file, or a docstring on the relevant class/function. Don't wait until "right before implementing" if there's any chance of a long research/debugging detour first (the CullingThreadPool hang investigation above is exactly what intervened between this spec being given and it actually being implemented).

### QtWebEngine in the main window needs Qt Quick on OpenGL (2026-10-17)
`app.py`'s `QSG_RHI_BACKEND=opengl` setting and why it can't be removed is now documented in full
in `harness_designer/MAP.md`'s `app.py` entry — see there.

### A QLabel's minimum width is its longest unbreakable word -- use `WrapLabel` for text the app does not control (2026-10-17)
Full incident and rule now documented in `harness_designer/ui/widgets/MAP.md`'s `wrap_label.py`
entry — see there.

### Do not write unit tests (user, 2026-10-17)
Do not create `unittest` / pytest files, a `tests/` folder, or anything that exists only so a test can reach into the code (hook constants, test helpers). Build what was asked; check it with throwaway scripts in the session scratchpad (outside the repo), by reading the code, and say plainly what was and was not verified.

**Why:** Said directly, 2026-10-17: "I do not want unit tests written so if you wrote any you can delete them." Earlier the same day the user had already removed the whole `tests/` folder from the working tree and said not to worry about it ("if so don't worry about it not being there anymore"). The test files written for the scraper and Claude work were deleted; the Phase 1-2 and `claude/` suites remain only in git history.

**How to apply:** Never add test files, and delete any you find that you wrote. Design docs that mention tests for Phases 1-2 / `claude/` describe history. The rules about not touching the real Windows Credential Manager (it holds the user's actual key) and the live `Config` database still apply to scratch experiments.

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

**How to apply:** Whenever writing or editing a function signature, check every call site (or reasonable caller behavior) for what types/values actually get passed, including None, and make sure the hint covers all of them. **Exception (user, 2026-10-22): `harness_designer/check_types.py`** -- only the signature of `do` (and of `logfunc` in `harness_designer/debug.py`) carries a hint, the ParamSpec form `Callable[_P, _R] -> Callable[_P, _R]`; everything else in `check_types.py` and everything behind `logfunc` (`_logfunc` and its `_wrapper`) is deliberately unannotated, so type checkers keep every decorated function's real signature through the decorators (see the `check_types.py` entry under Architecture notes).

**What Cython 3.2.4 really enforces, probed against the real compiler (2026-10-21; mypy is blind to all of it because it follows PEP 484, and a run from source never fails -- only the compiled build does):**
- `tuple`, `list`, `dict`, `set`, `frozenset`, `str`, `bytes` -- also `list[...]`, `tuple[int, int]`, etc., and any `X | None` -- get an **exact-type** check. Subclasses are rejected too (Cython's own message says it is "deliberately stricter than PEP-484"): a `NamedTuple` for `tuple`, a `defaultdict`/`OrderedDict` for `dict`, a str-`Enum` for `str` all raise. `None` raises unless the hint includes `| None`.
- A union of two or more non-None types (`tuple | list | None`) generates **no check at all**; so do `Any`, `object` and user classes.
- `int` / `int | None` / `float | None` first convert any number (`PyNumber_Long`/`PyNumber_Float`): numpy scalars and ints-for-float are fine, but a float passed to an `int` parameter is **silently truncated**, and only non-numbers raise. Bare `float` converts to a C double; `bool` is a truth test.
- Real incidents: `execute(params: tuple | None)` on four wrappers while 14 call sites passed lists (the part-search, peg-board housing drop and compat-part lookups all crashed), and `SetFileTypes(file_types: str)` on three property controls that are handed a dict.
- `python diagnostics/cython_hint_audit.py` is that scan (see `diagnostics/MAP.md`). Run it after changing a signature's hint or adding calls to a compiled-checked parameter. It resolves call targets through `self`/`super()`/function names/DB-wrapper receivers and infers argument types from literals, builtin calls, locals, `self.x` and `a, b = self.method()` returns. After those fixes it found no other definite mismatches -- everything left was a `None`-union false positive (guarded or assigned just before the call). It cannot see arguments typed by another object's return value, callbacks/Qt slots, or subclass instances built elsewhere, so "none found" is not proof.
- Runtime counterpart (2026-10-22): `check_types.do` (its settings are the constants at the top of `harness_designer/check_types.py`, which the user edited -- leave them) verifies every annotated parameter and return value at run time and writes ONLY what does not fit into `type_audit.sqlite3` (repo root; `HARNESS_TYPE_AUDIT_DB` overrides): table `functions` (name, signature, return type, source file, line) and table `calls` (calling function, file, line, signature of the call as made, type returned). Run the app from source, exercise the editors, then `python diagnostics/type_audit_report.py` prints the two side by side. It catches what the static scan cannot see (callbacks, Qt slots, `CallAfter(fn, *args)` forwarding, dynamic receivers) but only for code that ran. It runs from source only, never compiled, so do not build or test `check_types.py` compiled. A call is written only if no row has the same function (name + source file), calling function, calling file, signature and return type; wrong calls go into an in-memory SQLite database that is dumped to the file every `_FLUSH_SECONDS` and at exit, so the app's worker processes and later sessions add to the same file without repeats. Delete the file to start over.

### Type hinting conventions: typing module, Union vs `|`, quoting, TYPE_CHECKING imports
Several related rules govern how type hints are written in this codebase (updated 2026-07-28, supersedes any earlier looser guidance on quoting):

- **Minimize use of the `typing` module for builtins.** Use bare builtin generics (`tuple[float, float]`, `list[int]`, `dict[str, int]`) — never `typing.Tuple`/`typing.List`/`typing.Dict`/etc.
- **`Optional` is NEVER to be used**, full stop. Use `X | None` (preferred) or `Union[X, None]` (only when forced — see below).
- **`|` is preferred over `Union`** for unions in general. Only fall back to `Union` (imported as `from typing import Union as _Union`) when using `|` would force a quoted string annotation — i.e. when the type on one side of the `|` is only available via a `TYPE_CHECKING`-guarded import and quoting the whole `X | None` expression as one string would otherwise be the only option.
- **Quotes must NEVER wrap a builtin.** Never write `"tuple[float, float]"`, `"int"`, `"None"`, etc. — always bare. This includes never quoting an entire `SomeClass | None` expression just because `SomeClass` needs deferral — quote only `SomeClass` itself, and only inside a `Union[...]`, never bare-string with `|`.
- **If a module is imported only for typing purposes, guard the import with `if typing.TYPE_CHECKING:` and import the *module*, not the type/class directly** — e.g. `from . import somemodule as _somemodule`, then reference `_somemodule.SomeClass` in the annotation. Always alias the imported module with a leading single underscore (`_somemodule`), not the bare module name.
- When such a `TYPE_CHECKING`-only module reference needs to appear in a union with `None` (or anything else), use `_Union["_somemodule.SomeClass", None]` — quote only the module-qualified class reference, use `Union` (not `|`) for the union itself, never quote the whole expression as one string.
- **`*args`/`**kwargs` get their own convention, distinct from normal per-element variadic-arg typing** (confirmed 2026-09-23): annotate `*args: tuple[Any]` and `**kwargs: dict[str, Any]` — the annotation describes the *collected* container (a tuple / a str-keyed dict), not "the type of each individual argument" the way `*args: int` would read under ordinary PEP typing. Needs `from typing import Any` (and `Any` is the one `typing` member exempt from the "minimize typing module" rule above, since it has no bare-builtin equivalent). This only applies to genuine open-ended passthrough `*args`/`**kwargs` (decorators, `CallAfter`/`CallLater`-style callable-forwarding helpers) — a variadic parameter with a real, specific element type (e.g. `Color.Set(self, *RGBA: int | float)`, actual RGBA channel values) keeps its normal per-element type, unaffected by this rule.
- **`__init__` has NO return annotation** (decided 2026-10-23, after trying the class name and `Self`). Not `-> None`, not the class name, not `-> Self`. The class name is wrong for a subclass that does not override `__init__`. `-> Self` (`from typing import Self as _Self`) is rejected by the type checkers -- mypy: 'The return type of "__init__" must be None' and 'Missing return statement'; basedpyright: 'Return type of "__init__" must be None' -- and changes nothing about what `Cls(...)` is inferred as. Parameters keep their hints. `Self` as `_Self` stays right for methods that really return the instance (the `Point` / `Angle` / `Quaternion` operators, `CanvasBase`). `check_types.do` never checks or reports an `__init__`'s return. A 693-file codemod removed the annotations (2026-10-23); `builder/` and `diagnostics/` were left as they were (their interpreter can be 3.10).
- **A parameter or return that is a config CLASS (`Config.editor_3d`, not an instance of it) is annotated with the aliases at the end of `config.py`** (decided 2026-10-23): `ConfigType`, `ConfigEditor3DType`, `ConfigEditorSchematicType`, `ConfigEditorPegboardType`, `ConfigAxisOverlayType`. Under `TYPE_CHECKING` each is the config class itself, so the IDE completes `config.` with that section's settings; at run time each is `ConfigDB` (the metaclass every `Config.*` class has), which is what `check_types.do` compares against. Writing `Config.editor_3d` as the hint says 'an instance of it' and the recorder flagged every call. The dialogs that embed a 3D canvas (`part_orientation.py`, `transition_editor/dialog.py`, `housing_editor/config.py`) hand it their own stand-in `_Config` classes; those are `ConfigDB` classes (`metaclass=ConfigDB`) whose qualified name has a leading underscore, so `__persisted__` keeps them out of the database and the run-time check accepts them. A stand-in MUST keep the underscore: without it its table name would collide with the real editor's (`Config.editor_3d` -> table `editor_3d`) and the stand-in's values would be written over the user's settings.
- **Config editor classes share a placeholder base** (2026-10-23): `_ConfigEditorBase` in `config.py` holds a type-inference snapshot of what `editor_3d` / `editor_pegboard` / `editor_schematic` have in common (settings and, recursively, the shared `ConfigDB` sections); the editors subclass it instead of using `metaclass=ConfigDB`, and each shared section subclasses the base's (`class lighting(_ConfigEditorBase.lighting)`). Values in the base are placeholders, never defaults the app relies on. Anything whose `__qualname__` has a period-separated section starting with `_` is NEVER stored (`ConfigDB.__persisted__`): no table, no rows. If you add a setting that all three editors have, add a placeholder for it to the base too; The base's `floor.reflections` and `input.*` classes are plain placeholders, so an editor that stores one adds `metaclass=ConfigDB` to its own subclass (`class zoom(_ConfigEditorBase.input.zoom, metaclass=ConfigDB)`) and one that does not leaves it plain. Stored today: `editor_3d` has all of them; `editor_pegboard` and `editor_schematic` only `input.truck_pedestal`, `input.zoom` and `input.reset` (their `input.dolly` is all `None` and is not stored; their live wheel-zoom settings in `input.zoom` are). Every placeholder is annotated with its type (`X | None` where an editor leaves it `None`). `sensitivity` and `speed` are always plain `float` (the 2D editors' unused ones are `0.0`, not `None`) so the shared canvas code can do arithmetic on them. The base canvas config parameter is `_config.ConfigEditorBaseType`.
- **Cython comes first, mypy is advisory** (user, 2026-10-23): the point of the hint work is that the compiled build runs without Cython raising and that `check_types` stops flagging real calls. mypy only helps find suspects; when a hint is right for Cython and the recorder but mypy complains (`BaseVar.position -> Point | None` adds ~100 mypy errors in callers and is still correct: position-less placeholder objects exist), keep the hint and ignore mypy. Checked with a real MSVC build (Cython 3.2.4): a parameter hinted with an exact builtin (`frozenset`, `tuple`, `list`, `dict`, `set`, `str`, `bytes`) raises `TypeError` for any other type (`frozenset` <- `set`), but a UNION (`frozenset | set`, `tuple[...] | list`, `float | None` <- `Decimal`), a class hint, a `None` hint and every `def` / property return annotation are not enforced. Element counts in a hint (`list[float, float, float, float]`) are ignored by Cython and rejected by mypy: write `list[float]`. So when the recorder shows a builtin-typed parameter receiving another type, WIDEN THE HINT to a union; a wrong class hint is only documentation.
- **Default to a `TYPE_CHECKING`-guarded, quoted forward reference for any cross-module class-type annotation — do not spend time checking whether the import would actually be circular first** (settled 2026-09-24, after empirically verifying the reason this used to matter no longer applies — see next entry). The quoted/deferred form is the default; only hoist an import to real/unquoted module level for reasons unrelated to typing (e.g. the module is already needed at runtime in that file for a non-typing reason).

### Quoted forward-reference class annotations cost nothing under Cython — verified empirically (2026-09-24)
Confirmed by direct Cython compile comparison (not reasoning from docs): for a **plain Python class** (`class Foo:`, not `cdef class`) — which is what every class in this codebase is (`Point`, `Angle`, `Wire`, `MainFrame`, `Project`, etc.) — a quoted `TYPE_CHECKING`-deferred forward reference (`x: "_mod.Foo"`) and a real unquoted import (`from mod import Foo; x: Foo`) generate **byte-for-byte identical C code**: no `ArgTypeTest`, no optimized attribute access, both just a generic `PyObject*` with plain `PyObject_GetAttr` calls. Tested both as a function parameter and as an annotated local variable reassigned to an incompatible type (`x: Foo = Foo(); x = Bar()`) — neither the quoted nor the unquoted version raised a compile warning or inserted a coercion check; both compiled clean and stayed fully dynamic.

**This does NOT extend to builtins/primitives** — `int`, `float`, `str`, `bool`, and typed containers like `list[float]` DO get a real Cython-native C-level type (confirmed separately, matches the pre-existing `Camera2D.zoom_at_point` bug where a `delta: float` local reused for a `Point` value crashed post-compile with a coercion `TypeError`). The existing "quotes must never wrap a builtin" rule is exactly about protecting that real mechanism — unaffected by this entry, still critical.

**Why the class-typing question came up at all:** the actual "app crashes on a wrong-typed parameter" behavior the user described is `check_types.py`'s own `@_check_types.do` decorator — a Python-level `isinstance` check applied via decorator at ~6179 call sites, completely independent of Cython's native typing. (Separately: as of 2026-10-22 that checker is gone -- `do` is now the runtime type recorder; see the `check_types.py` entry elsewhere in this file.)

**How to apply:** Keep writing `TYPE_CHECKING`-guarded, quoted forward references for cross-module class types as the default/preferred style (per the entry above) — it costs nothing at the Cython level and keeps the IDE/static-analysis benefit. Don't treat "does this risk a circular import" as a reason to skip the guard; the guard is the default regardless.

**Third category found 2026-10-19, NOT covered by the empirical test above: raw third-party C-extension types used directly (PySide6/Qt classes — `QSize`, `QColor`, `QPixmap`, `QHBoxLayout`/`QVBoxLayout`, `QPoint`, etc. — not subclassed by this project, used as-is) DO get real fixed-type coercion, same risk class as builtins/containers.** User hit a real runtime crash reassigning a `tuple[int, int]` to a variable holding a `QSize`. This is distinct from "a harness_designer class that happens to subclass a Qt type" (e.g. `MainFrame(QtWidgets.QMainWindow)`) — the SUBCLASS itself is still a plain Python class for this purpose and remains safe per the entry above; it's specifically using the raw upstream Qt/Shiboken type directly (not wrapped in one of this project's own classes) that's risky. Full audit of this exact pattern across the whole codebase is in `CYTHON_REASSIGNMENT_AUDIT.md` (repo root, not committed) — ~30 confirmed true positives spanning SQL-helper list→str joins, numpy ndarray↔class mixes, and raw-Qt-type mixes (`QColor`→this project's `Color` class, `QPoint`→`int`, `QHBoxLayout`→`QVBoxLayout`, etc.), plus a documented false-positive list (PySide6 `Signal()`/`SignalInstance` idiom, `LazyTabMixin` base-vs-subclass attribute narrowing, `self.size`/`.context`/`.x`/`.y`/`.window` shadowing inherited Qt methods, bare unannotated locals).

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

### Import block ordering (confirmed 2026-09-23)
Every module's top-of-file import block follows a fixed group order, each
group separated by one blank line, in this order:

1. Typing-only imports — `from typing import ...` and `from collections.abc
   import Callable`/other ABCs used purely for type hints.
2. Non-local imports — stdlib and third-party (`os`, `threading`, `numpy`,
   `PySide6`, etc).
3. Local (in-project) imports — `from . import x` / `from .sub import y`,
   including `import harness_designer` itself when a submodule needs the
   top-level package.

If the module has a `TYPE_CHECKING` block, it goes after the three groups
above, separated by **two** blank lines (not one), and is followed by
**two** more blank lines before the rest of the module. Example shape:

```python
from typing import TYPE_CHECKING, Union as _Union
from collections.abc import Callable

import os
import threading
from PySide6 import QtCore

from . import config as _config
from . import check_types as _check_types

if TYPE_CHECKING:
    from . import logger as _logger

<rest of module>
```

No `TYPE_CHECKING` block: it's just the three groups, one blank line
between each, with the rest of the module following normally (no forced
double blank line since there's no `TYPE_CHECKING` block to separate from).

**How to apply:** When touching a file's imports for any reason (adding one,
moving a local import to module level, fixing a PySide6-depth violation),
bring the whole import block into this shape while there, not just the line
being changed.

### PySide6 imports: never more than one layer down
Anything imported from PySide6 must be imported at most one layer down — import the submodule (`QtCore`, `QtWidgets`, `QtGui`, ...), then reference names off it. Never import a name directly from a PySide6 submodule.

Not OK:
```python
from PySide6.QtCore import Signal

x = Signal(...)
```

OK:
```python
from PySide6 import QtCore

x = QtCore.Signal(...)
```

**How to apply:** Any `from PySide6.QtXxx import Something` is wrong — rewrite as `from PySide6 import QtXxx` plus `QtXxx.Something` at each use site. This applies throughout the codebase, not just new code — flag it when seen in passing.

### Cython variable type reuse
Never reassign a type-annotated parameter/variable to a value of a **different type** in the same function. Works fine interpreted (dynamic typing), but crashes only once Cython-compiled — Cython gives the variable a fixed C-level storage type from the annotation, and reassigning to an incompatible type triggers a coercion failure.

**Why:** a camera class's `zoom_at_point` reused `delta: float` for a later `Point` value (`delta = world_pos_before - world_pos_after`) — this predates the `gl/canvas2d` → `gl/canvas_base`+`canvas_schematic`+`canvas_pegboard`+`canvas_3d` rename (see `gl/MAP.md`), so don't trust an old mention of `canvas2d`/`camera.py` as a current path. Ran fine interpreted; crashed post-compile with `TypeError: must be real number, not Point`. Fixed by giving the Point-typed value its own name (`focal_delta`).

**How to apply:** Never reuse a parameter or annotated-variable name for a different type later in the function body, even though it "works" when run as plain interpreted `.py`. If debugging a report where dynamic-Python testing shows no problem but the user reports a live crash, ask whether the crash only happens in a Cython-compiled build before looking elsewhere.

### Concrete return types are load-bearing for Cython — never weaken to a base/abstract type
Every `@property` return type, `__iter__` yield type, and `__getitem__` return type must name the
**most specific concrete class**, not a base class, abstract type, `TypeVar`, or `Generic`. The
whole codebase compiles to C extension modules via Cython for release builds; Cython uses concrete
type annotations to emit statically typed C, and if a hint is generalized, Cython falls back to
plain Python object boxing for that value, silently losing the compiled build's performance
advantage — no error, just slower code.

**How to apply:** A refactor that "reduces boilerplate" by moving a typed method into a base class,
or that widens a return type to a shared ancestor for API-surface reasons, can quietly destroy
Cython's ability to specialize that method — check whether the concrete type information survives
before doing either. `TYPE_CHECKING` blocks are unaffected (Cython ignores them at compile time);
this only bites real runtime annotations on hot paths.

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

**Singleton-cache short-circuit before an existence-check query:** Every DB entry class (`PJTCavity`, `PJTHousing`, `Cavity`, `Housing`, etc.) is a per-`db_id` singleton via its metaclass (`_PJTEntrySingleton` in `database/project_db/pjt_bases.py`, `_EntrySingleton` in `database/global_db/bases.py`) — the same Python object is always returned for the same id, tracked in `cls._instances` as `db_id -> weakref`. Both metaclasses now implement `__contains__` (`db_id in cls._instances and cls._instances[db_id]() is not None`), and every table's `__getitem__` checks it first: `if item in PJTCavity or item in self:` (`item in self` is the fallback DB `SELECT id ... WHERE id=?` existence check). If the row's Python wrapper is already alive, this skips the query entirely. Confirmed 2026-08-20 across all 26 `project_db` tables and all 41 applicable `global_db` tables (excluding `setting.py`/`resource_state.py`, which don't fit the pattern — see below). The user's own assessment, unprompted: "I think this is actually a fantastic upgrade because it will reduce database hits by possibly 1000's of queries, even getting into 10's of thousands for really large projects" — validates this as a real, load-bearing perf win, not just a style nit.

**How to apply:** When adding a new entry-class table's `__getitem__` (or reviewing an existing one), always add the `item in EntryClass or item in self` short-circuit, matching every other table in both `project_db`/`global_db`. Skip it only when the lookup key isn't the row's own `db_id` (e.g. `resource_state.py`'s composite `(resource_type, resource_id)` key, resolved only *after* the query already ran) or when `__getitem__` doesn't construct/return an entry instance at all (e.g. `setting.py`, which returns a raw column value).

### Cython extensions (.pyx): compile and place the binary after every change
When a `.pyx` is added or edited, compile it and put the binary where the package imports it -- next to the source (e.g. `wire_routing/astar.cp311-win_amd64.pyd`) -- so tests can import it right away. Directed 2026-09-20. The binary and the generated C are gitignored (`*.pyd`, `harness_designer/**/*.c` in `.gitignore`); only the `.pyx` and its `.pyi` stub are tracked. Hot loops belong in a `.pyx` (integer math, `malloc`'d C arrays, `nogil`), not in compiled `.py` -- explicit instruction: "don't compile the python code as an extension module, write the code in cython instead."

**Interpreter: always `C:\python3.11.14\python.exe` (in bash: `/c/python3.11.14/python.exe`) -- for EVERYTHING, not just the compile:** edit/patch scripts, tests, benchmarks, `py_compile`, all of it. The `python` on PATH is 3.10 (Windows codepage default, chokes on UTF-8 files like this one) and must not be used. Directed 2026-09-20.

**How:** with cwd at the repo root and `PYTHONPATH=.`, run it (Cython 3.2.4; MSVC 2022 present) with `builder.msvc_env.activate()`, then `builder.cython_build.cythonize_to_c([(dotted_name, pyx_path)], build_dir)` with `build_dir` OUTSIDE the repo (so no `.c` lands in the tree), then `builder.compiler.compile_one(dotted_name, c_path, out_pyd, obj_dir, [compiler.python_include_dir()])` with `out_pyd = <pyx dir>/<stem> + compiler.ext_suffix()`. `PYTHONPATH=.` matters: that interpreter has a stale installed `harness_designer` in site-packages that otherwise shadows the repo. Repo conventions for a `.pyx`: the `# cython:` directive header (see `culling.pyx`/`bvh.pyx`) and a `.pyi` stub beside it. The user's own `build.py` also builds everything in place.

**Compile flags (decided 2026-09-20):** for local builds add speed flags on top of the builder's `/O2 /GL /DNDEBUG /MD`: `/Ob3 /Ot /Oi /Gy /GS-` and, at link, `/OPT:REF /OPT:ICF` (keep `/LTCG`). **Do NOT use `/arch:AVX2`** (the user removed it: it makes the binary CPU-specific and measured no gain -- `astar` is scalar/branchy, unchanged at ~0.53 s per 100-wire frame; `culling` gained only ~3-5%) **and do not use `/fp:fast`** (no gain over that, and it loosens float semantics). Measured on `astar` and `culling` -- a flag change is worth keeping only if an A/B run shows it. The `.pyd` files already on the user's machine were built with AVX2 and were deliberately left as they are. If a binary won't replace ("Device or resource busy"), the user's app is running and has it loaded -- ask them to close it, never force it; and note a silent failed `cp` makes an A/B benchmark measure the old binary twice.

**Fallback:** `routing.py` imports `astar` in a try/except and falls back to its pure-Python `_astar_py`, which is also the reference to check the compiled result against.

**Also register every new hand-written `.pyx` in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS` -- the ad hoc local compile above is NOT enough on its own.** Found 2026-09-30: `wire_routing/astar.pyx` had been missing from that list since it was written. `discover_modules()` only auto-walks plain `.py` files for cythonization; a hand-written `.pyx` not in that explicit tuple is invisible to the packaged wheel build (`wheel_build.py`'s own `_stage_assets` even explicitly skips copying `.pyx` sources as plain assets). Since the locally-compiled `.pyd` is gitignored, a from-scratch/CI wheel build had been silently shipping with no compiled `astar` extension at all, falling back to the slow pure-Python `_astar_py` in production -- nothing short of reading that one list would reveal it. Fixed by adding `astar.pyx` there alongside the pre-existing `bvh.pyx`/`culling.pyx` entries, and the new `rope_pull/rope_pull.pyx` was added to the same list the day it was written, not after the fact.

**How to apply:** whenever a new `.pyx` is written (whether or not it has a pure-Python fallback), add its path to `_HAND_WRITTEN_EXTENSIONS` in the same change, not as a follow-up -- the ad hoc dev-time compile-and-place-the-.pyd step makes it work locally, but says nothing about whether a clean packaged build will ever compile it.

### SQLite runs in WAL mode (decided 2026-09-20): commits cost per COMMIT, not per row
Full writeup now in `harness_designer/database/db_connectors/sqlite_connector/MAP.md`'s
`connector.py` entry — see there. One line worth keeping visible here since it applies app-wide:
there is ONE connector for the whole app (parts catalog `GLBTables` and project `PJTTables` share
the same file/connection), so this is app-wide, not project-only.

**How to apply:** when a hot path (mouse-move handlers, drags) writes to the DB, the cost driver is the NUMBER OF COMMITS, so batch writes into one `batch_update` (see `PJTHousing._update_position2d`, `reroute.apply_shifts`) rather than one write per row. Measure with a real commit loop before assuming a batch was the fast one -- an earlier test here looked 50x faster by accident because it rewrote unchanged values.

### Rotation matrix convention
`Angle.as_matrix_numpy` returns the **column-vector** rotation matrix `R` where `R @ v` rotates a column vector, but the rest of the codebase applies rotation in **row-vector** convention (`v @ R.T`) via numpy `@`. Full rule, the `MeshSurfacePicker` bug this caused, and how to apply it in a new transform cache are now in `harness_designer/geometry/MAP.md` (and `geometry/angle/angle.py`'s entry in `geometry/angle/MAP.md`) — see there.

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

### Point/Angle callback system is THE architectural backbone — default to it for any new reactive behavior
The user (sole author) stated directly and emphatically (2026-08-17): "the whole callback system I designed for the angles and the points was a genius way to go about it. it is literally the backbone to this entire program." Full writeup — the mechanism, confirmed real-world reach, and the default-to-this-first rule — now lives in `harness_designer/app_mixins/MAP.md`'s `callback_mixin.py` entry and `harness_designer/geometry/MAP.md`; see there.

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

### Don't let a designed-but-deferred piece of work silently drop
When a multi-step design gets worked out in detail (e.g. the `smooth` tri-state getter/setter pattern — resolve `None` against a per-type `Config.editor_X.renderer.smooth_Y`, needed on every view class backed by a `smooth` DB column) but the conversation immediately pivots to a different task before it's implemented, it's easy to build the *prerequisites* (config fields, in this case) and then never circle back to the actual implementation once focus shifts. The user caught this directly (2026-08-20): "you were supposed to have overridden the smooth getter and setter in ALL of the object view classes... " — it had been fully speced turns earlier but silently never got built once the housing/cavity/terminal AABB work took over.

**Why:** Long, multi-topic sessions make it easy to lose track of a committed-to piece of work that isn't the *current* topic — especially dangerous when it's a real correctness/crash risk (this one reintroduced the exact `int(None)` crash from the session's original bug reports, now live again on objects that were otherwise just fixed).

**How to apply:** When a design is agreed upon but not immediately implemented (deferred for a legitimate reason, e.g. the user wants to keep going on something else first), explicitly track it as still-open (TODO.md, or a running mental checklist) and surface it again before declaring a broader task "done" — don't let scope drift silently swallow a committed piece of work. When asked "is there anything else we missed," this is exactly the category of thing to check for first.

### Config is a live DB, not a fixture
`Config.*` writes through to the real `%APPDATA%\HarnessDesigner\config.db` on every non-underscore
attribute assignment — indistinguishable from a change made through the running app. **Never read
from or assign to `Config.*` in a throwaway script, and never run more than one process concurrently
against the same (real or shared-scratch) app-data directory.** This also fires on a bare
`import harness_designer` (`Config.open()` and the logger singleton both run at import time) —
sandbox `USERPROFILE`/`HOME` to a scratch directory before running anything that imports this
package at all, even just to check it doesn't crash. When delegating a task that runtime-tests GL
canvases/editors/config-backed UI, explicitly instruct the agent not to exercise code paths that
read/write live `Config.*`, or to restore any value it changes before finishing (a past agent's
`Canvas.set_grid_snap`/`set_grid_display` smoke test wrote straight into the live config.db and had
to be fixed by hand — the permission system blocked its own cleanup attempt). Full incident history
(the log-rotation corruption that prompted this rule) is in `harness_designer/MAP.md`'s `config.py`
entry.

### Silent crash debugging
When the app dies with **zero diagnostics** (no Python traceback, nothing in the log, no console output), that pattern means a genuine native/C-stack-level crash, not a normal Python exception — this codebase compiles to Cython C extensions, and deep Python recursion doing real work per frame (e.g. a DB query) can blow the C stack before Python's own `RecursionError` trips.

**Confirmed root cause pattern (2026-07-10):** two `@property` getters on the same DB row wrapper class calling each other — `PJTTerminal.is_start` checked `self.load`, and `PJTTerminal.load` checked `self.is_start` right back, guaranteeing infinite recursion whenever the raw `is_start` column was truthy (the schema default for every new row). Triggered by `PJTCavityControl.set_obj` eagerly loading a terminal's property tab whenever a cavity has one.

**How to apply when hunting a silent crash:**
1. Consider whether it's new-code-specific first, but don't over-anchor if the user says otherwise.
2. When the user names specific files, carefully read that file's `@property` getters for cross-references — grep for `if self\.\w+` patterns and trace whether any two properties call each other.
3. Eager (non-lazy) property-panel loading (e.g. unconditional `set_obj` calls unlike the `LazyTabMixin` pattern used elsewhere) turns a merely-buggy property into an immediate crash-on-select — worth checking which `set_obj`/`_load_tab` call sites are eager vs. lazy when a crash correlates with "selecting X."

### Don't run overlapping background test processes for this app
When verifying anything that imports `harness_designer` (or runs it) via Bash/PowerShell background tasks, run **one at a time** and wait for it to actually finish before starting another.

**Why:** During the check_types.do rollout (2026-07-30), several overlapping `import harness_designer` verification runs were launched in the background to chase down a suspected hang. Each one independently constructed a `LogHandler` against the same real (or shared scratch) log directory, causing file-lock contention that looked exactly like an unrelated deadlock and burned significant time misattributing the symptom before the real cause (an actual bug, see check_types.py entry below) was found. Some of the resulting stray processes couldn't be terminated from within the sandbox (`Stop-Process`/`taskkill` returned Access Denied even though owned by the same user) and didn't show up in the user's own Task Manager either (a different process/session view than the sandbox) — the user ultimately had to intervene manually to clear one.

**How to apply:** Never fire multiple concurrent background Bash/PowerShell test runs that import or launch this app. If a background verification run appears to hang, don't just launch another one to investigate — check on the existing one first, and treat "access denied" on a kill attempt as a sign the sandbox can't reach that process, not as a reason to spawn more of them.

### Don't launch the app yourself
Never launch (or relaunch, close/kill) the `harness_designer` Qt desktop app via Bash/PowerShell to "verify" a code change. Make the edit, tell the user what to check, wait for them to run it and report back.

**Why:** During 2D schematic editor work, repeatedly relaunching the app in the background after each small edit annoyed the user ("stop running it!!!"). Trying to stop/check for the running process afterward was ALSO wrong — the user hadn't asked for that either ("I didn't tell you to close it!!!"). The user manages the app's process lifecycle themselves.

**How to apply:** Never call `run.py` (or the app's entry point) via Bash/PowerShell to check a UI/rendering change, and never kill/stop a running instance on your own initiative. This is a native Windows GUI app with no screenshot/automation tool available, so launching it wouldn't even allow visual verification — it only produces console output for import/syntax errors, which `python -m py_compile` already covers without touching the running app. Use `py_compile` (or equivalent static checks) for pre-flight verification, then hand off to the user for the visual check.

**Exception — don't reflexively `py_compile` mid-refactor scaffolding either (2026-08-12):** While the user is actively building out a new module in stages (e.g. `gl/new_canvas_base/`, worked on file-by-file with other files deliberately left unfinished/unwired), don't run `python -m py_compile` or similar verification passes on it after each edit by default. Explicitly rejected: "I am not worried about compile checking right now as it may fail because of other things that still need to be updated." A failure there wouldn't signal anything wrong with the edit just made — it's expected noise from other pieces intentionally not built yet (missing config sections, `__init__.py` pointing at not-yet-renamed modules, etc. — see the `new_canvas_base`/`new_canvas2d` entries above). Only compile-check such in-progress work if the user asks, or once they've indicated a module is meant to actually run standalone.

### When a bug is "goofy and hard to explain," add live diagnostic prints before reasoning further
For a visual/behavioral bug the user can't precisely describe in words (intermittent, angle/position-dependent, "sometimes right, sometimes not"), repeated rounds of code-level reasoning and offline synthetic reproductions are a weak substitute for real captured runtime data — add targeted `print()` diagnostics at the suspect boundary and get the user to run the app and paste real output.

**Confirmed case (2026-08-26):** the rotation-ring protractor's degree labels sometimes rendered ~90-120° rotated when viewed obliquely, "depending on the angle and how far the camera is." Several rounds of pure reasoning (checking for gimbal lock, auditing the camera "eye vs. focal position" naming, tightening/blending the billboard's up-reference degenerate-case threshold, verifying the billboard math numerically offline) each produced a real, defensible improvement but never found the actual bug — because the actual bug (`Angle.from_matrix`'s sign-canonicalization step calling `Quaternion.__neg__`, which computes the *inverse*, where it needed plain four-component negation instead — see the Angle/Quaternion entry below) only reveals itself in real data: printing the camera position and every label's world position + current quaternion, every render() frame, and having the user paste output from the moment the bug was visibly happening, showed a live discontinuity between two adjacent labels' quaternions that a hand-derived or synthetic test never reproduced. Reconstructing that exact real matrix offline (not a synthetic one) and testing it through `Angle.from_matrix` is what surfaced the bug directly. The user's own assessment: "adding the debug prints what the right move to locate where the issue was."

**How to apply:** When a bug report is hard to pin down verbally, or when 2+ rounds of code-reasoning-driven fixes haven't resolved a report the user says is still happening, stop guessing further and add print statements at the actual computation boundary (inputs and outputs, every frame/call if the bug is per-frame) — then ask the user to reproduce the bad state and paste the console output from that exact moment. Prefer this over another synthetic/offline reproduction attempt once reasoning has already produced 2+ non-fixes; synthetic tests only probe the hypothesis already in mind; real captured data can reveal a hypothesis was never considered at all. Remove the temporary prints once the root cause is confirmed and fixed — don't leave them in.

### `Angle`/`Quaternion` negation vs. inverse — two different operations, easy to conflate
`inverse()`/`__neg__`/`conj()`/`negation()` are four related-but-different operations across
`angle.py`/`quaternion.py` — easy to reach for the wrong one (the `Angle.from_matrix` canonicalization
bug is the cautionary example). Full breakdown now in `harness_designer/geometry/angle/MAP.md` — see
there before using any of them interchangeably.

### Never use `getattr()`/`hasattr()` as a way to control code flow
Don't reach for `getattr(obj, 'attr', default)` or `hasattr(obj, 'attr')` to decide which of several duck-typed code paths to run. Use a real `isinstance()` check against the concrete type(s) involved, and if a shared method needs to exist on every branch, add a real (even if no-op) method to the common base class so it's always callable.

**Why:** The user's own words: "I dislike using getattr as a way to control the flow of the code. The reason why is because it breaks type hinting and autocomplete in an IDE and it can also mask an error." `getattr(x, 'render', None)` silently returns `None` (and gets treated as "nothing to do") for a typo'd attribute name, a renamed method, or a genuinely-wrong object just as readily as for an intentional "this type doesn't have it" case — an IDE/type-checker can't warn about any of it, since the string key isn't statically checked at all.

**Confirmed case (2026-08-26):** `Base3D.render_handler`/`BaseSchematic.render_handler`/`BasePegboard.render_handler` (added as part of the rotation-gizmo/drag-arrows depth-testing fix — see the render_handler architecture notes elsewhere in this file) were first written as `target = getattr(self._active_handler, 'objN', self._active_handler); render = getattr(target, 'render', None); if render is None: return`. Rejected and replaced with `isinstance(self._active_handler, RotationRings)` (matching the codebase's own existing precedent in `handle_interaction`) to pick the right branch, plus a real no-op `DragHandlerBase.render()` default (overridden by `DragHandler3D` with actual logic) so the non-rotation branch can call `.render(shaders)` directly and unconditionally, with full type-checking support.

**How to apply:** When code needs to branch on "which concrete type is this," use `isinstance()` against the actual classes. When code needs "call this method whether or not this particular subtype has anything real to do," give the common base class a real method (a documented no-op default is fine) instead of probing for the attribute's existence at the call site.

**Check `ObjectBase` for an `is_X` property before reaching for `isinstance`/`hasattr` at all (confirmed 2026-09-23):** `objects/object_base.py`'s `ObjectBase` already exposes real `@property` type checks for most concrete object kinds — `is_wire_marker`, `is_wire_service_loop`, `is_wire_layout`, etc. (each just `isinstance(self, ConcreteClass)` under the hood, done this way instead of a bare `isinstance` call site so the concrete class doesn't need importing everywhere). `drag_handlers/editor_3d/generic.py`'s `Generic.__init__`/`delete` originally used `hasattr(target.obj3d, 'begin_move_session')` to detect a `WireServiceLoop3D` — fixed to `target.is_wire_service_loop` instead, on the wrapper object (`target`), not the view-specific `obj3d`. Grep `object_base.py` for `is_` properties before writing a fresh `isinstance()` check or, worse, a `hasattr` guard.

### When the user names the exact fix, stop investigating and implement it
If the user has stated a specific root cause and a specific fix approach ("mimic the code in X function," "there's no need for Y to happen elsewhere"), don't keep cross-checking it against other files/call sites/theories before acting — implement what they described.

**Confirmed case (2026-09-11):** while debugging a cavity-name-position bug, the user correctly identified that `update_cavities()`'s fallback cavity-creation branch should be unreachable by design ("cavities are added when a housing is added, there is no need for them to be added elsewhere") and pointed at the exact guard clause proving it. Continuing to search for corroborating/contradicting evidence (checking other call sites via `dep_trace.py`, reading unrelated mixin files) after that point drew a direct correction: "all you have to do is read the PJTHousingsTable.insert function and literally copy and paste the needed code... This requires no searching of any other files" and "i'll do it myself. you are second guessing too many things." The underlying technical read (a real, necessary call site existed in `objects_3d/housing.py`'s `_set_model`) turned out correct and worth surfacing, but it should have been offered as a single clear statement, not as a springboard for continued independent verification once the user had already given clear direction.

**Why:** The user is the domain authority on this codebase's own design intent (see Background entry above — self-taught but deeply familiar with his own architecture). When he states a design fact directly, additional searching reads as not listening, not as diligence — and burns time/context he's already offered to spend himself ("i'll do it myself").

**How to apply:** Once the user gives a concrete, specific instruction (naming the function to mimic, the file to edit, or the exact fix), execute it directly. Reserve independent investigation for before the user has committed to an approach, or when they explicitly ask "does this make sense" / "how is X possible" (a genuine question, answerable directly from already-open files, is fine — see the very next exchange in this same incident, where asking "how is it possible for the project housing to get inserted before any global cavities actually exist" was answered correctly and briefly). The signal to stop: the user says "you are second-guessing" or states a plan for what *they'll* do — that's a request to step back, not an invitation to keep researching in parallel.

---

## Project (current state, plans, open work)

### Material system rewrite (2026-09-15) — hue-preserving weight-based materials
`gl/materials/` was rebuilt from scratch at the user's request: "the system I have currently ends
up changing the actual color that is seen" — picking a color and rendering it wasn't showing back
that same color. Root-caused to three compounding issues in the old per-material ad hoc RGB
formulas plus the fragment shaders' per-channel overflow clamp; fixed via scalar material weights
applied directly to the caller's `Color`. Full root-cause writeup and the new design are now in
`harness_designer/gl/materials/MAP.md` — see there.

### Current priority order
As of 2026-07-10: CI/build squared away. Sequence, in order:
1. **Handlers for adding objects** (3D editor) — was current focus.
2. **3D schematic editor** — get it fully functioning.
3. **Object browser** — explicitly not completed yet (e.g. the tree has no click-to-select wiring at all); deliberately deferred until after the 3D schematic editor.
4. **editor2d shared OpenGL context** work (`AA_ShareOpenGLContexts` / editor2d not yet sharing context) — bumped when the user shifted to handlers work.

**Why:** Deliberate reprioritization, not a stall — each stage is intentionally gated on the previous one.

**How to apply:** Don't flag stages 2-4 as overdue/half-finished until the stages before them are done. Don't treat object-browser gaps as bugs to fix — it's simply not built out yet. (Re-check current status with the user — this snapshot is from 2026-07-10 and may have moved on.)

### Commercial release plan
User plans to release harness_designer commercially, targeting a business-use price point around "10 cents on the dollar" vs. incumbent enterprise harness-design CAD (Zuken E3.series, Siemens Capital, CATIA Electrical Harness Installation, Autodesk Inventor Routed Systems).

**Competitive research (2026-07-19):** Every tool with real 3D connector/housing positioning is enterprise-tier, quote-only pricing, aimed at automotive/aerospace OEMs. Every free/cheap harness tool found (harness.design, EZ Wire, Splice CAD) is 2D/schematic-only — none do 3D. No free-and-3D overlap exists in the market currently. harness_designer's live, continuous, no-button-press full-3D wire reflow during a housing drag/rotate (spotting pinch points and excess wire-entry-angle stress in real time) appears to have no public precedent even among enterprise 3D tools.

**Business model:** Core app stays lean; enterprise-tier feature parity is planned to arrive later as separate paid add-ons/extensions/plugins, not built into core — à la carte, a company buys only the modules it needs. The `harness_designer` package is purpose-written for this: a plugin does a plain `import harness_designer` and gets full access to the UI, DB layer, and rendering pipeline — no separate internal-vs-public API to maintain. A plugin is just another consumer of the same objects the core app uses.

**Why:** The user's read: the real SMB/mid-size pain isn't just enterprise CAD's price — it's being forced to pay for a "mess of things they don't use." Unbundling directly targets that: core covers the baseline, paid add-ons cover specialized capability (e.g. the wire-bundle-packing solver above could plausibly be one such add-on rather than core weight).

**How to apply:** When prioritizing features, weigh value to the underserved SMB/DIY/small-manufacturer segment over matching every enterprise-suite feature — the wedge is "the only 3D option at this price," not feature parity. When a new capability comes up that's enterprise-suite-grade in scope (heavy solvers, certification/compliance workflows, PLM integration), consider flagging whether it belongs in core or a future à la carte module. Enterprise-tier sales (Tier-1 automotive, aerospace) are a plausible later target but face real moats (PLM integration, certification, support contracts) price alone won't overcome — don't assume the low price point converts them directly.

### Licensing: moving from GPLv2 to a source-available license (decided 2026-10-26, alpha release planned within weeks)
**Why:** an earlier project of the user's was forked, re-released on PyPI with its original support links and author name intact, and the user got flooded with issues for code they neither wrote nor released. Under MIT/Apache/GPL that redistribution is legal, so there is no takedown route; a license that does not grant redistribution makes it infringement (DMCA to PyPI works). The user wants the code "open" (modify, fork on a public repo, contribute) but not redistributed as built/packaged software.

**User's terms (all in `LICENSE-DRAFT.md`, repo root, staged, NOT reviewed by an attorney; the real `LICENSE` is still GPLv2 until the user says to swap):** no distributing built/compiled/packaged forms or using any package index, under any name; no porting to another language without written permission; no use in a commercial environment without a purchased license; public repos of modified source are fine if notices stay and changed parts are marked; any contribution (PR or discussion, any form) becomes covered by the license; third-party plugins (not by the user, not shipped with the app) are external and not covered; running uncompiled source is forbidden UNLESS testing the user's own changes for the purpose of contributing. The app will be written so it cannot run uncompiled (design not done yet).

**Installers (done 2026-10-26):** all three show the repo-root `LICENSE` before installing: Windows Inno `LicenseFile`, macOS `build_pkg.sh` substitutes it (HTML-escaped) into the `license.html` template, Linux `install.sh` pages it and requires typing `yes` (or `--accept-license`). Keep `LICENSE` plain text because Inno shows plain text. The macOS BSD-sed path and the Linux interactive prompt were not run (only on Windows with GNU sed).

**Still open:** attorney review; swap `LICENSE`; contribution terms in `CONTRIBUTING.md` (currently a placeholder) and a CLA bot; the compile-only check and whether the license needs a no-circumvention clause beyond Section 5.5; whether Section 3 (commercial license) should still apply to a company developer testing a contribution (as drafted it does). The repo was already public under GPL-2.0 (23 stars, 0 forks on 2026-10-26), so copies cloned before the swap stay GPLv2. Commit authors: the user, the Copilot agent and Claude only (no outside humans), so relicensing needs no one's consent; copyright in purely AI-written code is unsettled.

---

### `insert_example_harness.py` (repo root, built 2026-10-26) -- seeds a complex example vehicle harness via raw SQL, not the app's object layer
User asked for an example project (a "fairly complex vehicle wiring harness") insertable by a standalone script, using only parts already in the catalog. Built as a single root-level script, deliberately NOT importing `harness_designer` or driving `Project`/`PJTHousing`/etc.: `SQLConnector.__init__` takes a live `MainFrame` (a Qt widget) and `.connect()` does splash/download work, so the real object graph can't be stood up headlessly without launching the GUI (which MEMORY.md already says not to do). Instead it opens the sqlite file directly and reimplements only `database/id_generator.py`'s 128-bit row-id packing (byte-for-byte), then looks up every part it uses from the live catalog at run time by real `part_number`.

**Non-obvious discovery that would burn a lot of time to rediscover:** `pjt_cavities.part_id` is a required (NOT NULL) FK into the GLOBAL `cavities` table, but that table only has AUTHORED cavity geometry for 11 housings total, out of 78,148 in the live database (confirmed by querying `SELECT DISTINCT housing_id FROM cavities` against a real `harness_designer.db`) -- every other housing has zero catalog cavity rows. A housing can only be placed with real cavities if it's one of those 11 (all Aptiv GT/CTS/OCS/HES/Apex sealed connectors, one TE Connectivity 13-pos IDC board connector, one Bosch 4-pos -- part numbers are the `*_PN` constants at the top of the script). Several of those 11 also have a `num_pins` that doesn't match their actual authored cavity count (`ecm_a`'s catalog part advertises 16 pins but only 12 are authored; one candidate housing advertised 3 pins but only had 2, dropped from the script for that reason) -- always check real cavity count (`cav_count` in a `SELECT ... (SELECT COUNT(*) FROM cavities WHERE housing_id = h.id)` query), never trust `housings.num_pins` alone, before indexing into a housing's cavities.

Also confirmed empirically (useful for anything else that writes `pjt_*` rows directly): there is no real `project_id` column on any `pjt_*` table -- a row belongs to a project purely because the leading 3 bytes of its 16-byte `id` equal that project's integer `projects.id` (`pjt_bases.py`'s `_project_id_bounds`), so every project's rows live together in the same tables already, and a fresh project's ids can never collide with another's. Circuit-trace connectivity (confirmed against a real project's own data, not just the docstring) is by sharing one physical `pjt_points3d` row's id between a terminal's position/`attach_point3d_id` and a wire's start/stop point -- equality of id, not of coordinates -- so the script shares that row outright rather than modelling the live app's separate per-side "clone" point.

This script was tested against a scratch copy of the real `harness_designer.db` (never the live file), inserting a full harness (11 housings spanning 2-50 pins, 113 cavities, 76 terminals, 53 wires across 33 circuits, a chained 10-splice chassis-ground bus, 2 bundles, 5 wire seals, one TPA lock, and one each of a CPA lock/cover/boot placed generically since none of those 11 housings' `compat_cpas`/`compat_covers`/`compat_boots` are populated in this catalog) with zero broken FK references and every circuit having exactly one `is_start` terminal. It has never been opened in the actual GUI.

## Architecture notes (deep-dive references)

### Bundles: design lives in BUNDLE_DESIGN.md (repo root)
Bundle/transition PLACEMENT and cross-view reaction rules are in `BUNDLE_PLACEMENT.md` (repo root); add placement decisions THERE. All bundle-specific design -- the 2026-09-25 create-from-wire / extend / shared-waypoint / 1-to-1 layout spec, open questions, code-state audit, known bugs, decision log -- is in `BUNDLE_DESIGN.md`. Read it in full before touching anything bundle-related, and add new bundle decisions THERE, not here. Bundles are 3D + pegboard only (no schematic).

### Transitions: model/rendering design lives in TRANSITION_DESIGN.md (repo root)
How a transition's own 3D model is built and rendered (as opposed to placement/attaching, which stays in `BUNDLE_PLACEMENT.md`) is in `TRANSITION_DESIGN.md` -- the OCC boolean pipeline's known failure modes (ShapeList, is_valid fragility, boolean-seam shading artifacts), the decision to replace it with cylinder/sphere primitives placed by vector math with no boolean op, the confirmed data semantics of `offset`/`bulb_offset`/`angle` (all literal world-space values per branch, not rotated with the branch -- confirmed against `build123d.Plane.rotated()`'s real behavior; euler angles are the confirmed permanent format, not a stopgap toward quaternions -- gimbal lock only occurs converting *to* euler, never *from* it), the hub-sphere rule, measured performance, known catalog data bugs (9 blank rows, 5 rows with a stray `bulb_offset` on the wrong branch, a `branches` off-by-one in `database/global_db/transition.py`), and the implementation order for porting the (prototyped, not yet ported) primitive design from `scratches/transition_viewer/` into the real app. Read it in full before touching transition model-building code, and add new decisions THERE, not here. A future, not-yet-scheduled dialog for user-authored transitions/boots (built from the same primitive description) is sketched in `TRANSITION_EDITOR_DIALOG.md` -- add dialog-specific detail there.

### Boots: design lives in BOOT_DESIGN.md (repo root)
Boot-specific design (shape/geometry description and whether/how a boot bends to follow the routed harness) is in `BOOT_DESIGN.md` -- a from-scratch design, since today a boot is a single rigid uploaded CAD model (`Boot.model3d`) with no procedural geometry, no shape field, and no bending of any kind. Three hard problems recorded there, none solved yet: (1) the housing-connection end's cross-section shape (round vs. rectangular, and possibly changing shape along the boot's own length), (2) the boot flexing to follow the actual routed bundle at runtime (would make a boot the first non-rigid catalog object in the app), (3) continuous taper along the boot's length (the user's own assessment: hard to render correctly even with a real CAD kernel, not just with primitives). Read it in full before touching boot design, and add new decisions THERE, not here.

### Twisted wires + per-conductor table: design lives in TWISTED_WIRE_DESIGN.md (repo root, started 2026-11-03)
Rendering a twisted pair/triple (driven by `wires.tpi`) with a procedural shader, vertex-pinned stripes and bend handling (twist-phase carry + mitred ends, verified numerically), and the new table describing each individual conductor inside a multi-conductor wire (`wires` keeps describing the outside; no unique column but the id; `wire_id` points at the cable). The conductors table, the fixed "no color" id and the builder's static (ledger-based) catalog ids are BUILT in both repos (2026-11-03); the rendering is still design only. Read it in full before touching either, and add new decisions THERE, not here.

### Reading a live run's evidence: app log, crash dumps, project DB (found 2026-10-15)
The app can't be launched from here, but the user's runs leave real evidence -- check it before theorising from the code (static reading alone got a "wires still tangled" report wrong twice).
- Everything is under `%APPDATA%\HarnessDesigner\`: `log\<date> - pending.log` (records start with an ISO timestamp + level; tracebacks are quoted `TRACEBACK` records), `log\render_failure_<Class>_*.html` (crash_dump of the view object whose render raised), `log\manual_dump_Canvas_*.html` (the user's Ctrl+Shift+D: every view object that canvas drew last frame), and `harness_designer.db` (+ `-wal`/`-shm`; project data in the `pjt_*` tables).
- Each dump `.html` embeds one JSON object per line in `<script type="application/json" id="dump-data">` (html-unescape, then `json.loads` per line; first line is meta with `roots`, the rest are nodes whose `children` are `value`/`ref`/`container`/`error` items). Parse that, not the rendered page.
- A dump shows the LIVE state (a chain's in-memory drag overlay, e.g. `Wire._waypoint_points`), not the saved route. The saved route is `pjt_wire_paths` joined to `pjt_points_pegboard` (peg-board) / `pjt_points3d`. Copy the db + `-wal` + `-shm` into the scratchpad and open the copy `mode=ro` -- never the live files. The overlay and the saved path disagreeing is exactly what exposed the missing release-time commit (BUNDLE_PLACEMENT.md section 11, the 2026-10-15 entry).
- When something that used to be cleaned up stops being cleaned up (an object keeps rendering after delete), diff the file against HEAD first: another session's uncommitted insert had split `CanvasBase.remove_object` in two.

### Python 3.14t (free-threaded) port: decided to drop build123d + VTK, go straight to OCP/OCCT; PySide6 is now the sole real blocker (2026-10-19)
Full dependency audit (`PYTHON_314T_COMPAT.md`, sent to user, not committed to the repo) found two "blocker" packages with no `cp314t` wheel: cadquery-ocp (and therefore build123d, which has no backend but it) and PySide6/shiboken6; VTK was a partial blocker (ready on Linux, missing on Windows/macOS).

**User's decision, overriding two of those three findings:** cadquery-ocp/build123d is a non-issue — user is dropping `build123d` entirely and calling OCP/OCCT directly instead, and has *already* updated their own fork of OCP to support 3.14t. VTK is also moot — the 3.14t version of the app will not support VTK at all (visualization path presumably gets rebuilt without it, not otherwise detailed here). **How to apply:** when touching anything that currently goes through `build123d` (likely the CAD/model-import and geometry-construction code — not yet located/confirmed which files these are) or anything VTK-based, check with the user before assuming the current PySide6/Qt-only, build123d-mediated path is still the target for the 3.14t port; it is being replaced, not patched.

**What's left:** PySide6 is now the single real blocker for 3.14t. User "had thought there was a 3.14t release of it" and was surprised there isn't one yet — per the audit, Qt for Python's maintainer has WIP groundwork (`PYSIDE_COARSE_BINDING_LOCK` / PYSIDE-2221, a "lazy lock" / PYSIDE-2404) on an unreleased `free-threading` branch, nothing shipped as of 2026-10-19. No workaround identified yet; this is an open problem, not a solved one.

### Cython reassignment audit: ~75 real fixes applied across 35 files (2026-10-19)
Ran mypy over the whole `harness_designer/` package (803 files), filtered to `[assignment]`-class errors (483 candidates across 182 files), triaged all of them via 5 parallel agents, then applied the confirmed fixes via 4 more parallel agents. Full triage detail (true/false positive reasoning per candidate) was written to `CYTHON_REASSIGNMENT_AUDIT.md` (repo root, not committed -- regenerate by re-running the same mypy command if needed later; see the "Third category found 2026-10-19" note on the "Quoted forward-reference class annotations" entry above for the three-way risk rule this was built on).

**What got fixed:** ~75 same-scope variable-reassignment sites, mostly the `list[str] -> str` via `', '.join(...)` pattern in SQL-building helpers (renamed to `..._str`/`..._sql`), a cluster of numpy `ndarray`-unwrap-via-`out = out[0]` sites in `geometry/angle/angle.py`, `quaternion.py`, `point.py`, and several raw-Qt-type mixes (`QColor` to this project's `Color` class, `QPoint` to `int`, `QHBoxLayout`/`QVBoxLayout` locals, `QGroupBox`). Two widened annotations instead of renames: `global_db/bases.py`'s `__table_name__: str` and `ui/mainframe.py`'s `_selection_source_editor: str` both got `| None` added since they're genuinely optional and were being assigned `None` while annotated non-Optional.

**Caught during application, not during triage:** the original triage data had the wrong file paths for the `cavity.py`/`aabb`/`obb`-setter and `housing.py`/`compat_*_array`-setter fixes -- it said `objects/objects_3d/cavity.py`/`housing.py`, but those files don't have those setters at all. The real bugs (at line numbers within ~10 of what was reported) were in `database/global_db/cavity.py`/`housing.py`. This codebase has the same base filename (`cavity.py`, `housing.py`, etc.) under `objects/objects_3d/`, `database/global_db/`, and `database/project_db/` (as `pjt_cavity.py`/`pjt_housing.py`) -- always confirm which directory's copy a line-number-based finding actually refers to before trusting it, especially from automated triage that may not have context on this naming collision.

**Deliberately NOT fixed:** `database/create_database/transition_branches.py`'s `branch_id: bytes | None = 0` default looks like a `None` typo but isn't -- the `pjt_transition_branches` table defines `branch_id` as `IntField('branch_id', no_null=True)`, so `None` would fail the NOT NULL constraint at insert time. Left as-is with a comment; this is a pre-existing annotation-vs-column mismatch, not the reassignment bug.

