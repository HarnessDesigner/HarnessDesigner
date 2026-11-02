## FILES

#### __init__.py

A module-replacement singleton loader (`__CullingLoader`, swaps itself into
`sys.modules[__name__]` at import time, copying over `__name__`/`__file__`/`__package__`/etc. so
it still looks like a normal module) so `gl.culling.cull(...)`/`gl.culling.shutdown()` read as
plain module-level calls while actually being backed by exactly one process-wide
`CullingThreadPool()` instance, constructed once at import. All three canvases
(`canvas_3d`/`canvas_schematic`/`canvas_pegboard`) call this one shared instance rather than each
building their own pool — canvas updates can only ever happen serially anyway (everything runs on
the main thread), so a per-canvas pool (each spinning up its own 10 persistent worker threads)
would have been pure duplication, not a real parallelism win. This module is also the current,
relocated home of the architecture this file's DESIGN NOTES's "CullingThreadPool.cull() index-mismatch" note
still describes by its old path (`gl/canvas3d/culling.pyx`) — the class and the fix below are
unchanged, just moved here.

#### culling.pyx

`CullingThreadPool` — per-frame AABB-frustum culling across a fixed set of 10 persistent worker
threads, each backed by a `Queue(maxsize=1)` for work-in/results-out. ⚠ Previously a real
deadlock, root-caused 2026-08-08 during a hang that only reproduced when finalizing a
wire-to-wire snap merge: `cull()`'s dispatch loop skipped any worker whose container was currently
empty but only counted *how many* jobs went out (`num_jobs`), not *which* worker indices actually
got one; the gather loop then blindly called the blocking `.finish()` for workers
`0..num_jobs-1`, assuming dispatched containers were always a contiguous run starting at index 0.
Deleting/creating objects shifts the distribution unevenly across the 10 fixed containers, so once
an early container went empty while a later one didn't, `.finish()` got called on a worker that
was never dispatched a job and blocked forever — looked "print-statement dependent" while
debugging purely by coincidence (what actually varied was the live object count/distribution at
the moment of the next cull pass). **Confirmed still fixed in current source**: a `dispatched`
list now tracks the actual dispatched worker indices, and the gather loop iterates exactly that
list instead of `range(num_jobs)`. Any future change to the container-assignment scheme must
preserve that invariant: the set of workers gathered from must exactly match the set actually
dispatched to. Being a `.pyx` file, a source edit alone does nothing until `culling.c`/the `.pyd`
below are regenerated — rebuilding needs the project's actual Python 3.11 (`C:\python3.11.14`),
not whatever generic `python` resolves to on PATH (a mismatched Python/Cython pairing fails with
unrelated-looking errors, e.g. a missing `libc.math.fabsf` pxd); a stale, currently-loaded `.pyd`
also can't be deleted/overwritten on Windows until every process that imported it (the running
app, any lingering orphaned Python process from a prior crash) is closed first.

#### culling.pyi

Type stub for the compiled `culling.cp311-win_amd64.pyd` extension below — gives
`CullingThreadPool`'s signature to type checkers/IDEs without needing the compiled binary present
or re-parsing the `.pyx` source.

#### culling.cp311-win_amd64.pyd

The compiled Cython extension that actually runs at runtime (CPython 3.11, win_amd64 ABI) — must
be regenerated from `culling.pyx` after any source change via the project's real build recipe
(`builder/cython_build.py`/`builder/compiler.py`), never hand-edited.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### CullingThreadPool.cull() index-mismatch: a real deadlock, not a GL/context issue (2026-08-08)
`CullingThreadPool` runs per-frame AABB-frustum culling on a fixed set of 10 persistent worker threads, each with a `Queue(maxsize=1)`; `Canvas._object_data` is a permanent list of 10 containers and `add_object()`/`remove_object()` fill the smallest / remove from the holder with no rebalancing. The bug (app hang at 0% CPU, immune to Ctrl+C, only on finalizing a wire-to-wire snap merge via `handlers.wire_handler.merge_wire_into`): the dispatch loop skipped workers with empty containers but only counted jobs (`num_jobs`), then the gather loop called `.finish()` (blocks on `Queue.get()`) for workers `0..num_jobs-1`, so once an early container emptied while a later one did not, it blocked forever on a worker never dispatched to. Debug `print()` placement had no causal effect; what varied was the object distribution at the next cull. Fixed by tracking the actually dispatched worker indices (`dispatched` list appended beside each `worker.cull(...)`) and gathering from exactly those. **Invariant to preserve:** the workers gathered from must exactly match the workers dispatched to. It is a `.pyx`, so a source edit does nothing until the `.c`/`.pyd` is regenerated (`builder/cython_build.py`/`compiler.py`), with the project's Python 3.11 at `C:\python3.11.14` (a mismatched Python/Cython fails with unrelated errors such as a missing `libc.math.fabsf` pxd), and a loaded `.pyd` cannot be overwritten on Windows until every process that imported it (the app, orphaned processes) is closed.
