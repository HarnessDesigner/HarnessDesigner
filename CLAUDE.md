# harness_designer

## Read at the start of every session, in this order
1. **`MEMORY.md`** (repo root, full file) — persistent project memory: user background, coding
   conventions, feedback on how to work in this repo, architecture decisions. Read it in full
   before doing anything else.
2. **`CODEBASE_MAP.md`** (repo root) — directory/file map of the package, per its own mandatory
   note at the top of that file.

## Locating code: use `diagnostics/dep_trace.py`, not grep-and-read

This is a large (~530 file) codebase. Answering "where is X defined," "what does this file
import," "who calls this method," or "does this override call its superclass" by reading files
and grepping around burns a large amount of context and time, and it's easy to miss a call site
that way. `diagnostics/dep_trace.py` answers all of these directly from a static AST pass and is
fast and cheap. **Reach for it before Read/Grep whenever the question is a "where/what/who"
question about code structure** — use Read/Grep once dep_trace.py has told you which file(s) and
line(s) to actually look at.

**Cross-check dep_trace.py results against MEMORY.md/CODEBASE_MAP.md.** dep_trace.py's default
mode shows a file's import tree, and every mode's `--name` is a regex search over code (types,
definitions, call sites, overrides, importers). Whenever a file, class, function, or topic that
search touches also shows up in MEMORY.md's table of contents (its `###` headings, e.g. a search
around rotation code lining up with "Rotation matrix convention") or CODEBASE_MAP.md's section
for that area, read that section in full before making changes — it likely documents a
convention, a past bug, or a reason something looks the way it does that dep_trace.py's purely
structural view of the code can't tell you. (At session start this table of contents arrives
pre-loaded via the SessionStart hook; outside that, read the files directly.)

```
python diagnostics/dep_trace.py <file_or_dir> [--depth shallow|deep] [--name PATTERN] [--local] [--json]
python diagnostics/dep_trace.py <file_or_dir> --types       [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --calls       [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --overrides   [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --imported-by [--name PATTERN] [--json]
```

**`target` is always required** (a single `.py` file, or a directory scanned recursively for
every `*.py` file under it) and **can go anywhere on the command line** — before or after the
mode flag(s), before or after `--name`, it doesn't matter.

**Any combination of the four mode flags (`--types`, `--calls`, `--overrides`, `--imported-by`)
can be given together in one run**, sharing the one `--name` filter — e.g.
`--calls --overrides --name __init__` runs both and reports both against the same pattern. Each
mode runs exactly as it would alone; only the *output shape* changes once more than one is
active:
- **Exactly one mode active (or none)** — flat output, unchanged: plain text is the bare report
  with no header, `--json` is a bare array/object (whatever that mode normally returns).
- **More than one mode active** — plain text prints one `== --mode ==` labeled section per
  active mode, back to back; `--json` becomes one object keyed by mode name, e.g.
  `{"calls": [...], "overrides": [...]}`, instead of a bare array.

`--calls` and `--overrides` share one class-registry build when both are active in the same run
(so combining them costs one extra pass over `target`, not two) — same for `--imported-by`'s
module index.

**There is no separate `--find` flag** — definition lookup (find a class/function/method by
name) is just "index everything and filter by `--name`," which is exactly what happens when you
give `--name` **without any mode flag at all**: no mode flag and no `--name` is the default
import-trace mode; no mode flag *with* `--name` is definition lookup. This one is not
combinable with the other four — it's what runs when none of them are given.

**`--name PATTERN` is optional on every mode** — supply it to filter to one thing, or **omit it
entirely to get a full, unfiltered snapshot of everything that mode tracks across the whole
`target`** (e.g. `--overrides` with no `--name` lists every override relationship found under
`target`; no mode flag and no `--name` reports every import in `target`). Omitting `--name` is a
normal, intended way to use this tool, not a degenerate case — reach for the unfiltered dump
whenever you want a broad map of a subsystem before diving into any one thing.

**`PATTERN` is always a regex, matched with `re.search`.** A plain literal like `Housing3D`
behaves exactly like a substring search (it has no regex metacharacters to change the meaning),
so ordinary names work exactly as you'd expect with zero extra syntax; patterns with real regex
syntax (`^set_.*`, `__(init|new)__`, `Q.*Event$`) work the same way, no flag needed to "turn on"
regex mode. Because it's a substring search rather than an exact match, `--name set_view` also
matches `_set_view` — anchor with `^name$` when an exact match matters.

> The filter is deliberately its own flag (`--name`), not attached to the mode flag
> (`--imported-by NAME`) — an earlier version worked that way and had a real bug: if `target`
> immediately followed the mode flag with nothing in between (`--imported-by harness_designer`),
> argparse couldn't tell whether `harness_designer` was the mode's optional value or the
> positional `target`, silently swallowed it as the former, and errored that `target` was
> missing. Keeping `--name` separate removes that ambiguity for good, regardless of order.

### Default mode (no mode flag, no `--name`) — what does this file import, and what's used from it

```
python diagnostics/dep_trace.py <file_or_dir> [--depth shallow|deep] [--local] [--json]
```

For every `import`/`from ... import` statement, lists the specific attributes/calls/bare names
actually used from it elsewhere in the file, including references inside quoted
`TYPE_CHECKING`-only forward-reference annotations — and tags any import that sits inside an
`if TYPE_CHECKING:` block as `[TYPE_CHECKING]` (a type-only reference, not a real runtime
dependency). Run this on a directory to get one such report per file.

