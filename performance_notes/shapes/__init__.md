# harness_designer/shapes/__init__.py

## Line 34-95 (`cache_primitives`) — builds every primitive once, with timing
Builds each primitive's mesh and caches it, reporting progress to a splash screen when one is given. Runs once at start-up. The `_timed` wrapper logs how long each step takes.

**Typing and Qt imports (fixed in this pass):** `cache_primitives` returns a `dict`; the timing wrapper takes a callable and returns its result. The Qt imports are now module-level `QtCore`/`QtWidgets` references, not per-call imports.
