# harness_designer/ocp_threadworker.py

## Line 49-65 — `threading.Lock` used as a one-shot completion signal
`OCPThreadTask` acquires `self._lock` once in `__init__` (line 50), then
`__enter__`/`__exit__` (lines 53-57) re-acquire/release it around the
`with worker: pass` block in `_OCPThreadWorker.add` so the calling thread
blocks until the OCP worker thread's `__call__` (line 65) releases it. This
works, but it's using a mutex's acquire/release as a substitute for a
`threading.Event` (`wait()`/`set()`), which is the tool actually meant for
"block until signaled once" and is what the rest of this module (and
`memory_diagnostics.py`'s listener) already uses for exit signaling. Not a
measurable bottleneck either way (both are cheap OS-level primitives) — flag
only because it's not yet wired into the app (per the module docstring) and
would be a cheap, low-risk clarity/consistency fix to make before it is.
