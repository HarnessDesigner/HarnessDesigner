## FILES

#### CLAUDE.md

A condensed, always-loaded reminder of `dep_trace.py`'s usage (this directory is auto-read by Claude Code when working here) — the repo-root `CLAUDE.md` has the fuller version of the same mandate.

#### compare_snapshots.py

`main()`-driven script for diffing two snapshots of something (likely two `dep_trace.py` JSON dumps, or two memory/map states) — check its `--help`/source for the exact inputs it expects before relying on its output; no dedicated MEMORY.md entry describes its origin.

#### cython_hint_audit.py

Static check for the failure that only appears in the compiled build: a call that passes an argument Cython's runtime type check refuses (`TypeError: Argument 'params' has incorrect type (expected tuple, got list)`), which a run from source and mypy never see. Usage: `python diagnostics/cython_hint_audit.py [target_dir] [--json] [--float-to-int]` (target defaults to `harness_designer`; point it at the whole package, like `dep_trace.py`'s cross-file modes). It indexes every parameter whose hint Cython enforces (`tuple`/`list`/`dict`/`set`/`frozenset`/`str`/`bytes`, their `[...]` forms and `| None` -- an exact-type check that rejects subclasses and neighbouring types; unions of two or more non-None types get no check), infers argument types from literals, builtin calls, locals, `self.x` attributes and `a, b = self.method()` returns, and reports a call only when every definition it could reach rejects the argument. Output is split into DEFINITE (the argument can only be a rejected type) and POSSIBLE (it may also be `None` -- the tool cannot see an `if x is not None` guard, so each one needs a look); tiers `A`/`T`/`B`/`S` say how the call was matched (see the module docstring). The rules it encodes were probed against Cython 3.2.4, not read from docs -- re-probe if the Cython version changes. Not seen: argument types that come from another object's return value, callbacks and Qt slots, subclass instances built elsewhere, `getattr` dispatch -- "nothing found" is a good sign, not proof. Validated on 2026-10-21 by running it against a copy of the tree with the four `execute()` hints put back to `tuple | None`: it found all 14 list-passing call sites (including both from a real crash log). Its method-name exclusion list is built at run time from builtin, stdlib, numpy, pandas, PIL and PySide6 classes, so it needs those importable to be accurate (it warns if PySide6 is missing).

#### dep_trace.py

The static-AST dependency/call/override/import tracer — **read this directory's `CLAUDE.md` or the repo-root `CLAUDE.md` for its full usage.** This is the primary tool for "where is X defined," "what does this file import," "who calls this method," "does this override call its superclass" questions, and should be reached for before Read/Grep for those (a repo hook actively blocks direct `Read` of `.py` files and pushes toward this tool first). Also used throughout this very documentation reorg, and cited directly in MEMORY.md's project history for confirming dead code (`dep_trace.py --calls`) and full caller lists (`dep_trace.py --imported-by`).

#### find_unused_functions.py

Scans module-level function definitions (`collect_module_level_functions`) and counts call-like references to each name across the given paths (`count_call_like_references`), flagging ones with zero hits as candidate dead code (`Finding`). `count_getattr_setattr_files` tracks how many files use dynamic attribute access as a caveat on the result's confidence — shares `dep_trace.py`'s own documented blind spot: a function reached only through `getattr`/`setattr`, `importlib`, or a star import can look unused when it isn't. Treat a "0 references" finding as a lead to verify, not a ready-to-delete result.

#### fix_string_annotations.py

An AST-based codemod helper for fixing string/quoted type annotations (`_flatten_bitor`, `_base_name_of`, `_module_level_defs`, `_enclosing_class`) — likely built to enforce or migrate toward the "quoted forward-reference" typing conventions documented in the repo-root MEMORY.md's type-hinting section. No dedicated MEMORY.md entry describes its origin or intended workflow.

#### query_memory.py

A `main()`-driven script for querying/searching this project's MEMORY.md (or the auto-memory store) programmatically rather than by eye. No dedicated MEMORY.md entry describes its origin.

#### type_audit_report.py

Lists the wrong calls that `harness_designer/check_types.py` recorded (see its entry in `harness_designer/MAP.md`). Rewritten 2026-10-22 as a plain lister: the check itself now runs inside `do` at run time and stores only what does not fit, so there is nothing left to re-judge. It reads the two tables, `functions` (name, annotated signature and return type, source file, line) and `calls` (calling function, file, line, the signature of the call as it was made, the type returned) and prints each function with its annotated signature and, under it, every wrong call -- the signature that was passed and who called -- so the mismatch can be read by eye. Usage: `python diagnostics/type_audit_report.py [--db FILE] [--function REGEX] [--file REGEX] [--md FILE]`; `--md` also writes a checklist table with *Fix?* and *Comments* columns. `--db` defaults to `type_audit.sqlite3` in the repo root (or the file named by `HARNESS_TYPE_AUDIT_DB`). The recorder's judgement is coarser than a full resolver's: a hint written as a quoted name that cannot be imported at run time is matched by class name only, so a class re-exported under another name can show up as a false positive.
