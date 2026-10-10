# harness_designer/gl/info.py

## Line 32-83 (`_safe_gl_get_*`) — one query per field, once
These functions run inside `get`, which runs once at start-up. Not on any hot path.

## Line 86-145 (`get`) — collected once, cached in a module global
Creates an offscreen surface and context, runs about a dozen GL queries, then tears the context down. Runs once per process.

**Functional issue (flagged, not fixed):** the docstring says a call without a parent returns the cached dict and raises `RuntimeError` if info was never collected. The code does neither: it always collects on the first call, and it returns `None` on the first call (the `return None` at line 145) rather than the dict. Callers that read the return value after the first call receive `None`. The parent argument is also never used. Confirm the intended contract before changing it.

**Typing:** `_safe_gl_get_integer` returned `None` on failure but was annotated `-> int`; changed to `-> int | None` in this pass.
