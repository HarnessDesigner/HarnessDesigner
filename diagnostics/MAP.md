## FILES

#### CLAUDE.md

A condensed, always-loaded reminder of `dep_trace.py`'s usage (this directory is auto-read by Claude Code when working here) — the repo-root `CLAUDE.md` has the fuller version of the same mandate.

#### compare_snapshots.py

`main()`-driven script for diffing two snapshots of something (likely two `dep_trace.py` JSON dumps, or two memory/map states) — check its `--help`/source for the exact inputs it expects before relying on its output; no dedicated MEMORY.md entry describes its origin.

#### dep_trace.py

The static-AST dependency/call/override/import tracer — **read this directory's `CLAUDE.md` or the repo-root `CLAUDE.md` for its full usage.** This is the primary tool for "where is X defined," "what does this file import," "who calls this method," "does this override call its superclass" questions, and should be reached for before Read/Grep for those (a repo hook actively blocks direct `Read` of `.py` files and pushes toward this tool first). Also used throughout this very documentation reorg, and cited directly in MEMORY.md's project history for confirming dead code (`dep_trace.py --calls`) and full caller lists (`dep_trace.py --imported-by`).

#### find_unused_functions.py

Scans module-level function definitions (`collect_module_level_functions`) and counts call-like references to each name across the given paths (`count_call_like_references`), flagging ones with zero hits as candidate dead code (`Finding`). `count_getattr_setattr_files` tracks how many files use dynamic attribute access as a caveat on the result's confidence — shares `dep_trace.py`'s own documented blind spot: a function reached only through `getattr`/`setattr`, `importlib`, or a star import can look unused when it isn't. Treat a "0 references" finding as a lead to verify, not a ready-to-delete result.

#### fix_string_annotations.py

An AST-based codemod helper for fixing string/quoted type annotations (`_flatten_bitor`, `_base_name_of`, `_module_level_defs`, `_enclosing_class`) — likely built to enforce or migrate toward the "quoted forward-reference" typing conventions documented in the repo-root MEMORY.md's type-hinting section. No dedicated MEMORY.md entry describes its origin or intended workflow.

#### query_memory.py

A `main()`-driven script for querying/searching this project's MEMORY.md (or the auto-memory store) programmatically rather than by eye. No dedicated MEMORY.md entry describes its origin.
