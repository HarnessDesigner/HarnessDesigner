# harness_designer/check_types.py

`do` (line 1451) is applied to roughly 8,500 functions. What it costs depends entirely on the constant `_ENABLED` (line 108).

## Line 1451-1460 (`do`) — currently free
`_ENABLED = 0`, so `do` returns `func` untouched: no wrapper, no per-call cost, no `_FuncState` objects, no flush thread (the `atexit` / `Finalize` / thread start at line 1621 are inside `if _ENABLED`). Nothing in the app's normal run pays for this module except one function call per decorated function at import time.

## When `_ENABLED` is turned on (audit runs only)
Everything below applies only to an audit run from source; never leave it on for a normal session and never for the compiled build.
- Per checked call the wrapper does a counter update and `_call_mark` (line 368), then `_verify_args` (line 971) compares each annotated parameter with its hint tree and `_call_keys` (line 1010) builds the dedup key for a wrong call. A function is checked on its first `_FULL_CALLS = 1000` calls, then every `_STRIDE = 8`th. Hot per-frame functions will therefore be slowed by a Python-level wrapper for the rest of the session, so frame timings taken with it on are not representative.
- Memory: one `_FuncState` (slots, line 193) per decorated function that has been called, with hint trees, verdict dict and `rows`/`seen` lists that only ever grow (bounded per function by `_SITE_LIMIT = 5` callers and `_SITE_CALLS = 10`). With thousands of functions this is a few MB, and it is intentional (it is the recorded evidence).
- `_flush_loop` (line 1615) wakes every `_FLUSH_SECONDS = 10`; `_fold` (line 1483) and `_dump` (line 1555) do their SQLite work with a lock held and run `execute` inside loops. Only rows that are new since the last tick are written, so the cost is proportional to new wrong calls, not to total calls. Not a concern.
- `_make_generator_wrapper` (line 1360) builds an f-string inside its loop for each yielded item when checking a generator; only matters for audit runs over generators that yield a lot.

## Recommendation
Nothing to change for speed. If a profiling session ever wants the audit on, set `_STRIDE` higher first (it is the one lever that scales per-call cost) and accept that it is a debugging mode.
