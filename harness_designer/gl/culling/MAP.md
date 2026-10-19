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
relocated home of the architecture MEMORY.md's "CullingThreadPool.cull() index-mismatch" note
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