- `--depth shallow` — just the list of import statements, no usage detail (fast overview of
  what a file pulls in).
- `--depth deep` (default) — full usage trace: every attribute/call/annotation use of each
  import, with line numbers.
- `--local` — hide stdlib/third-party imports, showing only in-project ones (relative imports,
  plus absolute imports rooted at the same top-level package as the file). Combine with either
  depth.

### No mode flag, but `--name` given — where is a class/function/method defined

```
python diagnostics/dep_trace.py <file_or_dir> --name PATTERN [--json]
```

Dump every class, function, and method definition under `target` whose bare name matches
`PATTERN`, each with its file:line, kind (`class`/`function`/`method`), qualname, and full
signature. Use this instead of grepping for `def foo` / `class Foo` — it gives the exact
signature and qualified name (`Housing3D.set_position`, not just `set_position`) directly.

### `--types` — where is a type used as a parameter/return/variable annotation

```
python diagnostics/dep_trace.py <file_or_dir> --types [--name PATTERN] [--json]
```

- `--types` (no `--name`) — dump the **entire type-usage index** for `target`: every annotated
  type found, grouped by type name, with every location (file:line, function/qualname, and
  whether it's a `param`, `return`, or `variable`) that uses it.
- `--types --name Housing3D` — filter to types matching that pattern (the type's bare name or a
  full dotted path).

Use this before changing a class's shape (renaming it, changing its constructor, splitting it
up) to find every signature that would need updating.

### `--calls` — every call site of a function/method

```
python diagnostics/dep_trace.py <file_or_dir> --calls [--name PATTERN] [--json]
```

- `--calls` (no `--name`) — dump **every call expression** found under `target` (every
  `foo(...)` and every `obj.foo(...)`), each with its file:line and enclosing qualname. This is
  the complete call graph of the target, unfiltered — useful for a coarse overview of a
  subsystem's internal traffic, but large on anything bigger than a single file.
- `--calls --name set_position` — filter to calls whose name matches that pattern. For
  `self.X(...)`, `cls.X(...)`, and `super().X(...)` calls specifically, it also resolves the
  receiver against the class hierarchy built from `target` and reports which class's
  implementation actually runs (the override itself, or a specific ancestor's, when the class
  doesn't define it). Calls through any other receiver expression are listed but not resolved
  (heuristic name match only — see Limitations below).

### `--overrides` — override / super-call mapping

```
python diagnostics/dep_trace.py <file_or_dir> --overrides [--name PATTERN] [--json]
```

- `--overrides` (no `--name`) — dump **every override relationship** found under `target`:
  every method that shadows an ancestor's method of the same name, which ancestor(s) define it
  too, and whether the override calls `super().method()` (extends the base behavior) or not
  (fully shadows it).
- `--overrides --name Housing3D` — filter to overrides *defined by* that class.
- `--overrides --name __init__` — filter to every override *of* that method name, across every
  class under `target` (the more commonly useful query — e.g. "every `__init__` override and
  whether it chains to `super()`").

Use this before touching a mixin method (this codebase leans heavily on mixins —
`DimensionMixin`, `NameMixin`, `CallbackMixin`, etc. — so a method actually used by a class may
not be defined on that class at all) or before adding an override yourself, to see what's
already being shadowed.

### `--imported-by` — reverse import lookup: who imports this file

```
python diagnostics/dep_trace.py <file_or_dir> --imported-by [--name PATTERN] [--json]
```

The mirror image of the default mode. Resolves every import statement under `target` (relative
or absolute, including `TYPE_CHECKING`-guarded ones, tagged as such) down to the actual file it
points at.

- `--imported-by` (no `--name`) — dump the **entire reverse-import graph** for `target`: every
  file that gets imported by at least one other file under `target`, and the full list of
  importers for each.
- `--imported-by --name camera` — filter to file(s) matching that pattern against a bare
  filename, a path fragment like `gl/canvas_3d/camera.py`, or a dotted module path like
  `harness_designer.gl.canvas_3d.camera`.

Use this before renaming/moving/deleting a file, or changing its public surface, to find every
caller that would break.

### `--json`

Every mode accepts `--json` to print machine-parseable JSON instead of the plain-text report —
useful when you want to post-process the result yourself rather than read it directly.

### Scope matters for cross-file modes

`--calls`, `--overrides`, and `--imported-by` build their picture (class hierarchy, or module
index) from every file under the given `target` before answering. Point them at a directory —
usually `harness_designer/` for a real answer — since a single file only resolves against things
defined/reachable in that same file; anything outside `target` is invisible to them.

### Limitations

- Usage/calls reached only through `getattr`/`setattr`, `importlib`, or a star import
  (`from x import *`) can't be resolved statically. Star imports are flagged as untraceable
  rather than silently skipped; any `getattr`/`setattr` calls found are flagged too.
- `--calls` resolution for `self.`/`cls.`/`super().` receivers is heuristic name-matching
  against a simple depth-first ancestor walk (not full C3 linearization) — exact for single
  inheritance and virtually all non-diamond multiple inheritance, which covers ordinary mixin
  usage in this codebase. Calls through any other receiver (e.g. `some_other_obj.foo()`) are
  listed but never resolved.
- If two classes anywhere under `target` share the same simple name, resolution for either one
  bails out to "unresolved" rather than guessing — this has actually happened in this codebase
  (two unrelated `CallbackMixin` classes).

Full design notes are in the module docstring at the top of `diagnostics/dep_trace.py` itself.
