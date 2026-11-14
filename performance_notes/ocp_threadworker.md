# harness_designer/ocp_threadworker.py

Funnels every OCP call through one daemon thread (`OCPThreadWorker`, created and started at import, line 125-126). Callers block until the job finishes, so it is a serialisation point: two callers that arrive together run one after the other, never in parallel. That is deliberate (OCP is not thread safe) but it means any long OCP job (a big boolean, `ocp_ops.build_text_mesh` on a long string) delays every other OCP caller and the caller's own thread. Anything on the Qt main thread that calls an `@ocp_thread` function freezes the UI for the job's length.

## Line 48-86 (`OCPThreadTask`) and 100-107 (`_OCPThreadWorker.add`) — a Lock used as a one-shot completion signal
`OCPThreadTask` acquires a `threading.Lock` in `__init__`; `with worker: pass` in `add` re-acquires it so the caller blocks until the worker releases it. A `threading.Event` is the usual tool for "wait for one completion" and is what the rest of the module's exit signalling uses. The cost difference is nil; flag only as a clarity point.

## Line 112-116 (`_OCPThreadWorker.run`) — blocking `queue.get(True)` is correct
The thread sleeps on the queue and costs nothing while idle. Good.

## Line 133-140 (`ocp_thread`) — adds a queue hop plus a thread handoff per call
For many tiny OCP calls (one per character in a text label) the handoff dominates the work. `ocp_ops.build_text_mesh` is one call per string, which is the right granularity; keep new OCP entry points coarse like that.
